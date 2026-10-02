"""Declarative PCC native GUI shell for the Python Harness port."""

import pcc_gui  # noqa: F401  pcc1 compiles the framework into this program's closure
from pcc.extern import (
    c_rawptr,
    c_abi_typed_export,
    c_int32,
    c_int64,
    c_ptr,
    c_str,
    c_void,
    extern,
)
from pcc.unsafe import (
    calloc,
    cstr,
    free,
    function_addr,
    load_i32,
    load_i64,
    null,
    ptr_is_null,
    stack_alloc,
    store_i32,
    store_i64,
    store_ptr,
)

import gui_bridge as native
from gui_model import HarnessGuiState


getenv = extern("getenv", (c_ptr,), c_rawptr)
fflush = extern("fflush", (c_ptr,), c_int32)

kit_init = extern("pcc_kit_init", (c_int64,), c_int32)
kit_create = extern("pcc_kit_create", (c_int64,), c_int64)
kit_destroy = extern("pcc_kit_destroy_subtree", (c_int64,), c_int64)
kit_rect = extern(
    "pcc_kit_rect",
    (c_int64, c_int64, c_int64, c_int64, c_int64, c_int32),
    c_void,
)
kit_text = extern(
    "pcc_kit_text",
    (c_int64, c_int64, c_int64, c_ptr, c_int64, c_int64, c_int32),
    c_void,
)
kit_text_copy = extern(
    "pcc_kit_text_copy",
    (c_int64, c_int64, c_int64, c_str, c_int64, c_int64, c_int32),
    c_int32,
)
kit_render = extern(
    "pcc_kit_render", (c_int64, c_ptr, c_ptr, c_ptr, c_ptr, c_ptr), c_void
)

commands_init = extern(
    "pcc_gui_commands_init", (c_int64, c_int64, c_int64, c_int64), c_int32
)
command_register = extern(
    "pcc_gui_commands_register",
    (c_int32, c_ptr, c_int32, c_int32, c_int64, c_int64),
    c_int32,
)
command_invoke = extern("pcc_gui_commands_invoke", (c_ptr,), c_int32)
resolve_result = extern(
    "pcc_gui_commands_resolve_result", (c_int64, c_ptr, c_int64), c_int32
)
command_completion = extern(
    "pcc_gui_commands_completion", (c_int64, c_ptr), c_int32
)
release_completion = extern(
    "pcc_gui_commands_release_completion", (c_int64,), c_int32
)
commands_shutdown = extern("pcc_gui_commands_shutdown", (), c_int64)


WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 800
SIDEBAR_WIDTH = 280
RENDER_CAPACITY = 512
NEW_SESSION_X = 14
NEW_SESSION_Y = 74
NEW_SESSION_WIDTH = 252
NEW_SESSION_HEIGHT = 38
COMPOSER_X = 390
COMPOSER_WIDTH = 780
COMPOSER_HERO_Y = 388
COMPOSER_ACTIVE_Y = 666
SUBMIT_OFFSET_X = 728
SUBMIT_OFFSET_Y = 78
SUBMIT_SIZE = 36

BG = 0xFFFFFFFF
SIDEBAR = 0xFFF9FAFB
INK = 0xFF0F1115
SECONDARY = 0xFF61666B
CAPTION = 0xFFADB2B8
BORDER = 0xFFE6E8EB
BLUE = 0xFF4176E6
BLUE_PALE = 0xFFE4EDFD
INPUT = 0xFFFFFFFF
USER_BUBBLE = 0xFFEDF3FE


def _rect(parent: int, x: int, y: int, width: int, height: int, color: int) -> int:
    node = kit_create(parent)
    if node < 0:
        raise RuntimeError("Harness scene exceeds the current kernel capacity")
    kit_rect(node, x, y, width, height, color)
    return node


def _text(parent: int, x: int, y: int, value, length: int, size: int, color: int) -> int:
    node = kit_create(parent)
    if node < 0:
        raise RuntimeError("Harness scene exceeds the current kernel capacity")
    kit_text(node, x, y, value, length, size, color)
    return node


def _projected_text(parent: int, x: int, y: int, value: str, size: int, color: int) -> int:
    node = kit_create(parent)
    if node < 0:
        raise RuntimeError("Harness scene exceeds the current kernel capacity")
    # c_str leases the UTF-8 input only for this call. The canonical kernel
    # copies it and owns the bytes through replacement/destruction/re-init.
    if kit_text_copy(node, x, y, value, len(value.encode("utf-8")), size, color) != 0:
        raise RuntimeError("failed to copy Harness scene text")
    return node


