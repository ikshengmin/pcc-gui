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
