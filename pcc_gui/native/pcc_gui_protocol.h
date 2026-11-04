#ifndef PCC_GUI_PROTOCOL_H
#define PCC_GUI_PROTOCOL_H
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif

/* A lease identifies one document/session generation. Fields are opaque byte
 * sequences: this API does not parse URLs, implement Fetch, or run handlers.
 * 0 success; 1 pending take; 2 invalid/stale/thread/output; 4 native failure;
 * 5 wrong head/state or short output buffer; 6 resource/identity limit.
 * All scalar output slots must be aligned and independent. Errors and pending
 * takes preserve every output. A pending peek writes only ready=0. */
int64_t pcc_gui_protocol_open(int64_t *owner);

/* Native producers on any thread. Input bytes are copied before publication.
 * Maximum 64 KiB metadata, 8 MiB body, 256 outstanding requests per owner,
 * 64 owners, and 64 MiB across all live request and reply bytes. */
int64_t pcc_gui_protocol_submit(int64_t owner, const void *metadata, int64_t metadata_len,
    const void *body, int64_t body_len, int64_t *request);

/* UI owner. Peek is non-consuming. Field 0 is metadata; field 1 is body.
 * A request stays readable until its terminal reply is taken or owner retires.
 * Claim exactly the FIFO head before invoking any source callback. */
int64_t pcc_gui_protocol_request_peek(int64_t owner, int64_t *ready, int64_t *request,
    int64_t *metadata_len, int64_t *body_len);
int64_t pcc_gui_protocol_request_copy(int64_t owner, int64_t request, int64_t field,
    void *out, int64_t capacity);
int64_t pcc_gui_protocol_request_claim(int64_t owner, int64_t request);

/* Native producers on any thread. Reply/fail require a claimed request.
 * Cancellation may also remove an unclaimed request from the FIFO. The first
 * terminal transition wins; repeat cancellation of a still-live cancelled
 * request succeeds. A source response status belongs in opaque metadata. */
int64_t pcc_gui_protocol_reply(int64_t owner, int64_t request, const void *metadata,
    int64_t metadata_len, const void *body, int64_t body_len);
int64_t pcc_gui_protocol_fail(int64_t owner, int64_t request, int64_t error_code);
int64_t pcc_gui_protocol_cancel(int64_t owner, int64_t request);

/* UI owner. Terminal kind: 1 reply, 2 failure (nonzero opaque error_code),
 * 3 cancellation. Take copies into independent caller buffers/slots, then
 * consumes once. Insufficient capacity preserves the result for retry. */
int64_t pcc_gui_protocol_response_peek(int64_t owner, int64_t request, int64_t *ready,
    int64_t *kind, int64_t *error_code, int64_t *metadata_len, int64_t *body_len);
int64_t pcc_gui_protocol_response_take(int64_t owner, int64_t request, void *metadata,
    int64_t metadata_cap, void *body, int64_t body_cap, int64_t *kind, int64_t *error_code);

/* UI owner. Retire discards pending/terminal children, invalidates every key,
 * and never dispatches a callback. Already copied caller data is independent. */
int64_t pcc_gui_protocol_retire(int64_t owner);
int64_t pcc_gui_protocol_live_counts(int64_t *owners, int64_t *requests, int64_t *bytes);
#ifdef __cplusplus
}
#endif
#endif
