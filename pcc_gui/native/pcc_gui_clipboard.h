#ifndef PCC_GUI_CLIPBOARD_H
#define PCC_GUI_CLIPBOARD_H
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
/* Main-thread-only, positive opaque keys. Outputs remain unchanged on error.
 * 0 success; 2 invalid/stale/thread; 3 invalid UTF-8; 4 native failure;
 * 5 insufficient output space; 6 length/identity limit. */
int64_t pcc_gui_clipboard_open_general(int64_t *key_out);
int64_t pcc_gui_clipboard_open_named(const void *name, int64_t length, int64_t *key_out);
int64_t pcc_gui_clipboard_close(int64_t key);
int64_t pcc_gui_clipboard_write_utf8(int64_t key, const void *text, int64_t length);
int64_t pcc_gui_clipboard_clear(int64_t key);
int64_t pcc_gui_clipboard_snapshot(int64_t key, int64_t *snapshot_out, int64_t *length_out);
int64_t pcc_gui_clipboard_snapshot_copy(int64_t snapshot, void *out, int64_t capacity);
int64_t pcc_gui_clipboard_snapshot_release(int64_t snapshot);
int64_t pcc_gui_clipboard_live_counts(int64_t *boards_out, int64_t *snapshots_out);
#ifdef __cplusplus
}
#endif
#endif