def _build_sidebar(root: int, state: HarnessGuiState, projection) -> None:
    sidebar = _rect(root, 0, 0, SIDEBAR_WIDTH, WINDOW_HEIGHT, SIDEBAR)
    _rect(root, SIDEBAR_WIDTH - 1, 0, 1, WINDOW_HEIGHT, BORDER)
    _text(sidebar, 20, 24, cstr("deepseek"), 8, 20, INK)
    _text(sidebar, 238, 27, cstr("<<"), 2, 14, SECONDARY)
    _rect(
        sidebar,
        NEW_SESSION_X,
        NEW_SESSION_Y,
        NEW_SESSION_WIDTH,
        NEW_SESSION_HEIGHT,
        BG,
    )
    _text(sidebar, 30, 84, cstr("+  New Session"), 14, 14, INK)
    _text(sidebar, 18, 142, cstr("Workspaces"), 10, 12, CAPTION)
    _rect(sidebar, 14, 168, 252, 34, 0xFFF1F3F5)
    _text(sidebar, 28, 177, cstr("pcc"), 3, 14, INK)
    _text(sidebar, 18, 222, cstr("Sessions"), 8, 12, CAPTION)
    _rect(sidebar, 14, 248, 252, 42, BLUE_PALE)
    _projected_text(sidebar, 28, 259, projection.title, 14, INK)
    _text(sidebar, 28, 740, cstr("Settings"), 8, 14, SECONDARY)
    _projected_text(sidebar, 196, 740, state.status, 12, CAPTION)


def _build_composer(root: int, active: int) -> None:
    x = COMPOSER_X
    y = COMPOSER_ACTIVE_Y if active != 0 else COMPOSER_HERO_Y
    width = COMPOSER_WIDTH
    _rect(root, x, y, width, 126, 0xFFE6E8EB)
    _rect(root, x + 1, y + 1, width - 2, 124, INPUT)
    if active != 0:
        _text(root, x + 18, y + 18, cstr("Ask a follow-up"), 15, 16, CAPTION)
    else:
        _text(
            root,
            x + 18,
            y + 18,
            cstr("What can I help you build?"),
            26,
            16,
            CAPTION,
        )
    _text(root, x + 18, y + 91, cstr("+"), 1, 18, SECONDARY)
    _text(root, x + 52, y + 92, cstr("Read-only"), 9, 13, SECONDARY)
    _text(root, x + 604, y + 92, cstr("DeepSeek"), 8, 13, SECONDARY)
    _rect(root, x + SUBMIT_OFFSET_X, y + SUBMIT_OFFSET_Y, SUBMIT_SIZE, SUBMIT_SIZE, BLUE)
    _text(root, x + 740, y + 86, cstr("^"), 1, 18, BG)


def _build_hero(root: int) -> None:
    _text(root, 620, 299, cstr("<>"), 2, 26, INK)
    _text(root, 660, 295, cstr("DeepSeek Harness"), 16, 26, INK)
    _rect(root, 870, 296, 68, 22, BLUE_PALE)
    _text(root, 880, 299, cstr("Preview"), 7, 12, 0xFF0E3074)
    _text(root, 398, 352, cstr("Choose workspace  v"), 19, 13, INK)
    _build_composer(root, 0)


def _build_active(root: int, projection) -> None:
    _projected_text(root, 300, 22, projection.title, 14, INK)
    _text(root, 308, 62, cstr("Chat"), 4, 13, BLUE)
    _text(root, 378, 62, cstr("Trajectory"), 10, 13, SECONDARY)
    _rect(root, 300, 84, 952, 1, BORDER)
    y = 146
    for message in projection.messages:
        if message.role == "user":
            _rect(root, 720, y, 420, 42, USER_BUBBLE)
            _projected_text(root, 742, y + 12, message.content, 15, INK)
            y += 86
        else:
            label = projection.request_model
            if message.role == "tool" or message.role == "assistant-tool-call":
                label = message.name
            _projected_text(root, 410, y, label, 13, SECONDARY)
            text = message.content
            if message.role == "assistant-tool-call":
                text = message.arguments
            _projected_text(root, 410, y + 28, text, 15, INK)
            y += 86
    _projected_text(
        root, 410, y,
        str(projection.event_count) + " logged events  |  " + projection.last_turn_reason,
        12, CAPTION,
    )
    _build_composer(root, 1)


def build_scene(state: HarnessGuiState, resources) -> int:
    resources.destroy_scene()
    if kit_init(RENDER_CAPACITY) != 0:
        return -1
    root = kit_create(-1)
    if root < 0:
        return -1
    # Publish ownership before any fallible dynamic text copy. Cleanup owns
    # this partial tree even when scene construction never returns normally.
    resources.root = root
    projection = state.render_model()
    kit_rect(root, 0, 0, WINDOW_WIDTH, WINDOW_HEIGHT, BG)
    _build_sidebar(root, state, projection)
    if state.phase == "active":
        _build_active(root, projection)
    else:
        _build_hero(root)
    return root


