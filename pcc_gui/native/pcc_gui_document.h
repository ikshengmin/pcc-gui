#ifndef PCC_GUI_DOCUMENT_H
#define PCC_GUI_DOCUMENT_H
#include <stdint.h>
/* Immutable t2-browser-presentation-v1 data, principal boxes, read-only host.
 * Main thread only. Failed validation retains the previous document. */
int32_t pcc_gui_document_present(void *window, const uint8_t *json,
                                 uint64_t size);
/* Same document validation. Opt one password node into native editing, or
 * pass -1 for none. A hidden or disabled node has no active editor. */
int32_t pcc_gui_document_present_with_password(void *window, const uint8_t *json,
                                               uint64_t size, int64_t node);
/* One coalesced UTF-16LE replacement, up to 4096 code units. Returns its
 * node index, or -1 when no edit is pending. Never exposes text via frames. */
int64_t pcc_gui_document_take_password_edit(void *window, uint8_t *bytes,
                                            uint32_t capacity, uint32_t *length);
/* Per-presented-frame, opt-in button activation. Main thread only.
 * A newly presented view has no enabled buttons and no pending click. */
int32_t pcc_gui_document_enable_button(void *window, int64_t node);
int64_t pcc_gui_document_take_click(void *window);
int32_t pcc_gui_document_status(void *window, const char *message);
int32_t pcc_gui_document_rect(void *window, int64_t node, double *xywh);
int64_t pcc_gui_document_node_count(void *window);
#endif
