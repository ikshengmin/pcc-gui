"""Pure host tests of real GUI state/drawing code with a named fake native ABI.

These do not execute PCC intrinsics, compile modules, open a window, or prove
native pixels/GC. Pinned source contracts are recorded in the qualification.
"""

import importlib.util
from pathlib import Path
import struct
import sys
import types

import pytest

from gui_model import HarnessGuiState
from model_runtime import DeterministicModelProvider


PROJECT = Path(__file__).resolve().parents[1]


class FakeGuiABI:
    """Explicit test double for the existing raw native call boundary."""

    def __init__(self):
        self.next_pointer = 1
        self.heap = {}
        self.stack = set()
        self.freed = []
        self.nodes = {}
        self.next_node = 0
        self.log = []
        self.environment = {"PCC_HARNESS_GUI_BRIDGE": "fake-bridge"}
        self.clicks = []
        self.fail = {}
        self.copied_texts = []

    def allocate(self, count, size):
        pointer = self.next_pointer
        self.next_pointer += 1
        self.heap[pointer] = bytearray(count * size)
        return pointer

    def stack_alloc(self, size):
        pointer = self.allocate(1, size)
        self.stack.add(pointer)
        return pointer

    def free(self, pointer):
        if not pointer:
            return
        assert pointer in self.heap, "double free"
        self.freed.append(pointer)
        del self.heap[pointer]

    def store(self, pointer, offset, value, kind="q"):
        struct.pack_into("<" + kind, self.heap[pointer], offset, value)

    def load(self, pointer, offset, kind="q"):
        return struct.unpack_from("<" + kind, self.heap[pointer], offset)[0]

    def function(self, name):
        def invoke(*args):
            self.log.append(name)
            failure = self.fail.get(name)
            if isinstance(failure, Exception):
                raise failure
            if failure is not None:
                return failure
            if name == "getenv":
                return self.environment.get(args[0], 0)
            if name == "pcc_kit_init":
                assert not self.nodes
                return 0
            if name == "pcc_kit_create":
                node = self.next_node
                self.next_node += 1
                self.nodes[node] = {"parent": args[0], "text": None}
                return node
            if name == "pcc_kit_destroy_subtree":
                count = len(self.nodes)
                self.nodes.clear()
                return count
            if name == "pcc_kit_rect":
                self.nodes[args[0]]["rect"] = args[1:]
            if name in ("pcc_kit_text", "pcc_kit_text_copy"):
                _, x, y, text, length, size, color = args
                assert len(text.encode("utf-8")) == length
                self.nodes[args[0]]["text"] = text
                self.nodes[args[0]]["position"] = (x, y)
                if name == "pcc_kit_text_copy":
                    self.copied_texts.append((text, length))
            if name == "pcc_kit_render":
                _, rects, colors, rect_count, texts, text_count = args
                self.store(rect_count, 0, sum("rect" in node for node in self.nodes.values()))
                self.store(text_count, 0, sum(node["text"] is not None for node in self.nodes.values()))
            if name == "pcc_gui_commands_completion":
                self.store(args[1], 8, 1, "i")
            if name == "running":
                return int(bool(self.clicks))
            if name == "poll_click":
                if not self.clicks:
                    return 0
                x, y = self.clicks.pop(0)
                self.store(args[0], 0, x)
                self.store(args[1], 0, y)
                return 1
            return 0
        return invoke

    def labels(self):
        return [node["text"] for node in self.nodes.values() if node["text"] is not None]

    def assert_no_allocations(self):
        assert set(self.heap) <= self.stack


