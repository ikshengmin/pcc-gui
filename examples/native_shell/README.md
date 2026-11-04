# Native desktop URL opening and file selection

Use the main thread and a live document request lease. The C declarations are
in `pcc_gui/native/pcc_gui_shell.h`, with PCC externs in `pcc_gui/pcc_gui_shell.py`.
`invalid_url.py` starts and consumes a deliberately invalid open request. Use a
private copy with `__BRIDGE__` replaced by the absolute built bridge path.

For a real external open, supply the caller's canonical NSURL-ready URL bytes
and activation flag. The native host checks the system's handler before asking
NSWorkspace to open the URL. A successful start publishes a native request key.
Take the terminal reply on the UI owner through the protocol queue. A successful
launch has an empty reply. Failure codes 10, 11 and 12 distinguish invalid
URL, no handler and launch failure. Source conversion, Promises and application
URL policies belong to the caller. Cancellation and document retirement can
prevent result delivery after the OS has already acted.

File reveal passes an absolute path to the system file viewer. Relative paths
are resolved against the process's current directory. Selection failure has
the source API's synchronous void result. Both APIs copy their input text
during the call.

The Darwin regression runs the public bridge with three NSWorkspace methods
intercepted in its own executable. It checks the exact URL, activation flag,
Finder path and empty viewer root. Native worker completions cover success,
failure, duplicate replies, cancellation and document retirement. This test
never opens Finder or a browser. The source behavior follows the selected
[Electron Darwin platform implementation](https://github.com/electron/electron/blob/v44.7.0/shell/common/platform_util_mac.mm).

For a generated-program comparison, build `tests/fixtures/native_shell.m`
with `PCC_GUI_SHELL_TEST_LIBRARY`. The `pcc_gui_test_shell_open_external` and
`pcc_gui_test_shell_show_item_in_folder` functions intercept the operations.
The test-only observer copies the URL or resolved file path. The activation
flag can be inspected separately. Call `pcc_gui_test_shell_finish` on a worker
to supply the deferred workspace result. The normal protocol functions peek,
take, cancel and retire these same requests.
