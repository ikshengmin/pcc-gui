# Owned native menus

`menu.py` uses the canonical native menu ABI through typed `call_c_abi` calls.
Build the canonical AppKit bridge and replace `__BRIDGE__` in a private copy
with its absolute path before compiling with the selected PCC toolchain. It
creates an owned window/menu and waits for a real native menu choice.

The API owns monotonic menu/item keys, a single-parent acyclic menu graph,
explicit item state/UTF8 labels/shortcuts and application-menu restoration.
Native callbacks publish bounded integer events; peek does not consume them.
The caller acknowledges each selected head before invoking source callbacks.
Release requires an uninstalled, detached, nontracking menu; child menu keys
remain live and must be released explicitly. Foreign application-menu
replacements are preserved when this owner relinquishes its menu.

Popup is synchronous AppKit tracking. No Python/T2 graph or callback enters the
native tracking loop. Asynchronous Electron scheduling and translated Harness
integration require a separate production owner; this example does not claim
that wiring. Clang/AppKit ownership tests and host PCC IR emission do not qualify
native PCC1 independence. Installed PCC1 and complete application execution are
separate gates.