def load_app(monkeypatch):
    abi = FakeGuiABI()
    extern = types.ModuleType("pcc.extern")
    for name in ("c_rawptr", "c_int32", "c_int64", "c_ptr", "c_str", "c_void"):
        setattr(extern, name, object())
    extern.extern = lambda name, *args: abi.function(name)
    extern.c_abi_typed_export = lambda *args: lambda function: function
    unsafe = types.ModuleType("pcc.unsafe")
    unsafe.calloc = abi.allocate
    unsafe.cstr = lambda text: text
    unsafe.free = abi.free
    unsafe.function_addr = lambda name: 1
    unsafe.load_i32 = lambda pointer, offset: abi.load(pointer, offset, "i")
    unsafe.load_i64 = abi.load
    unsafe.null = lambda: 0
    unsafe.ptr_is_null = lambda pointer: pointer == 0
    unsafe.stack_alloc = abi.stack_alloc
    unsafe.store_i32 = lambda pointer, offset, value: abi.store(pointer, offset, value, "i")
    unsafe.store_i64 = abi.store
    unsafe.store_ptr = abi.store
    bridge = types.ModuleType("gui_bridge")
    for name in ("init", "close", "capture", "running", "sleep", "render_ack", "render_scene", "poll_click"):
        setattr(bridge, name, abi.function(name))
    for name, module in [("pcc_gui", types.ModuleType("pcc_gui")), ("pcc", types.ModuleType("pcc")),
                         ("pcc.extern", extern), ("pcc.unsafe", unsafe), ("gui_bridge", bridge)]:
        monkeypatch.setitem(sys.modules, name, module)
    spec = importlib.util.spec_from_file_location("harness_gui_app_host_probe", PROJECT / "gui_app.py")
    app = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(app)
    return app, abi


def test_distinct_submissions_reach_canonical_projection_and_actual_drawing(monkeypatch):
    app, abi = load_app(monkeypatch)
    resources = app._GuiResources()
    state = HarnessGuiState()
    resources.state = state
    try:
        first = "  first draft\nkept verbatim  "
        second = "different café 世界"
        state.submit(first)
        app.build_scene(state, resources)
        assert first in abi.labels()
        assert "8 logged events  |  completed" in abi.labels()
        state.submit(second)
        app.build_scene(state, resources)
        labels = abi.labels()
        assert first in labels and second in labels
        assert "PCC harness is running. You said: " + second in labels
        assert "hello from pcc gui" not in labels
        assert "16 logged events  |  completed" in labels
        assert (second, len(second.encode("utf-8"))) in abi.copied_texts
        assert state.render_model().event_count == state.runtime.session.count() == 16
    finally:
        assert resources.dispose() is None
    abi.assert_no_allocations()


def test_blank_busy_and_closed_sends_never_dispatch_commands(monkeypatch):
    app, abi = load_app(monkeypatch)
    state = HarnessGuiState()
    try:
        assert not app._submit_text(state, " \n\t ", 1)
        state.runtime.session.start_turn()
        assert state.status == "Running"
        assert not app._submit_text(state, "busy", 2)
        state.runtime.session.end_turn("aborted")
        state.dispose()
        assert not app._submit_text(state, "closed", 3)
        assert "pcc_gui_commands_invoke" not in abi.log
        assert state.render_model().messages == []
    finally:
        state.dispose()


def test_painted_submit_rectangles_control_actual_dispatch(monkeypatch):
    app, abi = load_app(monkeypatch)
    state = HarnessGuiState()
    try:
        assert app._dispatch_click(state, 1120, 750, 1) == 0
        assert "pcc_gui_commands_invoke" not in abi.log
        assert app._dispatch_click(state, 1120, 470, 1) == 2
        assert state.runtime.session.count() == 8
        assert app._dispatch_click(state, 1120, 470, 2) == 0
        assert app._dispatch_click(state, 1120, 750, 2) == 2
        assert abi.log.count("pcc_gui_commands_invoke") == 2
        assert state.runtime.session.count() == 16
        assert app._dispatch_click(state, 1154, 750, 3) == 0
        assert app._dispatch_click(state, 1120, 780, 3) == 0
        assert app._dispatch_click(state, 15, 75, 3) == 1
        assert state.phase == "hero" and state.transcript() == []
        state.dispose()
        assert app._dispatch_click(state, 15, 75, 4) == 0
    finally:
        state.dispose()
    abi.assert_no_allocations()


def test_command_failure_does_not_submit_and_releases_temporary_buffers(monkeypatch):
    app, abi = load_app(monkeypatch)
    state = HarnessGuiState()
    try:
        abi.fail["pcc_gui_commands_invoke"] = -8
        assert not app._submit_text(state, "not accepted", 1)
        assert state.transcript() == []
        abi.fail["pcc_gui_commands_invoke"] = RuntimeError("command failed")
        with pytest.raises(RuntimeError, match="command failed"):
            app._submit_text(state, "not accepted", 2)
    finally:
        state.dispose()
    abi.assert_no_allocations()


