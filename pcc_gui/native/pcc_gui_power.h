#ifndef PCC_GUI_POWER_H
#define PCC_GUI_POWER_H
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
/* UI-thread ownership, native-only publication from arbitrary posting threads.
 * mask: resume=1, shutdown=2. No operation requests an OS power transition.
 * 0 success; 2 invalid/stale/thread/output; 4 registration/host failure;
 * 6 explicit lease/queue/sequence exhaustion. */
int64_t pcc_gui_power_open(int64_t mask,int64_t *out_key);
/* kind: resume=1, shutdown=2. Peek does not consume. Only ready is written
 * when pending; all outputs remain unchanged on error. */
int64_t pcc_gui_power_peek(int64_t key,int64_t *ready,int64_t *sequence,int64_t *kind);
int64_t pcc_gui_power_ack(int64_t key,int64_t sequence);
int64_t pcc_gui_power_release(int64_t key);
int64_t pcc_gui_power_live_count(int64_t *out_count);
#ifdef __cplusplus
}
#endif
#endif