@c_abi_typed_export("harness_gui_submit_command", "i32", ("ptr", "i64"))
def harness_gui_submit_command(invoke, resolver: int) -> int:
    return resolve_result(resolver, null(), 0)


def _init_commands() -> int:
    if commands_init(8, 8, 8, 8) != 0:
        return -1
    return command_register(
        1, function_addr("harness_gui_submit_command"), 0, 0, 0, 0
    )


def _invoke_submit(request_id: int) -> int:
    packet = calloc(1, 64)
    error = calloc(1, 24)
    completion = calloc(1, 48)
    try:
        if ptr_is_null(packet) or ptr_is_null(error) or ptr_is_null(completion):
            return -1
        store_i64(packet, 0, request_id)
        store_i32(packet, 8, 1)
        store_i32(packet, 12, 0)
        store_i64(packet, 16, 1)
        store_ptr(packet, 24, null())
        store_i64(packet, 32, 0)
        store_i64(packet, 40, 0)
        store_i64(packet, 48, request_id)
        store_ptr(packet, 56, error)
        invoked = command_invoke(packet)
        if invoked != 0:
            return invoked
        completed = command_completion(request_id, completion)
        if completed != 0:
            return completed
        if load_i32(completion, 8) != 1:
            return load_i32(completion, 8) - 1000
        return release_completion(request_id)
    finally:
        free(completion)
        free(error)
        free(packet)


def _render(root: int, rects, colors, texts, rect_count, text_count) -> None:
    store_i64(rect_count, 0, 0)
    store_i64(text_count, 0, 0)
    kit_render(root, rects, colors, rect_count, texts, text_count)
    native.render_scene(
        rects,
        colors,
        load_i64(rect_count, 0),
        texts,
        load_i64(text_count, 0),
    )


class _GuiResources:
    """Application lifetime over existing runtime, kernel and native owners."""

    def __init__(self) -> None:
        self.state = None
        self.root = -1
        self.commands_started = False
        self.native_started = False
        self.rects = null()
        self.colors = null()
        self.texts = null()
        self.closed = False

    def allocate_render_buffers(self) -> None:
        self.rects = calloc(RENDER_CAPACITY, 32)
        if ptr_is_null(self.rects):
            raise MemoryError("Harness rectangle allocation failed")
        self.colors = calloc(RENDER_CAPACITY, 4)
        if ptr_is_null(self.colors):
            raise MemoryError("Harness color allocation failed")
        self.texts = calloc(RENDER_CAPACITY, 48)
        if ptr_is_null(self.texts):
            raise MemoryError("Harness text-record allocation failed")

    def destroy_scene(self) -> None:
        root = self.root
        self.root = -1
        if root >= 0 and kit_destroy(root) <= 0:
            # Kernel-owned text remains with any unreleased nodes. Never free
            # retained payloads independently or retry an uncertain release.
            raise RuntimeError("Harness scene destruction failed")

    def dispose(self):
        if self.closed:
            return None
        self.closed = True
        failure = None
        try:
            if self.state is not None:
                self.state.dispose()
        except BaseException as error:
            failure = error
        try:
            self.destroy_scene()
        except BaseException as error:
            if failure is None:
                failure = error
        try:
            if self.commands_started:
                self.commands_started = False
                if commands_shutdown() != 0:
                    raise RuntimeError("Harness command shutdown failed")
        except BaseException as error:
            if failure is None:
                failure = error
        for pointer in [self.texts, self.colors, self.rects]:
            try:
                if not ptr_is_null(pointer):
                    free(pointer)
            except BaseException as error:
                if failure is None:
                    failure = error
        self.texts = null()
        self.colors = null()
        self.rects = null()
        try:
            if self.native_started:
                self.native_started = False
                native.close()
        except BaseException as error:
            if failure is None:
                failure = error
        return failure


def _finish(resources, result: int, failure) -> int:
    cleanup_failure = resources.dispose()
    if failure is not None:
        raise failure
    if cleanup_failure is not None:
        if result == 0:
            raise cleanup_failure
        print("HARNESS_GUI_CLEANUP_FAILED", str(cleanup_failure))
    return result


def _submit_text(state: HarnessGuiState, text: str, request_id: int) -> bool:
    if not state.can_submit(text):
        return False
    if _invoke_submit(request_id) != 0:
        return False
    state.submit(text)
    return True


def _click_action(state: HarnessGuiState, x: int, y: int) -> int:
    """Only the current painted controls are eligible for command dispatch."""
    if state.closed:
        return 0
    if (
        x >= NEW_SESSION_X
        and x < NEW_SESSION_X + NEW_SESSION_WIDTH
        and y >= NEW_SESSION_Y
        and y < NEW_SESSION_Y + NEW_SESSION_HEIGHT
    ):
        return 1
    if not state.can_submit("hello from pcc gui"):
        return 0
    composer_y = COMPOSER_ACTIVE_Y if state.phase == "active" else COMPOSER_HERO_Y
    submit_x = COMPOSER_X + SUBMIT_OFFSET_X
    submit_y = composer_y + SUBMIT_OFFSET_Y
    if (
        x >= submit_x
        and x < submit_x + SUBMIT_SIZE
        and y >= submit_y
        and y < submit_y + SUBMIT_SIZE
    ):
        return 2
    return 0


