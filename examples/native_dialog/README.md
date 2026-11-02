# Native message box

`message_box.py` is a small compiled-Python consumer of the framework's native
message-box ABI. Build the canonical AppKit bridge, replace `__BRIDGE__` in a
private copy with its absolute path, and compile that copy using the selected
PCC toolchain. It creates a hidden owner and a real standalone OK dialog.
The original example stays unchanged. The native interaction fixture exercises
button choice, checkbox, cancel, parent close and resource release automatically.

The example uses `call_c_abi` and explicit output storage, not Python ctypes.
Compiler/ABI/runtime support must be qualified against the selected compiler;
clang/AppKit bridge tests alone do not qualify native PCC1. A custom bridge build
is still an external build owner. Source Electron option/Promise handling and
actual Harness main startup remain independent translation work.
