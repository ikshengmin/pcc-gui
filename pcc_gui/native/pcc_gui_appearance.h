#ifndef PCC_GUI_APPEARANCE_H
#define PCC_GUI_APPEARANCE_H
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
/* One UI-thread app appearance lease; no system preferences are written.
 * source: 0 system (nil), 1 Aqua, 2 DarkAqua. snapshot flags:
 * dark=1, contrast=2, invert=4, reduced transparency=8,
 * differentiate without color=16, reduced motion=32.
 * Native invalidations are coalesced into actual main-thread samples.
 * 0 success; 2 invalid/stale/thread/output; 4 native failure;
 * 5 another owner/reentrant write/foreign appearance; 6 resource limit. */
int64_t pcc_gui_appearance_open(int64_t *out);
int64_t pcc_gui_appearance_set_source(int64_t key,int64_t source);
int64_t pcc_gui_appearance_snapshot(int64_t key,int64_t *source,int64_t *flags);
/* Non-consuming immutable sample queue. Pending writes ready only.
 * Acknowledge exactly the head before running source callbacks. */
int64_t pcc_gui_appearance_event_peek(int64_t key,int64_t *ready,int64_t *sequence,int64_t *source,int64_t *flags);
int64_t pcc_gui_appearance_event_ack(int64_t key,int64_t sequence);
/* roles 0 window background, 1 label, 2 control background, 3 control text.
 * Outputs are sRGB straight channels 0..255 under effective app appearance. */
int64_t pcc_gui_appearance_color(int64_t key,int64_t role,int64_t *r,int64_t *g,int64_t *b,int64_t *a);
/* Retire before unregister/restore. Restore prior raw appearance only if the
 * last installed value still belongs to this lease. Same-value foreign writes
 * are indistinguishable. A failed setter may have applied its native value;
 * ownership is retained for inspection/release rather than silently lost. */
int64_t pcc_gui_appearance_release(int64_t key);
int64_t pcc_gui_appearance_live_count(int64_t *out);
#ifdef __cplusplus
}
#endif
#endif