def _dispatch_click(state: HarnessGuiState, x: int, y: int, request_id: int) -> int:
    action = _click_action(state, x, y)
    if action == 1:
        state.new_session()
        return 1
    if action == 2 and _submit_text(state, "hello from pcc gui", request_id):
        return 2
    return 0


def _gui_self_check(resources) -> int:
    resources.state = HarnessGuiState()
    state = resources.state
    if state.visible_regions() != [
        "sidebar", "session-navigation", "trajectory", "composer", "status", "settings",
    ]:
        return 1
    resources.commands_started = True
    command_status = _init_commands()
    if command_status != 0:
        print("HARNESS_GUI_COMMAND_INIT_FAILED", command_status)
        return 2
    if not _submit_text(state, "hello from pcc gui", 1):
        print("HARNESS_GUI_COMMAND_INVOKE_FAILED")
        return 2
    if state.transcript()[-1] != "assistant: PCC harness is running. You said: hello from pcc gui":
        return 3
    if state.agent.session.count() != 8:
        return 4
    if build_scene(state, resources) < 0:
        return 5
    resources.allocate_render_buffers()
    rect_count = stack_alloc(8)
    text_count = stack_alloc(8)
    store_i64(rect_count, 0, 0)
    store_i64(text_count, 0, 0)
    kit_render(resources.root, resources.rects, resources.colors, rect_count, resources.texts, text_count)
    if load_i64(rect_count, 0) < 9 or load_i64(text_count, 0) < 15:
        print("HARNESS_GUI_RENDER_COUNTS", load_i64(rect_count, 0), load_i64(text_count, 0))
        fflush(null())
        return 6
    return 0


def gui_self_check() -> int:
    resources = _GuiResources()
    result = 0
    failure = None
    try:
        result = _gui_self_check(resources)
    except BaseException as error:
        failure = error
    result = _finish(resources, result, failure)
    if result == 0:
        print("HARNESS_GUI_SELF_CHECK_OK")
    return result


def _run_gui(resources) -> int:
    bridge = getenv(cstr("PCC_HARNESS_GUI_BRIDGE"))
    if ptr_is_null(bridge):
        print("PCC_HARNESS_GUI_BRIDGE is not set")
        return 20
    resources.native_started = True
    if native.init(cstr("DeepSeek Harness"), WINDOW_WIDTH, WINDOW_HEIGHT, bridge) != 0:
        print("failed to initialize PCC native GUI")
        return 21
    resources.commands_started = True
    if _init_commands() != 0:
        return 22

    resources.state = HarnessGuiState()
    state = resources.state
    if build_scene(state, resources) < 0:
        return 23
    resources.allocate_render_buffers()
    rect_count = stack_alloc(8)
    text_count = stack_alloc(8)
    click_x = stack_alloc(8)
    click_y = stack_alloc(8)
    request_id = 1

    autosubmit = getenv(cstr("PCC_HARNESS_GUI_AUTOSUBMIT"))
    if not ptr_is_null(autosubmit):
        if _submit_text(state, "hello from pcc gui", request_id):
            request_id += 1
            if build_scene(state, resources) < 0:
                return 23

    _render(resources.root, resources.rects, resources.colors, resources.texts, rect_count, text_count)
    attempts = 0
    while native.render_ack() != 0 and attempts < 60:
        if native.running() == 0:
            return 0
        native.sleep(16)
        _render(resources.root, resources.rects, resources.colors, resources.texts, rect_count, text_count)
        attempts += 1

    capture_path = getenv(cstr("PCC_HARNESS_GUI_CAPTURE"))
    if not ptr_is_null(capture_path):
        result = native.capture(capture_path)
        print("HARNESS_GUI_CAPTURE", result)
        return result

    while native.running() != 0:
        if native.poll_click(click_x, click_y) != 0:
            action = _dispatch_click(state, load_i64(click_x, 0), load_i64(click_y, 0), request_id)
            if action != 0:
                if action == 2:
                    request_id += 1
                if build_scene(state, resources) < 0:
                    return 23
                _render(resources.root, resources.rects, resources.colors, resources.texts, rect_count, text_count)
        native.sleep(16)
    return 0


def run_gui() -> int:
    resources = _GuiResources()
    result = 0
    failure = None
    try:
        result = _run_gui(resources)
    except BaseException as error:
        failure = error
    return _finish(resources, result, failure)
