#ifndef PCC_GUI_DOCUMENT_H
#define PCC_GUI_DOCUMENT_H
#include <stdint.h>
/* Immutable t2-browser-presentation-v1 data, principal boxes, read-only host.
 * Main thread only. Failed validation retains the previous document. */
int32_t pcc_gui_document_present(void *window, const uint8_t *json,
                                 uint64_t size);
int32_t pcc_gui_document_status(void *window, const char *message);
int32_t pcc_gui_document_rect(void *window, int64_t node, double *xywh);
int64_t pcc_gui_document_node_count(void *window);
#endif
