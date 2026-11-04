// Native ingress and terminal byte ownership for one document generation.
// The registry lock covers lookup, publication and retirement; no callback,
// AppKit operation, or pointer into this storage leaves the critical section.
#import <Foundation/Foundation.h>
#include "pcc_gui_protocol.h"
#include <pthread.h>
#include <stdlib.h>
#include <string.h>

enum {
    PCC_PROTOCOL_OWNERS = 64, PCC_PROTOCOL_REQUESTS = 256,
    PCC_PROTOCOL_METADATA = 64 * 1024, PCC_PROTOCOL_BODY = 8 * 1024 * 1024,
    PCC_PROTOCOL_TOTAL = 64 * 1024 * 1024,
    PCC_PROTOCOL_QUEUED = 0, PCC_PROTOCOL_CLAIMED = -1,
    PCC_PROTOCOL_REPLY = 1, PCC_PROTOCOL_FAILURE = 2, PCC_PROTOCOL_CANCEL = 3
};
typedef struct { unsigned char *data; int64_t length; } PccProtocolBytes;
typedef struct {
    int64_t key, state, error;
    PccProtocolBytes metadata, body, reply_metadata, reply_body;
} PccProtocolRequest;
typedef struct {
    int64_t key;
    size_t queued;
    PccProtocolRequest *requests[PCC_PROTOCOL_REQUESTS];
    PccProtocolRequest *fifo[PCC_PROTOCOL_REQUESTS];
} PccProtocolOwner;

static pthread_mutex_t pcc_protocol_mutex = PTHREAD_MUTEX_INITIALIZER;
static PccProtocolOwner *pcc_protocol_owners[PCC_PROTOCOL_OWNERS];
static int64_t pcc_protocol_next = 1, pcc_protocol_owner_count, pcc_protocol_request_count;
static int64_t pcc_protocol_live_bytes;

static int pcc_protocol_enter(void) { return pthread_mutex_lock(&pcc_protocol_mutex) == 0; }
static int64_t pcc_protocol_leave(int64_t status) {
    pthread_mutex_unlock(&pcc_protocol_mutex);
    return status;
}
static int pcc_protocol_outputs(int64_t *const *slots, size_t count) {
    for (size_t i = 0; i < count; i++) {
        if (!slots[i] || (uintptr_t)slots[i] % _Alignof(int64_t)) return 0;
        for (size_t j = 0; j < i; j++) if (slots[i] == slots[j]) return 0;
    }
    return 1;
}
static int pcc_protocol_overlap(const void *p, size_t n, const void *q, size_t m) {
    if (!n || !m) return 0;
    uintptr_t a = (uintptr_t)p, b = (uintptr_t)q;
    return a <= b ? b - a < n : a - b < m;
}
static int64_t pcc_protocol_sizes(const void *metadata, int64_t metadata_len,
        const void *body, int64_t body_len) {
    if (metadata_len < 0 || body_len < 0 || (metadata_len && !metadata) || (body_len && !body)) return 2;
    return metadata_len > PCC_PROTOCOL_METADATA || body_len > PCC_PROTOCOL_BODY ? 6 : 0;
}
static PccProtocolOwner *pcc_protocol_owner(int64_t key) {
    if (key > 0) for (size_t i = 0; i < PCC_PROTOCOL_OWNERS; i++) {
        PccProtocolOwner *owner = pcc_protocol_owners[i];
        if (owner && owner->key == key) return owner;
    }
    return NULL;
}
static PccProtocolRequest *pcc_protocol_request(PccProtocolOwner *owner, int64_t key) {
    if (owner && key > 0) for (size_t i = 0; i < PCC_PROTOCOL_REQUESTS; i++) {
        PccProtocolRequest *request = owner->requests[i];
        if (request && request->key == key) return request;
    }
    return NULL;
}
static int pcc_protocol_clone(PccProtocolBytes *snapshot, const void *bytes, int64_t length) {
    if (length) {
        snapshot->data = malloc((size_t)length);
        if (!snapshot->data) return 0;
        memcpy(snapshot->data, bytes, (size_t)length);
    }
    snapshot->length = length;
    return 1;
}
// Keep the old request and accounting unchanged if either allocation fails.
static int64_t pcc_protocol_pair(PccProtocolBytes *meta_out, PccProtocolBytes *body_out,
        const void *metadata, int64_t metadata_len, const void *body, int64_t body_len) {
    if (metadata_len + body_len > PCC_PROTOCOL_TOTAL - pcc_protocol_live_bytes) return 6;
    PccProtocolBytes m = {0}, b = {0};
    if (!pcc_protocol_clone(&m, metadata, metadata_len)) return 4;
    if (!pcc_protocol_clone(&b, body, body_len)) { free(m.data); return 4; }
    *meta_out = m;
    *body_out = b;
    pcc_protocol_live_bytes += metadata_len + body_len;
    return 0;
}
static void pcc_protocol_drop(PccProtocolOwner *owner, size_t slot) {
    PccProtocolRequest *request = owner->requests[slot];
    owner->requests[slot] = NULL;
    pcc_protocol_live_bytes -= request->metadata.length + request->body.length
                             + request->reply_metadata.length + request->reply_body.length;
    free(request->metadata.data); free(request->body.data);
    free(request->reply_metadata.data); free(request->reply_body.data);
    free(request);
    pcc_protocol_request_count--;
}
static void pcc_protocol_unqueue(PccProtocolOwner *owner, size_t index) {
    size_t rest = owner->queued - index - 1;
    if (rest) memmove(owner->fifo + index, owner->fifo + index + 1, rest * sizeof(owner->fifo[0]));
    owner->fifo[--owner->queued] = NULL;
}

