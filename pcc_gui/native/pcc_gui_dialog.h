#ifndef PCC_GUI_DIALOG_H
#define PCC_GUI_DIALOG_H
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
/* UI-thread only. Keys are monotonic owned leases, never object addresses.
 * 0 success; 2 invalid/stale/state/thread/output; 3 invalid UTF8;
 * 4 unavailable host; 5 busy; 6 resource bound. */
int64_t pcc_gui_message_box_create(int64_t style,int64_t default_id,int64_t cancel_id,int64_t checked,int64_t *out);
/* field: 0 title, 1 message, 2 detail, 3 suppression checkbox label. */
int64_t pcc_gui_message_box_text(int64_t key,int64_t field,const void *bytes,int64_t length);
int64_t pcc_gui_message_box_button(int64_t key,const void *bytes,int64_t length);
int64_t pcc_gui_message_box_begin(int64_t key,void *parent);
/* Poll advances one owned modal-session turn. Ready does not consume the key.
 * Pending writes ready=0 only. All output addresses must be distinct. */
int64_t pcc_gui_message_box_poll(int64_t key,int64_t *ready,int64_t *response,int64_t *checked);
int64_t pcc_gui_message_box_cancel(int64_t key);
/* Pending jobs must be canceled and polled to completion before release. */
int64_t pcc_gui_message_box_release(int64_t key);
int64_t pcc_gui_message_box_live_count(int64_t *out);
#ifdef __cplusplus
}
#endif
#endif