def test_session_replacement_during_old_turn_never_projects_stale_result(monkeypatch):
    state = HarnessGuiState()
    old_agent = state.agent
    original = old_agent.run_turn

    def replace_then_complete(text):
        state.new_session()
        old_agent.cancelled = False
        # Simulate a provider that ignores cancellation. Its recorded result
        # still belongs exclusively to the replaced session.
        old_agent.cancellation.cancelled = False
        return original(text)

    monkeypatch.setattr(old_agent, "run_turn", replace_then_complete)
    try:
        state.submit("old session only")
        assert old_agent is not state.agent
        assert state.phase == "hero" and state.status == "Ready"
        assert state.transcript() == [] and state.render_model().messages == []
        state.submit("new session only")
        assert "old session only" not in "\n".join(state.transcript())
        assert state.render_model().messages[0].content == "new session only"
    finally:
        state.dispose()


def test_provider_error_keeps_logged_failure_and_releases_submit_guard(monkeypatch):
    state = HarnessGuiState()
    provider = DeterministicModelProvider()

    def fail(request):
        raise RuntimeError("provider failed")

    monkeypatch.setattr(provider, "complete", fail)
    state.runtime.models.register("failing", provider)
    state.runtime.config.provider = "failing"
    try:
        with pytest.raises(RuntimeError, match="provider failed"):
            state.submit("retained input")
        assert state.status == "error"
        assert state.can_submit("retry")
        assert state.render_model().messages[0].content == "retained input"
        assert state.render_model().last_turn_reason == "error"
    finally:
        state.dispose()


def test_dispose_is_once_even_when_runtime_cleanup_fails(monkeypatch):
    state = HarnessGuiState()
    dispose = state.runtime.dispose
    calls = []

    def fail_after_dispose():
        calls.append("disposed")
        dispose()
        raise RuntimeError("cleanup failed")

    monkeypatch.setattr(state.runtime, "dispose", fail_after_dispose)
    with pytest.raises(RuntimeError, match="cleanup failed"):
        state.dispose()
    state.dispose()
    assert calls == ["disposed"]
    assert state.status == "Closed"
    assert state.agent.cancelled


@pytest.mark.parametrize("path", ["normal", "capture", "render-error", "scene-error", "self-check", "self-check-error"])
def test_all_application_exits_dispose_runtime_scene_commands_buffers_and_bridge(monkeypatch, path):
    app, abi = load_app(monkeypatch)
    states = []
    original = app.HarnessGuiState

    def create_state():
        state = original()
        states.append(state)
        state.dispose_count = 0
        dispose = state.runtime.dispose

        def counted_dispose():
            state.dispose_count += 1
            dispose()
        monkeypatch.setattr(state.runtime, "dispose", counted_dispose)
        return state

    monkeypatch.setattr(app, "HarnessGuiState", create_state)
    if path == "capture":
        abi.environment["PCC_HARNESS_GUI_CAPTURE"] = "capture.png"
    if path == "render-error":
        abi.fail["render_scene"] = RuntimeError("paint failed")
    if path == "scene-error":
        abi.fail["pcc_kit_text_copy"] = -2
    if path == "self-check-error":
        abi.fail["pcc_gui_commands_invoke"] = -3
    if path in ("render-error", "scene-error"):
        with pytest.raises(RuntimeError):
            app.run_gui()
    elif path.startswith("self-check"):
        assert app.gui_self_check() == (2 if path.endswith("error") else 0)
    else:
        assert app.run_gui() == 0
    assert len(states) == 1 and states[0].closed
    assert states[0].dispose_count == 1
    assert states[0].agent.cancelled
    assert abi.log.count("pcc_gui_commands_shutdown") == 1
    assert abi.log.count("close") == (0 if path.startswith("self-check") else 1)
    assert not abi.nodes
    abi.assert_no_allocations()


def test_cleanup_failure_does_not_replace_primary_error_and_other_owners_finish(monkeypatch):
    app, abi = load_app(monkeypatch)
    resources = app._GuiResources()
    resources.state = HarnessGuiState()
    resources.commands_started = True
    resources.native_started = True
    app.build_scene(resources.state, resources)
    resources.allocate_render_buffers()
    primary = RuntimeError("primary paint failure")
    abi.fail["pcc_gui_commands_shutdown"] = RuntimeError("secondary command failure")
    with pytest.raises(RuntimeError) as raised:
        app._finish(resources, 0, primary)
    assert raised.value is primary
    assert abi.log.count("close") == 1
    assert resources.state.closed and not abi.nodes
    assert resources.dispose() is None
    abi.assert_no_allocations()