int64_t pcc_gui_protocol_open(int64_t *out) {
    if (![NSThread isMainThread] || !pcc_protocol_outputs(&out, 1)) return 2;
    if (!pcc_protocol_enter()) return 4;
    size_t slot = 0;
    while (slot < PCC_PROTOCOL_OWNERS && pcc_protocol_owners[slot]) slot++;
    if (slot == PCC_PROTOCOL_OWNERS || pcc_protocol_next == INT64_MAX) return pcc_protocol_leave(6);
    PccProtocolOwner *owner = calloc(1, sizeof(*owner));
    if (!owner) return pcc_protocol_leave(4);
    owner->key = pcc_protocol_next++;
    pcc_protocol_owners[slot] = owner;
    pcc_protocol_owner_count++;
    *out = owner->key;
    return pcc_protocol_leave(0);
}
int64_t pcc_gui_protocol_submit(int64_t owner_key, const void *metadata, int64_t metadata_len,
        const void *body, int64_t body_len, int64_t *out) {
    if (!pcc_protocol_outputs(&out, 1)) return 2;
    int64_t status = pcc_protocol_sizes(metadata, metadata_len, body, body_len);
    if (status) return status;
    if (!pcc_protocol_enter()) return 4;
    PccProtocolOwner *owner = pcc_protocol_owner(owner_key);
    if (!owner) return pcc_protocol_leave(2);
    size_t slot = 0;
    while (slot < PCC_PROTOCOL_REQUESTS && owner->requests[slot]) slot++;
    if (slot == PCC_PROTOCOL_REQUESTS || pcc_protocol_next == INT64_MAX) return pcc_protocol_leave(6);
    PccProtocolRequest *request = calloc(1, sizeof(*request));
    if (!request) return pcc_protocol_leave(4);
    status = pcc_protocol_pair(&request->metadata, &request->body, metadata, metadata_len, body, body_len);
    if (status) { free(request); return pcc_protocol_leave(status); }
    request->key = pcc_protocol_next++;
    owner->requests[slot] = request;
    owner->fifo[owner->queued++] = request;
    pcc_protocol_request_count++;
    *out = request->key;
    return pcc_protocol_leave(0);
}
int64_t pcc_gui_protocol_request_peek(int64_t owner_key, int64_t *ready, int64_t *key,
        int64_t *metadata_len, int64_t *body_len) {
    int64_t *outs[] = {ready, key, metadata_len, body_len};
    if (![NSThread isMainThread] || !pcc_protocol_outputs(outs, 4)) return 2;
    if (!pcc_protocol_enter()) return 4;
    PccProtocolOwner *owner = pcc_protocol_owner(owner_key);
    if (!owner) return pcc_protocol_leave(2);
    *ready = owner->queued != 0;
    if (owner->queued) {
        PccProtocolRequest *first = owner->fifo[0];
        *key = first->key; *metadata_len = first->metadata.length; *body_len = first->body.length;
    }
    return pcc_protocol_leave(0);
}
int64_t pcc_gui_protocol_request_copy(int64_t owner_key, int64_t key, int64_t field,
        void *out, int64_t capacity) {
    if (![NSThread isMainThread] || (field != 0 && field != 1) || capacity < 0) return 2;
    if (!pcc_protocol_enter()) return 4;
    PccProtocolRequest *request = pcc_protocol_request(pcc_protocol_owner(owner_key), key);
    if (!request) return pcc_protocol_leave(2);
    PccProtocolBytes bytes = field ? request->body : request->metadata;
    if (bytes.length > capacity) return pcc_protocol_leave(5);
    if (bytes.length && !out) return pcc_protocol_leave(2);
    if (bytes.length) memcpy(out, bytes.data, (size_t)bytes.length);
    return pcc_protocol_leave(0);
}
int64_t pcc_gui_protocol_request_claim(int64_t owner_key, int64_t key) {
    if (![NSThread isMainThread]) return 2;
    if (!pcc_protocol_enter()) return 4;
    PccProtocolOwner *owner = pcc_protocol_owner(owner_key);
    PccProtocolRequest *request = pcc_protocol_request(owner, key);
    if (!request) return pcc_protocol_leave(2);
    if (!owner->queued || owner->fifo[0] != request) return pcc_protocol_leave(5);
    pcc_protocol_unqueue(owner, 0);
    request->state = PCC_PROTOCOL_CLAIMED;
    return pcc_protocol_leave(0);
}
int64_t pcc_gui_protocol_reply(int64_t owner_key, int64_t key, const void *metadata,
        int64_t metadata_len, const void *body, int64_t body_len) {
    int64_t status = pcc_protocol_sizes(metadata, metadata_len, body, body_len);
    if (status) return status;
    if (!pcc_protocol_enter()) return 4;
    PccProtocolRequest *request = pcc_protocol_request(pcc_protocol_owner(owner_key), key);
    if (!request) return pcc_protocol_leave(2);
    if (request->state != PCC_PROTOCOL_CLAIMED) return pcc_protocol_leave(5);
    status = pcc_protocol_pair(&request->reply_metadata, &request->reply_body,
                               metadata, metadata_len, body, body_len);
    if (!status) request->state = PCC_PROTOCOL_REPLY;
    return pcc_protocol_leave(status);
}
int64_t pcc_gui_protocol_fail(int64_t owner_key, int64_t key, int64_t error_code) {
    if (!error_code) return 2;
    if (!pcc_protocol_enter()) return 4;
    PccProtocolRequest *request = pcc_protocol_request(pcc_protocol_owner(owner_key), key);
    if (!request) return pcc_protocol_leave(2);
    if (request->state != PCC_PROTOCOL_CLAIMED) return pcc_protocol_leave(5);
    request->error = error_code; request->state = PCC_PROTOCOL_FAILURE;
    return pcc_protocol_leave(0);
}
int64_t pcc_gui_protocol_cancel(int64_t owner_key, int64_t key) {
    if (!pcc_protocol_enter()) return 4;
    PccProtocolOwner *owner = pcc_protocol_owner(owner_key);
    PccProtocolRequest *request = pcc_protocol_request(owner, key);
    if (!request) return pcc_protocol_leave(2);
    if (request->state == PCC_PROTOCOL_CANCEL) return pcc_protocol_leave(0);
    if (request->state == PCC_PROTOCOL_QUEUED) {
        size_t i = 0;
        while (i < owner->queued && owner->fifo[i] != request) i++;
        if (i == owner->queued) return pcc_protocol_leave(4);
        pcc_protocol_unqueue(owner, i);
    } else if (request->state != PCC_PROTOCOL_CLAIMED) return pcc_protocol_leave(5);
    request->state = PCC_PROTOCOL_CANCEL;
    return pcc_protocol_leave(0);
}
int64_t pcc_gui_protocol_response_peek(int64_t owner_key, int64_t key, int64_t *ready,
        int64_t *kind, int64_t *error_code, int64_t *metadata_len, int64_t *body_len) {
    int64_t *outs[] = {ready, kind, error_code, metadata_len, body_len};
    if (![NSThread isMainThread] || !pcc_protocol_outputs(outs, 5)) return 2;
    if (!pcc_protocol_enter()) return 4;
    PccProtocolRequest *request = pcc_protocol_request(pcc_protocol_owner(owner_key), key);
    if (!request) return pcc_protocol_leave(2);
    *ready = request->state > 0;
    if (request->state > 0) {
        *kind = request->state; *error_code = request->error;
        *metadata_len = request->reply_metadata.length; *body_len = request->reply_body.length;
    }
    return pcc_protocol_leave(0);
}
int64_t pcc_gui_protocol_response_take(int64_t owner_key, int64_t key, void *metadata,
        int64_t metadata_cap, void *body, int64_t body_cap, int64_t *kind, int64_t *error_code) {
    int64_t *outs[] = {kind, error_code};
    if (![NSThread isMainThread] || !pcc_protocol_outputs(outs, 2) || metadata_cap < 0 || body_cap < 0) return 2;
    if (!pcc_protocol_enter()) return 4;
    PccProtocolOwner *owner = pcc_protocol_owner(owner_key);
    if (!owner) return pcc_protocol_leave(2);
    size_t slot = 0;
    while (slot < PCC_PROTOCOL_REQUESTS && (!owner->requests[slot] || owner->requests[slot]->key != key)) slot++;
    if (slot == PCC_PROTOCOL_REQUESTS) return pcc_protocol_leave(2);
    PccProtocolRequest *request = owner->requests[slot];
    if (request->state <= 0) return pcc_protocol_leave(1);
    int64_t m = request->reply_metadata.length, b = request->reply_body.length;
    if (m > metadata_cap || b > body_cap) return pcc_protocol_leave(5);
    if ((m && !metadata) || (b && !body) || pcc_protocol_overlap(metadata, m, body, b)) return pcc_protocol_leave(2);
    for (size_t i = 0; i < 2; i++) {
        if (pcc_protocol_overlap(metadata, m, outs[i], sizeof(int64_t)) ||
            pcc_protocol_overlap(body, b, outs[i], sizeof(int64_t))) return pcc_protocol_leave(2);
    }
    if (m) memcpy(metadata, request->reply_metadata.data, (size_t)m);
    if (b) memcpy(body, request->reply_body.data, (size_t)b);
    *kind = request->state; *error_code = request->error;
    pcc_protocol_drop(owner, slot);
    return pcc_protocol_leave(0);
}
int64_t pcc_gui_protocol_retire(int64_t owner_key) {
    if (![NSThread isMainThread]) return 2;
    if (!pcc_protocol_enter()) return 4;
    size_t slot = 0;
    while (slot < PCC_PROTOCOL_OWNERS && (!pcc_protocol_owners[slot] || pcc_protocol_owners[slot]->key != owner_key)) slot++;
    if (slot == PCC_PROTOCOL_OWNERS) return pcc_protocol_leave(2);
    PccProtocolOwner *owner = pcc_protocol_owners[slot];
    pcc_protocol_owners[slot] = NULL;
    for (size_t i = 0; i < PCC_PROTOCOL_REQUESTS; i++) if (owner->requests[i]) pcc_protocol_drop(owner, i);
    free(owner); pcc_protocol_owner_count--;
    return pcc_protocol_leave(0);
}
int64_t pcc_gui_protocol_live_counts(int64_t *owners, int64_t *requests, int64_t *bytes) {
    int64_t *outs[] = {owners, requests, bytes};
    if (![NSThread isMainThread] || !pcc_protocol_outputs(outs, 3)) return 2;
    if (!pcc_protocol_enter()) return 4;
    *owners = pcc_protocol_owner_count; *requests = pcc_protocol_request_count; *bytes = pcc_protocol_live_bytes;
    return pcc_protocol_leave(0);
}
