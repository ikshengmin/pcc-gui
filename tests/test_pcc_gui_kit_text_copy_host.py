"""Pure-host ownership probes; no pcc/compiler imports, native code or fixtures.

Run directly with an isolated standard-library Python interpreter.  The actual
kernel source executes against checked fake raw memory, which rejects freed,
out-of-bounds and double-free accesses.  This is not native/GC/render evidence.
"""

import ast
import json
from pathlib import Path
from types import SimpleNamespace
import unittest


REPO = Path(__file__).resolve().parents[1]
KIT = REPO / "pcc_gui" / "pcc_gui_kit.py"
CONTRACT = REPO / "pcc_gui" / "gui_declarative_contract_v1.json"


class RawMemory:
    def __init__(self):
        self.next_address = 4096
        self.blocks = {}
        self.globals = {}
        self.freed = []
        self.allocations = []
        self.calloc_calls = 0
        self.fail_on_call = -1
        self.callbacks = {}

    def allocate(self, size):
        assert 0 < size <= 2 * 1024 * 1024, size
        address = self.next_address
        self.next_address += size + 64
        self.blocks[address] = bytearray(size)
        return address

    def calloc(self, count, size):
        self.calloc_calls += 1
        if self.calloc_calls == self.fail_on_call:
            return 0
        address = self.allocate(count * size)
        self.allocations.append(address)
        return address

    def free(self, address):
        assert address in self.blocks, ("invalid or repeated free", address)
        self.freed.append(address)
        del self.blocks[address]

    def region(self, address, size):
        for base, data in self.blocks.items():
            if base <= address and address + size <= base + len(data):
                return data, address - base
        raise AssertionError(("freed or out-of-bounds access", address, size))

    def read(self, address, size):
        data, offset = self.region(address, size)
        return bytes(data[offset:offset + size])

    def write(self, address, value):
        data, offset = self.region(address, len(value))
        data[offset:offset + len(value)] = value

    def load(self, address, offset, size):
        return int.from_bytes(self.read(address + offset, size), "little", signed=True)

    def store(self, address, offset, value, size):
        self.write(address + offset, (value & ((1 << (size * 8)) - 1)).to_bytes(size, "little"))

    def define_global(self, name, value):
        address = self.allocate(8)
        self.globals[name] = address
        self.store(address, 0, value, 8)

    def global_value(self, name):
        return self.load(self.globals[name], 0, 8)

    def source(self, value):
        address = self.allocate(len(value) + 1)
        self.write(address, value + b"\0")
        return address


def load_kernel():
    memory = RawMemory()
    exports = {}

    def export(name, result, arguments):
        def decorate(function):
            exports[name] = (result, arguments)
            return function
        return decorate

    namespace = {
        "c_abi_typed_export": export,
        "calloc": memory.calloc,
        "free": memory.free,
        "define_global_i64": memory.define_global,
        "global_addr": lambda name: memory.globals[name],
        "int_to_ptr": lambda value: value,
        "ptr_to_int": lambda value: value,
        "ptr_is_null": lambda value: value == 0,
        "load_i32": lambda address, offset: memory.load(address, offset, 4),
        "load_i64": lambda address, offset: memory.load(address, offset, 8),
        "store_i32": lambda address, offset, value: memory.store(address, offset, value, 4),
        "store_i64": lambda address, offset, value: memory.store(address, offset, value, 8),
        "memcpy": lambda destination, source, size: memory.write(destination, memory.read(source, size)),
        "call_i64_i64": lambda callback, value: memory.callbacks[callback](value),
        "stack_alloc": memory.allocate,
    }
    tree = ast.parse(KIT.read_text(encoding="utf-8"), filename=str(KIT))
    # Do not import pcc_gui (which registers every runtime) or pcc.  Execute the
    # canonical implementation, not a separately maintained behavioral model.
    tree.body = [statement for statement in tree.body if not isinstance(statement, (ast.Import, ast.ImportFrom))]
    exec(compile(tree, str(KIT), "exec"), namespace)
    return SimpleNamespace(**namespace), memory, exports