def test_partial_buffer_allocation_and_command_initialization_are_cleaned(monkeypatch):
    app, abi = load_app(monkeypatch)
    allocated = 0
    original = app.calloc

    def fail_second(count, size):
        nonlocal allocated
        allocated += 1
        return 0 if allocated == 2 else original(count, size)

    monkeypatch.setattr(app, "calloc", fail_second)
    with pytest.raises(MemoryError, match="color allocation"):
        app.run_gui()
    abi.assert_no_allocations()
    assert not abi.nodes and abi.log.count("close") == 1

    app, abi = load_app(monkeypatch)
    abi.fail["pcc_gui_commands_register"] = -1
    assert app.run_gui() == 22
    assert abi.log.count("pcc_gui_commands_shutdown") == 1
    assert abi.log.count("close") == 1


def load_bridge():
    """Execute the real bridge with explicit fake symbols, never PCC imports."""
    import ast

    abi = FakeGuiABI()
    globals_by_name = {}
    symbols = {}
    calls = []

    def define_global(name, *values):
        pointer = abi.allocate(len(values), 8)
        globals_by_name[name] = pointer
        for index, value in enumerate(values):
            abi.store(pointer, index * 8, value)

    def symbol(handle, name):
        pointer = 10000 + len(symbols)
        symbols[pointer] = name
        return pointer

    def call(pointer, *arguments):
        name = symbols[pointer]
        if name == "pcc_gui_metal_window_text":
            params = arguments[2]
            calls.append((name, abi.load(params, 0), arguments[1], arguments[3]))
        else:
            calls.append((name, *arguments))
        failure = abi.fail.get(name)
        if failure is not None:
            raise failure
        return 9000 if name == "pcc_gui_metal_window_create" else 0

    def call_typed(pointer, restype, argtypes, values, result):
        assert restype == "i64"
        assert argtypes == ()
        assert values == ()
        abi.store(result, 0, call(pointer, *values))

    namespace = {
        "call_c_abi": call_typed,
        "c_int64": object(),
        "extern": lambda name, *args: abi.function(name),
        "cstr": lambda value: value,
        "define_global_i64_array": define_global,
        "dynamic_library_open": lambda path: 1,
        "dynamic_library_symbol": symbol,
        "global_addr": lambda name: globals_by_name[name],
        "int_to_ptr": lambda value: value,
        "ptr_to_int": lambda value: value,
        "load_i64": abi.load,
        "load_ptr": abi.load,
        "null": lambda: 0,
        "ptr_is_null": lambda value: value == 0,
        "stack_alloc": abi.stack_alloc,
        "store_i64": abi.store,
        "call_i64_ptr1": call,
        "call_i64_ptr2": call,
        "call_i64_ptr3": call,
        "call_i64_ptr3_i64_i64_i64": call,
        "call_ptr_i64_i64": call,
    }
    path = PROJECT / "gui_bridge.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    tree.body = [
        statement for statement in tree.body
        if not isinstance(statement, (ast.Import, ast.ImportFrom))
    ]
    exec(compile(tree, str(path), "exec"), namespace)
    return types.SimpleNamespace(**namespace), abi, calls


def test_bridge_clears_every_old_slot_when_projection_shrinks():
    bridge, abi, calls = load_bridge()
    assert bridge.init("Harness", 1280, 800, "fake-bridge") == 0
    records = abi.allocate(90, bridge.TEXT_RECORD_BYTES)
    for index in range(90):
        base = index * bridge.TEXT_RECORD_BYTES
        abi.store(records, base + bridge.TEXT_LENGTH_OFFSET, 1)
        abi.store(records, base + bridge.TEXT_FONT_OFFSET, 12)
        abi.store(records, base + bridge.TEXT_POINTER_OFFSET, 1)
    bridge.render_scene(0, 0, 0, records, 90)
    calls.clear()
    bridge.render_scene(0, 0, 0, records, 2)
    text_calls = [call for call in calls if call[0] == "pcc_gui_metal_window_text"]
    assert len(text_calls) == 90
    assert [call[1] for call in text_calls if call[2] == 0] == list(range(2, 90))
    calls.clear()
    bridge.render_scene(0, 0, 0, records, 2)
    assert len([call for call in calls if call[0] == "pcc_gui_metal_window_text"]) == 2
    bridge.close()


