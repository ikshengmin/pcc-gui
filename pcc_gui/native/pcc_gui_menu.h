#ifndef PCC_GUI_MENU_H
#define PCC_GUI_MENU_H
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
/* Main/UI thread only. Monotonic menu/item leases are not object pointers.
 * Status: 0 success, 2 invalid/stale/thread/output, 3 invalid UTF8,
 * 4 native failure, 5 busy/owned elsewhere, 6 explicit resource limit. */
int64_t pcc_gui_menu_create(int64_t *out_menu);
/* kind: 0 action, 1 separator, 2 submenu. Command is an opaque signed token. */
int64_t pcc_gui_menu_insert(int64_t menu,int64_t index,int64_t kind,int64_t command,const void *text,int64_t length,int64_t *out_item);
int64_t pcc_gui_menu_remove(int64_t menu,int64_t index);
/* field 0 label, 1 tooltip. Flags: enabled=1, visible=2, checked=4.
 * Modifier bits: shift=1, control=2, option=4, command=8. */
int64_t pcc_gui_menu_item_text(int64_t item,int64_t field,const void *text,int64_t length);
int64_t pcc_gui_menu_item_state(int64_t item,int64_t flags,int64_t modifiers,const void *key,int64_t length);
/* A child has one parent; 0 detaches it. Cycles and busy graphs refuse. */
int64_t pcc_gui_menu_item_submenu(int64_t item,int64_t child);
int64_t pcc_gui_menu_count(int64_t menu,int64_t *out_count);
/* 0 relinquishes this API's application menu and restores its previous menu
 * only if AppKit still points to the owned menu. Foreign replacements survive. */
int64_t pcc_gui_menu_set_application(int64_t menu);
/* Synchronous native tracking. Coordinates are logical points from the
 * parent's content top-left. Parent must be a caller-owned live window.
 * No Python/T2 callback runs in the native tracking loop. A native exception
 * fails this lease with status 4 and leaves it available for explicit release. */
int64_t pcc_gui_menu_popup(int64_t menu,void *parent,int64_t x,int64_t y,int64_t positioning_index);
int64_t pcc_gui_menu_cancel(int64_t menu);
/* Root queue: kind 1 opened, 2 command, 3 closed. For kind 1/3 the item cell
 * contains the originating menu lease; kind 2 contains the item lease.
 * Peek is non-consuming.
 * Pending writes ready=0 only. Output int64 cells must be distinct/aligned.
 * Ack the selected head before invoking application callbacks. */
int64_t pcc_gui_menu_event_peek(int64_t menu,int64_t *ready,int64_t *sequence,int64_t *kind,int64_t *item,int64_t *command);
int64_t pcc_gui_menu_event_ack(int64_t menu,int64_t sequence);
/* Release retires own item keys and drops queued events. Child menu keys stay
 * live and become detached; attached/installed/tracking menus must retire first. */
int64_t pcc_gui_menu_release(int64_t menu);
int64_t pcc_gui_menu_live_count(int64_t *menus,int64_t *items);
#ifdef __cplusplus
}
#endif
#endif