class OwnedTextTests(unittest.TestCase):
    def setUp(self):
        self.kit, self.memory, self.exports = load_kernel()
        self.assertEqual(self.kit.pcc_kit_init(8), 0)
        self.node = self.kit.pcc_kit_create(-1)

    def copy(self, value=b"hello", node=None):
        if node is None:
            node = self.node
        source = self.memory.source(value)
        self.assertEqual(self.kit.pcc_kit_text_copy(node, 12, 34, source, len(value), 16, 0xFF123456), 0)
        return source, self.kit._n8(node, 120)

    def snapshot(self):
        return {address: bytes(data) for address, data in self.memory.blocks.items()}

    def test_frozen_abi_and_contract(self):
        arguments = ("i64", "i64", "i64", "ptr", "i64", "i64", "i32")
        self.assertEqual(self.exports["pcc_kit_text_copy"], ("i32", arguments))
        self.assertEqual(self.exports["pcc_kit_text"], ("void", arguments))
        self.assertEqual(self.kit.NODE_SIZE, 208)
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))["kernel_text"]
        self.assertEqual(contract["node_record_bytes"], 208)
        self.assertEqual(contract["text_pointer_offset"], 120)
        self.assertEqual(contract["text_byte_length_offset"], 104)
        self.assertEqual(contract["copy"]["symbol"], "pcc_kit_text_copy")
        self.assertEqual(contract["copy"]["abi"], "i32(i64 node, i64 x, i64 y, ptr utf8, i64 byte_length, i64 font, i32 color)")

    def test_utf8_copy_outlives_input_and_is_nul_terminated(self):
        value = "Hi, café 🙂".encode("utf-8")
        source, owned = self.copy(value)
        self.assertNotEqual(source, owned)
        self.memory.free(source)
        self.assertEqual(self.memory.read(owned, len(value) + 1), value + b"\0")
        self.assertEqual(self.kit._n8(self.node, 104), len(value))
        self.assertEqual(self.kit._n8(self.node, 48), len(value) * 7)
        self.assertEqual(self.kit._n8(self.node, 32), 12)
        self.assertEqual(self.kit._n8(self.node, 40), 34)
        self.assertEqual(self.kit._n8(self.node, 112), 16)
        self.assertEqual(self.kit._n4(self.node, 88), 2)
        owners = self.memory.global_value("pcc_kit_owned_text")
        self.assertEqual(self.memory.load(owners, self.node * 8, 8), owned)

    def test_embedded_nul_and_explicit_byte_length(self):
        source = self.memory.source(b"a\0b trailing")
        self.assertEqual(self.kit.pcc_kit_text_copy(self.node, 0, 0, source, 3, 12, 1), 0)
        self.assertEqual(self.memory.read(self.kit._n8(self.node, 120), 4), b"a\0b\0")

    def test_invalid_input_is_atomic_and_does_not_allocate(self):
        source, owned = self.copy()
        stale = self.kit.pcc_kit_create(-1)
        self.assertEqual(self.kit.pcc_kit_destroy_subtree(stale), 1)
        before = self.snapshot()
        calls = self.memory.calloc_calls
        cases = ((-1, source, 5), (stale, source, 5), (99, source, 5),
                 (self.node, source, -1), (self.node, 0, 1),
                 (self.node, source, 0x124924924924924A),
                 (self.node, source, 0x7FFFFFFFFFFFFFFF))
        for node, pointer, length in cases:
            with self.subTest(node=node, pointer=pointer, length=length):
                self.assertEqual(self.kit.pcc_kit_text_copy(node, 99, 98, pointer, length, 97, 96), -1)
                self.assertEqual(self.snapshot(), before)
                self.assertEqual(self.memory.calloc_calls, calls)
        self.assertNotIn(owned, self.memory.freed)

    def test_failed_replacement_preserves_owned_node(self):
        source, owned = self.copy()
        before = self.snapshot()
        self.memory.fail_on_call = self.memory.calloc_calls + 1
        self.assertEqual(self.kit.pcc_kit_text_copy(self.node, 9, 8, source, 5, 7, 6), -2)
        self.assertEqual(self.snapshot(), before)
        self.assertNotIn(owned, self.memory.freed)

    def test_copy_from_self_and_interior_alias_precedes_release(self):
        _, original = self.copy(b"abcdef")
        self.assertEqual(self.kit.pcc_kit_text_copy(self.node, 0, 0, original, 6, 12, 1), 0)
        replacement = self.kit._n8(self.node, 120)
        self.assertEqual(self.memory.read(replacement, 7), b"abcdef\0")
        self.assertEqual(self.memory.freed.count(original), 1)
        self.assertEqual(self.kit.pcc_kit_text_copy(self.node, 0, 0, replacement + 2, 4, 12, 1), 0)
        final = self.kit._n8(self.node, 120)
        self.assertEqual(self.memory.read(final, 5), b"cdef\0")
        self.assertEqual(self.memory.freed.count(replacement), 1)

    def test_borrowed_and_owned_replacement_release_only_owned_storage(self):
        caller_owned = self.memory.source(b"borrowed")
        self.kit.pcc_kit_text(self.node, 0, 0, caller_owned, 8, 12, 1)
        self.assertEqual(self.kit._n8(self.node, 120), caller_owned)
        _, copied = self.copy(b"owned")
        self.assertNotIn(caller_owned, self.memory.freed)
        self.kit.pcc_kit_text(self.node, 0, 0, caller_owned, 8, 12, 1)
        self.assertEqual(self.memory.freed.count(copied), 1)
        self.assertEqual(self.kit._n8(self.node, 120), caller_owned)
        self.kit.pcc_kit_destroy_subtree(self.node)
        self.assertNotIn(caller_owned, self.memory.freed)
        self.assertEqual(self.memory.freed.count(copied), 1)

    def test_empty_text_releases_without_allocation_and_accepts_null(self):
        _, copied = self.copy()
        calls = self.memory.calloc_calls
        self.memory.fail_on_call = calls + 1
        self.assertEqual(self.kit.pcc_kit_text_copy(self.node, 4, 5, 0, 0, 12, 1), 0)
        self.assertEqual(self.memory.calloc_calls, calls)
        self.assertEqual(self.kit._n8(self.node, 120), 0)
        self.assertEqual(self.kit._n8(self.node, 104), 0)
        self.assertEqual(self.kit._n4(self.node, 88), 2)
        self.assertEqual(self.memory.freed.count(copied), 1)
        self.kit.pcc_kit_destroy_subtree(self.node)
        self.assertEqual(self.memory.freed.count(copied), 1)

    def test_rect_and_text_kind_preserve_ownership(self):
        _, copied = self.copy()
        self.kit.pcc_kit_rect(self.node, 1, 2, 30, 40, 5)
        self.assertEqual(self.kit.pcc_kit_node_kind(self.node, 2), 0)
        self.assertEqual(self.kit.pcc_kit_node_kind(self.node, 4), -1)
        self.assertEqual(self.kit._n8(self.node, 120), copied)
        self.assertEqual(self.kit._n4(self.node, 88), 2)
        self.assertNotIn(copied, self.memory.freed)
        self.assertEqual(self.memory.read(copied, 6), b"hello\0")

    def test_every_nontext_kind_change_releases_once(self):
        for kind in (0, 1, 3):
            with self.subTest(kind=kind):
                _, copied = self.copy()
                self.assertEqual(self.kit.pcc_kit_node_kind(self.node, kind), 0)
                self.assertEqual(self.kit.pcc_kit_node_kind(self.node, kind), 0)
                self.assertEqual(self.memory.freed.count(copied), 1)
                self.assertEqual(self.kit._n8(self.node, 120), 0)
                self.assertEqual(self.kit._n8(self.node, 104), 0)
        for on in (0, 1):
            with self.subTest(scroll=on):
                _, copied = self.copy()
                self.kit.pcc_kit_scroll_container(self.node, on)
                self.kit.pcc_kit_scroll_container(self.node, on)
                self.assertEqual(self.memory.freed.count(copied), 1)
                self.assertEqual(self.kit._n4(self.node, 88), 3 if on else 0)

    def test_subtree_removal_hook_and_slot_reuse_release_exactly_once(self):
        child = self.kit.pcc_kit_create(self.node)
        leaf = self.kit.pcc_kit_create(child)
        _, root_text = self.copy()
        _, child_text = self.copy(b"child", child)
        borrowed = self.memory.source(b"leaf")
        self.kit.pcc_kit_text(leaf, 0, 0, borrowed, 4, 12, 1)
        seen = []

        def on_remove(node):
            pointer = self.kit._n8(node, 120)
            self.memory.read(pointer, self.kit._n8(node, 104))
            seen.append(node)
            return 0

        self.memory.callbacks[77] = on_remove
        self.kit.pcc_kit_set_removal_hook(77)
        self.assertEqual(self.kit.pcc_kit_destroy_subtree(self.node), 3)
        self.assertEqual(seen, [leaf, child, self.node])
        self.assertEqual(self.memory.freed.count(root_text), 1)
        self.assertEqual(self.memory.freed.count(child_text), 1)
        self.assertNotIn(borrowed, self.memory.freed)
        self.assertEqual(self.kit.pcc_kit_destroy_subtree(self.node), -1)
        recycled = self.kit.pcc_kit_create(-1)
        self.assertNotEqual(recycled, self.node)
        self.assertEqual(self.kit._slot(recycled), self.kit._slot(self.node))
        self.assertEqual(self.kit._n8(recycled, 120), 0)
        _, recycled_text = self.copy(b"new", recycled)
        self.assertEqual(self.kit.pcc_kit_destroy_subtree(recycled), 1)
        self.assertEqual(self.memory.freed.count(recycled_text), 1)
        self.assertEqual(self.memory.freed.count(root_text), 1)

    def test_reinit_failures_preserve_all_state_and_success_releases_once(self):
        _, copied = self.copy()
        child = self.kit.pcc_kit_create(self.node)
        _, retired = self.copy(b"retired", child)
        self.kit.pcc_kit_destroy_subtree(child)
        self.kit.pcc_kit_focus(self.node)
        old_pool = self.memory.global_value("pcc_kit_pool")
        old_owners = self.memory.global_value("pcc_kit_owned_text")
        before = self.snapshot()
        for capacity in (0, -1, 8193):
            self.assertEqual(self.kit.pcc_kit_init(capacity), -1)
            self.assertEqual(self.snapshot(), before)
        for fail_at in (1, 2):
            with self.subTest(allocation=fail_at):
                self.memory.fail_on_call = self.memory.calloc_calls + fail_at
                self.assertEqual(self.kit.pcc_kit_init(4), -2)
                self.assertEqual(self.snapshot(), before)
                self.assertEqual(self.kit.pcc_kit_is_valid(self.node), 1)
                self.assertNotIn(copied, self.memory.freed)
        self.memory.fail_on_call = -1
        self.assertEqual(self.kit.pcc_kit_init(4), 0)
        for address in (copied, retired, old_pool, old_owners):
            self.assertEqual(self.memory.freed.count(address), 1)
        self.assertEqual(self.kit.pcc_kit_live_nodes(), 0)
        self.assertEqual(self.kit.pcc_kit_available_nodes(), 4)
        self.assertEqual(self.memory.global_value("pcc_kit_focus_node"), -1)
        self.assertEqual(self.kit.pcc_kit_init(4), 0)
        self.assertEqual(self.memory.freed.count(copied), 1)

    def test_initial_allocation_failure_leaves_uninitialized_state_safe(self):
        for fail_at in (1, 2):
            kit, memory, _ = load_kernel()
            before = {address: bytes(data) for address, data in memory.blocks.items()}
            memory.fail_on_call = fail_at
            self.assertEqual(kit.pcc_kit_init(2), -2)
            self.assertEqual({address: bytes(data) for address, data in memory.blocks.items()}, before)
            self.assertEqual(kit.pcc_kit_live_nodes(), 0)
            self.assertEqual(kit.pcc_kit_available_nodes(), 0)
            self.assertEqual(kit.pcc_kit_create(-1), -1)
            self.assertEqual(kit.pcc_kit_text_copy(0, 0, 0, 0, 0, 12, 1), -1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
