#ifndef PCC_GUI_TRAY_H
#define PCC_GUI_TRAY_H
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
/* UI-thread, app-owned status items. No source callback runs in native actions.
 * Image 0 creates an initially empty item. Image keys can retire independently.
 * Menu attachment is exclusive and does not start tracking automatically.
 * Drain/ack click, run source callback, then explicitly select popup if desired.
 * Status: 0 success, 2 invalid/stale/thread, 3 UTF8, 4 native failure,
 * 5 busy/owned elsewhere, 6 lease/queue exhaustion. */
int64_t pcc_gui_tray_create(int64_t image,int64_t *out);
int64_t pcc_gui_tray_set_image(int64_t tray,int64_t image);
int64_t pcc_gui_tray_tooltip(int64_t tray,const void *text,int64_t length);
int64_t pcc_gui_tray_menu(int64_t tray,int64_t menu);
int64_t pcc_gui_tray_popup(int64_t tray);
/* kind 1 primary, 2 secondary. Flags: shift=1/control=2/option=4/command=8.
 * Only ready is written on an empty queue; ack exactly the current head. */
int64_t pcc_gui_tray_event_peek(int64_t tray,int64_t *ready,int64_t *sequence,int64_t *kind,int64_t *flags);
int64_t pcc_gui_tray_event_ack(int64_t tray,int64_t sequence);
int64_t pcc_gui_tray_release(int64_t tray);
int64_t pcc_gui_tray_live_count(int64_t *out);
#ifdef __cplusplus
}
#endif
#endif
