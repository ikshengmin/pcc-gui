#ifndef PCC_GUI_SHELL_H
#define PCC_GUI_SHELL_H
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif

enum PccGuiShellError {
    PCC_GUI_SHELL_INVALID_URL = 10,
    PCC_GUI_SHELL_NO_APPLICATION = 11,
    PCC_GUI_SHELL_OPEN_FAILED = 12
};

/* Main-thread desktop operations with a live pcc_gui_protocol_open lease.
 * Pass length-delimited UTF-8, at most 64 KiB, without embedded NUL. A zero
 * length may use a null pointer. ABI errors 2/4/5/6 preserve out_request.
 *
 * The URL is the caller's canonical, NSURL-ready absolute serialization, or
 * empty for an invalid source URL. Activate is exactly 0 or 1. On start
 * success, take the request through pcc_gui_protocol_response_peek/take.
 * Kind 1 is success with empty metadata/body. Kind 2 carries a PccGuiShellError
 * or an infrastructure error (4). Kind 3 is cancellation. Cancellation and
 * retirement discard late completions; they do not undo a submitted OS open. */
int64_t pcc_gui_shell_open_external(int64_t owner, const void *url, int64_t length,
                                    int64_t activate, int64_t *out_request);

/* Returns after submitting the selection to Finder. Relative paths undergo
 * POSIX realpath resolution; absolute path spelling is preserved. Finder
 * declining the selection does not raise a caller error. */
int64_t pcc_gui_shell_show_item_in_folder(int64_t owner, const void *path, int64_t length);
#ifdef __cplusplus
}
#endif
#endif