@pytest.mark.parametrize("fails", [False, True])
def test_bridge_close_revokes_handle_once_and_reopen_starts_clean(fails):
    bridge, abi, calls = load_bridge()
    assert bridge.init("Harness", 1280, 800, "fake-bridge") == 0
    assert bridge.init("duplicate", 1280, 800, "fake-bridge") == -4
    if fails:
        abi.fail["pcc_gui_metal_window_close"] = RuntimeError("platform close failed")
        with pytest.raises(RuntimeError, match="platform close failed"):
            bridge.close()
    else:
        bridge.close()
    bridge.close()
    assert len([call for call in calls if call[0] == "pcc_gui_metal_window_close"]) == 1
    calls.clear()
    assert bridge.running() == 0
    assert bridge.poll_click(0, 0) == 0
    assert bridge.capture("unused.png") == -1
    bridge.render_scene(0, 0, 0, 0, 0)
    assert calls == []
    abi.fail.clear()
    assert bridge.init("Harness", 1280, 800, "fake-bridge") == 0
    assert bridge._g(bridge.TEXT_COUNT_SLOT) == 0
    assert bridge.render_ack() == -1
    bridge.close()


def test_bridge_rejects_out_of_range_text_count_before_native_dispatch():
    bridge, abi, calls = load_bridge()
    assert bridge.init("Harness", 1280, 800, "fake-bridge") == 0
    calls.clear()
    for invalid in (-1, bridge.NATIVE_TEXT_CAPACITY + 1):
        with pytest.raises(ValueError, match="slot capacity"):
            bridge.render_scene(0, 0, 0, 0, invalid)
    assert calls == []
    bridge.close()


def test_interruption_preserves_primary_exception_and_finishes_cleanup(monkeypatch):
    app, abi = load_app(monkeypatch)
    interruption = KeyboardInterrupt("interrupted paint")
    states = []
    original = app.HarnessGuiState

    def state_factory():
        state = original()
        states.append(state)
        return state

    def interrupt_render(*args):
        raise interruption

    monkeypatch.setattr(app, "HarnessGuiState", state_factory)
    monkeypatch.setattr(app.native, "render_scene", interrupt_render)
    with pytest.raises(KeyboardInterrupt) as raised:
        app.run_gui()
    assert raised.value is interruption
    assert states[0].closed
    assert not abi.nodes
    assert abi.log.count("pcc_gui_commands_shutdown") == 1
    assert abi.log.count("close") == 1
    abi.assert_no_allocations()


def test_interrupted_cleanup_still_releases_remaining_owners(monkeypatch):
    app, abi = load_app(monkeypatch)
    resources = app._GuiResources()
    resources.state = HarnessGuiState()
    resources.commands_started = True
    resources.native_started = True
    app.build_scene(resources.state, resources)
    resources.allocate_render_buffers()
    interruption = KeyboardInterrupt("interrupted command shutdown")

    def interrupt_shutdown():
        raise interruption

    monkeypatch.setattr(app, "commands_shutdown", interrupt_shutdown)
    assert resources.dispose() is interruption
    assert resources.state.closed and not abi.nodes
    assert abi.log.count("close") == 1
    assert resources.dispose() is None
    abi.assert_no_allocations()


def test_bridge_pump_uses_declared_no_argument_c_abi():
    bridge, abi, calls = load_bridge()
    declaration = (
        PROJECT.parents[1] / "pcc_gui" / "native" / "pcc_gui_metal_render_bridge.m"
    ).read_text()
    assert "int64_t pcc_gui_metal_run_loop_pump(void)" in declaration
    try:
        assert bridge.init("Harness", 1280, 800, "fake-bridge") == 0
        assert bridge.running() == 1
        pump_calls = [call for call in calls if call[0] == "pcc_gui_metal_run_loop_pump"]
        assert pump_calls == [
            ("pcc_gui_metal_run_loop_pump",),
            ("pcc_gui_metal_run_loop_pump",),
        ]
    finally:
        bridge.close()
