#ifndef PCC_GUI_FULLSCREEN_H
#define PCC_GUI_FULLSCREEN_H
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif

/* One main-thread observation lease per live Metal/AppKit window.
 * 0 success, 2 invalid/stale/thread/closed, 4 native failure,
 * 5 another owner or an unsupported overlapping opposite transition,
 * 6 resource limit. Errors leave caller output words unchanged. */
int64_t pcc_gui_fullscreen_acquire(void *window, int64_t *lease);
int64_t pcc_gui_fullscreen_state(int64_t lease, int64_t *closed, int64_t *fullscreen);
int64_t pcc_gui_fullscreen_set(int64_t lease, int64_t enabled);
/* Pops one copied notification: 0 empty, 1 entered, 2 left, 3 closed.
 * A closed lease remains readable until explicitly released. */
int64_t pcc_gui_fullscreen_take(int64_t lease, int64_t *kind);
int64_t pcc_gui_fullscreen_release(int64_t lease);
int64_t pcc_gui_fullscreen_live_count(int64_t *count);
#ifdef __cplusplus
}
#endif
#endif
