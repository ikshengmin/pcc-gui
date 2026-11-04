// Headless consumer of the canonical bridge. No application, window or network.
#import <AppKit/AppKit.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// Fail either side of a snapshot allocation and count the bridge's C storage.
// The protocol allocates and frees under its one native ownership lock.
static int fail_after = -1, allocations;
static int fail_next(void) {
    if (fail_after < 0) return 0;
    if (!fail_after) { fail_after = -1; return 1; }
    fail_after--; return 0;
}
static void *checked_malloc(size_t n) {
    void *p = fail_next() ? NULL : malloc(n); if (p) allocations++; return p;
}
static void *checked_calloc(size_t n, size_t size) {
    void *p = fail_next() ? NULL : calloc(n, size); if (p) allocations++; return p;
}
static void checked_free(void *p) { if (p) allocations--; free(p); }
#define malloc checked_malloc
#define calloc checked_calloc
#define free checked_free
#include "../../pcc_gui/native/pcc_gui_metal_render_bridge.m"
#undef malloc
#undef calloc
#undef free

#define CHECK(x) do { if (!(x)) { fprintf(stderr, "protocol assertion %d: %s\n", __LINE__, #x); exit(90); } } while (0)
static int64_t open_owner(void) {
    int64_t key = 0; CHECK(pcc_gui_protocol_open(&key) == 0 && key > 0); return key;
}
static int64_t empty_request(int64_t owner) {
    int64_t key = 0; CHECK(pcc_gui_protocol_submit(owner, NULL, 0, NULL, 0, &key) == 0); return key;
}
static void counts(int64_t owners, int64_t requests, int64_t bytes) {
    int64_t o = -1, r = -1, b = -1;
    CHECK(pcc_gui_protocol_live_counts(&o, &r, &b) == 0 && o == owners && r == requests && b == bytes);
}
static void take_without_bytes(int64_t owner, int64_t request, int64_t expected, int64_t error) {
    int64_t kind = -1, code = -1;
    CHECK(pcc_gui_protocol_response_take(owner, request, NULL, 0, NULL, 0, &kind, &code) == 0);
    CHECK(kind == expected && code == error);
}
static void byte_round_trip(void) {
    int64_t owner = open_owner(), other = open_owner(), first = -1;
    unsigned char meta[] = {0x80, 0, 0xff}, body[1025], copied[1025];
    for (size_t i = 0; i < sizeof(body); i++) body[i] = (unsigned char)(i * 17);
    CHECK(pcc_gui_protocol_submit(owner, meta, sizeof(meta), body, sizeof(body), &first) == 0);
    int64_t middle = empty_request(owner), last = empty_request(owner);
    CHECK(first < middle && middle < last);
    counts(2, 3, sizeof(meta) + sizeof(body));
    memset(meta, 0, sizeof(meta)); memset(body, 0, sizeof(body));
    int64_t ready = -1, key = -1, m = -1, b = -1, kind = 71, code = 72;
    CHECK(pcc_gui_protocol_request_peek(owner, &ready, &key, &m, &b) == 0 && ready && key == first);
    CHECK(m == 3 && b == sizeof(body));
    CHECK(pcc_gui_protocol_request_peek(owner, &ready, &key, &m, &b) == 0 && key == first);
    CHECK(pcc_gui_protocol_request_copy(other, first, 0, copied, sizeof(copied)) == 2);
    CHECK(pcc_gui_protocol_request_copy(owner, first, 0, copied, sizeof(copied)) == 0);
    CHECK(copied[0] == 0x80 && copied[1] == 0 && copied[2] == 0xff);
    memset(copied, 0xce, sizeof(copied));
    CHECK(pcc_gui_protocol_request_copy(owner, first, 1, copied, sizeof(copied) - 1) == 5);
    CHECK(copied[0] == 0xce && copied[sizeof(copied)-1] == 0xce);
    CHECK(pcc_gui_protocol_request_copy(owner, first, 1, copied, sizeof(copied)) == 0);
    for (size_t i = 0; i < sizeof(copied); i++) CHECK(copied[i] == (unsigned char)(i * 17));
    CHECK(pcc_gui_protocol_request_claim(owner, last) == 5);
    CHECK(pcc_gui_protocol_reply(owner, first, NULL, 0, NULL, 0) == 5);
    CHECK(pcc_gui_protocol_fail(owner, first, -17) == 5);
    CHECK(pcc_gui_protocol_response_peek(owner, first, &ready, &kind, &code, &m, &b) == 0);
    CHECK(!ready && kind == 71 && code == 72 && m == 3 && b == sizeof(body));
    CHECK(pcc_gui_protocol_response_take(owner, first, NULL, 0, NULL, 0, &kind, &code) == 1);
    CHECK(kind == 71 && code == 72);
    CHECK(pcc_gui_protocol_cancel(owner, middle) == 0 && pcc_gui_protocol_cancel(owner, middle) == 0);
    CHECK(pcc_gui_protocol_request_claim(owner, middle) == 5);
    CHECK(pcc_gui_protocol_request_claim(owner, first) == 0 && pcc_gui_protocol_request_claim(owner, first) == 5);
    CHECK(pcc_gui_protocol_request_peek(owner, &ready, &key, &m, &b) == 0 && key == last);
    CHECK(pcc_gui_protocol_reply(owner, first, "\0R", 2, copied, sizeof(copied)) == 0);
    memset(copied, 0xce, sizeof(copied));
    CHECK(pcc_gui_protocol_cancel(owner, first) == 5 && pcc_gui_protocol_fail(owner, first, -17) == 5);
    CHECK(pcc_gui_protocol_reply(owner, first, NULL, 0, NULL, 0) == 5);
    CHECK(pcc_gui_protocol_response_peek(owner, first, &ready, &kind, &code, &m, &b) == 0);
    CHECK(ready && kind == 1 && code == 0 && m == 2 && b == sizeof(copied));
    _Alignas(int64_t) unsigned char out[1025]; memset(out, 0xce, sizeof(out));
    unsigned char out_meta[2] = {0xce, 0xce}; kind = 71; code = 72;
    CHECK(pcc_gui_protocol_response_take(owner, first, out_meta, 2, out, sizeof(out)-1, &kind, &code) == 5);
    CHECK(out_meta[0] == 0xce && out[0] == 0xce && kind == 71 && code == 72);
    CHECK(pcc_gui_protocol_response_take(owner, first, out, 2, out, sizeof(out), &kind, &code) == 2);
    CHECK(pcc_gui_protocol_response_take(owner, first, out_meta, 2, out, sizeof(out), (int64_t *)out, &code) == 2);
    CHECK(out_meta[0] == 0xce && out[0] == 0xce && kind == 71 && code == 72);
    CHECK(pcc_gui_protocol_response_take(owner, first, out_meta, 2, out, sizeof(out), &kind, &code) == 0);
    CHECK(kind == 1 && code == 0 && out_meta[0] == 0 && out_meta[1] == 'R');
    for (size_t i = 0; i < sizeof(out); i++) CHECK(out[i] == (unsigned char)(i * 17));
    CHECK(pcc_gui_protocol_response_take(owner, first, NULL, 0, NULL, 0, &kind, &code) == 2);
    take_without_bytes(owner, middle, 3, 0);
    CHECK(pcc_gui_protocol_request_claim(owner, last) == 0);
    CHECK(pcc_gui_protocol_fail(owner, last, 0) == 2 && pcc_gui_protocol_fail(owner, last, -17) == 0);
    CHECK(pcc_gui_protocol_fail(owner, last, -18) == 5);
    take_without_bytes(owner, last, 2, -17);
    key = 71; m = 72; b = 73;
    CHECK(pcc_gui_protocol_request_peek(owner, &ready, &key, &m, &b) == 0 && !ready && key == 71 && m == 72 && b == 73);
    CHECK(pcc_gui_protocol_request_peek(owner, &ready, &ready, &m, &b) == 2);
    counts(2, 0, 0);
    CHECK(pcc_gui_protocol_retire(owner) == 0 && pcc_gui_protocol_retire(owner) == 2);
    CHECK(pcc_gui_protocol_retire(other) == 0);
}

enum { PRODUCERS = 4, EACH = 32 };
typedef struct { int64_t owner; unsigned char producer; } Producer;
static void *submit_batch(void *arg) { @autoreleasepool {
    Producer *p = arg;
    int64_t a = 71, b = 72, c = 73, d = 74, e = 75;
    CHECK(pcc_gui_protocol_open(&a) == 2 && pcc_gui_protocol_retire(p->owner) == 2);
    CHECK(pcc_gui_protocol_request_peek(p->owner, &a, &b, &c, &d) == 2);
    CHECK(pcc_gui_protocol_request_copy(p->owner, p->owner, 0, &a, sizeof(a)) == 2);
    CHECK(pcc_gui_protocol_request_claim(p->owner, p->owner) == 2);
    CHECK(pcc_gui_protocol_response_peek(p->owner, p->owner, &a, &b, &c, &d, &e) == 2);
    CHECK(pcc_gui_protocol_response_take(p->owner, p->owner, NULL, 0, NULL, 0, &a, &b) == 2);
    CHECK(pcc_gui_protocol_live_counts(&a, &b, &c) == 2);
    CHECK(a == 71 && b == 72 && c == 73 && d == 74 && e == 75);
    for (unsigned char i = 0; i < EACH; i++) {
        unsigned char bytes[] = {p->producer, i, 0, 0xff};
        int64_t key = -1;
        CHECK(pcc_gui_protocol_submit(p->owner, NULL, 0, bytes, sizeof(bytes), &key) == 0 && key > 0);
        memset(bytes, 0xaa, sizeof(bytes));
    }
    return NULL;
}}
static void concurrent_fifo(void) {
    int64_t owner = open_owner(); pthread_t threads[PRODUCERS]; Producer args[PRODUCERS];
    for (int i = 0; i < PRODUCERS; i++) {
        args[i] = (Producer){owner, (unsigned char)i};
        CHECK(pthread_create(&threads[i], NULL, submit_batch, &args[i]) == 0);
    }
    for (int i = 0; i < PRODUCERS; i++) CHECK(pthread_join(threads[i], NULL) == 0);
    counts(1, PRODUCERS * EACH, PRODUCERS * EACH * 4);
    int seen[PRODUCERS] = {0}; int64_t previous = 0;
    for (int i = 0; i < PRODUCERS * EACH; i++) {
        int64_t ready = 0, key = 0, m = -1, b = -1;
        CHECK(pcc_gui_protocol_request_peek(owner, &ready, &key, &m, &b) == 0 && ready && key > previous && m == 0 && b == 4);
        unsigned char data[4]; CHECK(pcc_gui_protocol_request_copy(owner, key, 1, data, 4) == 0);
        CHECK(data[0] < PRODUCERS && data[1] == seen[data[0]]++ && data[2] == 0 && data[3] == 0xff);
        CHECK(pcc_gui_protocol_request_claim(owner, key) == 0 && pcc_gui_protocol_reply(owner, key, NULL, 0, NULL, 0) == 0);
        take_without_bytes(owner, key, 1, 0); previous = key;
    }
    for (int i = 0; i < PRODUCERS; i++) CHECK(seen[i] == EACH);
    CHECK(pcc_gui_protocol_retire(owner) == 0);
}

typedef struct {
    pthread_mutex_t mutex;
    pthread_cond_t condition;
    int waiting, go;
} Gate;
static void gate_wait(Gate *gate) {
    pthread_mutex_lock(&gate->mutex); gate->waiting++; pthread_cond_broadcast(&gate->condition);
    while (!gate->go) pthread_cond_wait(&gate->condition, &gate->mutex);
    pthread_mutex_unlock(&gate->mutex);
}
typedef struct { Gate *gate; int64_t owner, request, status; int action; } Race;
static void *terminal_race(void *arg) {
    Race *r = arg; gate_wait(r->gate);
    if (r->action == 0) r->status = pcc_gui_protocol_reply(r->owner, r->request, NULL, 0, NULL, 0);
    if (r->action == 1) r->status = pcc_gui_protocol_fail(r->owner, r->request, -41);
    if (r->action == 2) r->status = pcc_gui_protocol_cancel(r->owner, r->request);
    return NULL;
}
static void release_gate(Gate *gate, int workers) {
    pthread_mutex_lock(&gate->mutex);
    while (gate->waiting != workers) pthread_cond_wait(&gate->condition, &gate->mutex);
    gate->go = 1; pthread_cond_broadcast(&gate->condition); pthread_mutex_unlock(&gate->mutex);
}
static void concurrent_completion(void) {
    int64_t owner = open_owner(), key = empty_request(owner);
    CHECK(pcc_gui_protocol_request_claim(owner, key) == 0);
    Gate gate = {PTHREAD_MUTEX_INITIALIZER, PTHREAD_COND_INITIALIZER, 0, 0};
    pthread_t threads[3]; Race args[3];
    for (int i = 0; i < 3; i++) {
        args[i] = (Race){&gate, owner, key, -1, i};
        CHECK(pthread_create(&threads[i], NULL, terminal_race, &args[i]) == 0);
    }
    release_gate(&gate, 3);
    int winner = -1;
    for (int i = 0; i < 3; i++) {
        CHECK(pthread_join(threads[i], NULL) == 0);
        if (args[i].status == 0) { CHECK(winner == -1); winner = i; }
        else CHECK(args[i].status == 5);
    }
    CHECK(winner >= 0);
    take_without_bytes(owner, key, winner+1, winner==1 ? -41 : 0);
    pthread_cond_destroy(&gate.condition); pthread_mutex_destroy(&gate.mutex);
    CHECK(pcc_gui_protocol_retire(owner) == 0);
}
static void *submit_during_retire(void *arg) {
    Race *r = arg; gate_wait(r->gate);
    int64_t out = 71; r->status = pcc_gui_protocol_submit(r->owner, "x", 1, NULL, 0, &out);
    CHECK((r->status == 0 && out > 0) || (r->status == 2 && out == 71));
    return NULL;
}
static void concurrent_retirement(void) {
    int64_t owner = open_owner(), claimed = empty_request(owner), ready = empty_request(owner);
    CHECK(pcc_gui_protocol_request_claim(owner, claimed) == 0 && pcc_gui_protocol_request_claim(owner, ready) == 0);
    CHECK(pcc_gui_protocol_reply(owner, ready, "m", 1, "b", 1) == 0);
    Gate gate = {PTHREAD_MUTEX_INITIALIZER, PTHREAD_COND_INITIALIZER, 0, 0};
    pthread_t threads[PRODUCERS]; Race args[PRODUCERS];
    for (int i = 0; i < PRODUCERS; i++) {
        args[i] = (Race){&gate, owner, 0, -1, 0};
        CHECK(pthread_create(&threads[i], NULL, submit_during_retire, &args[i]) == 0);
    }
    release_gate(&gate, PRODUCERS); CHECK(pcc_gui_protocol_retire(owner) == 0);
    int64_t next = open_owner(), out = 71; CHECK(next > ready);
    for (int i = 0; i < PRODUCERS; i++) CHECK(pthread_join(threads[i], NULL) == 0);
    CHECK(pcc_gui_protocol_submit(owner, NULL, 0, NULL, 0, &out) == 2 && out == 71);
    CHECK(pcc_gui_protocol_reply(next, claimed, NULL, 0, NULL, 0) == 2);
    CHECK(pcc_gui_protocol_fail(owner, claimed, -1) == 2 && pcc_gui_protocol_cancel(owner, ready) == 2);
    counts(1, 0, 0); CHECK(pcc_gui_protocol_retire(next) == 0);
    pthread_cond_destroy(&gate.condition); pthread_mutex_destroy(&gate.mutex);
}

static void failure_and_limits(void) {
    int64_t out = 71; fail_after = 0;
    CHECK(pcc_gui_protocol_open(&out) == 4 && out == 71); counts(0, 0, 0);
    int64_t owner = open_owner(); int baseline = allocations;
    for (int i = 0; i < 3; i++) {
        fail_after = i; out = 71;
        CHECK(pcc_gui_protocol_submit(owner, "m", 1, "b", 1, &out) == 4 && out == 71 && allocations == baseline);
        counts(1, 0, 0);
    }
    CHECK(pcc_gui_protocol_submit(owner, "x", PCC_PROTOCOL_METADATA+1, NULL, 0, &out) == 6 && out == 71);
    CHECK(pcc_gui_protocol_submit(owner, NULL, 0, "x", PCC_PROTOCOL_BODY+1, &out) == 6 && out == 71);
    _Alignas(int64_t) unsigned char unaligned[16];
    CHECK(pcc_gui_protocol_open((int64_t *)(unaligned+1)) == 2);
    int64_t key = empty_request(owner); CHECK(pcc_gui_protocol_request_claim(owner, key) == 0);
    int request_baseline = allocations;
    for (int i = 0; i < 2; i++) {
        fail_after = i;
        CHECK(pcc_gui_protocol_reply(owner, key, "m", 1, "b", 1) == 4 && allocations == request_baseline);
        counts(1, 1, 0);
    }
    CHECK(pcc_gui_protocol_reply(owner, key, NULL, 0, NULL, 0) == 0);
    take_without_bytes(owner, key, 1, 0);
    for (int i = 0; i < PCC_PROTOCOL_REQUESTS; i++) key = empty_request(owner);
    CHECK(pcc_gui_protocol_submit(owner, NULL, 0, NULL, 0, &out) == 6 && out == 71);
    CHECK(pcc_gui_protocol_cancel(owner, key) == 0); take_without_bytes(owner, key, 3, 0);
    CHECK(empty_request(owner) > key); CHECK(pcc_gui_protocol_retire(owner) == 0);
    int64_t keys[PCC_PROTOCOL_OWNERS];
    for (int i = 0; i < PCC_PROTOCOL_OWNERS; i++) keys[i] = open_owner();
    CHECK(pcc_gui_protocol_open(&out) == 6 && out == 71);
    for (int i = 0; i < PCC_PROTOCOL_OWNERS; i++) CHECK(pcc_gui_protocol_retire(keys[i]) == 0);
    owner = open_owner(); unsigned char *large = calloc(PCC_PROTOCOL_BODY, 1); CHECK(large != NULL);
    int64_t first = 0;
    for (int i = 0; i < PCC_PROTOCOL_TOTAL / PCC_PROTOCOL_BODY; i++) {
        CHECK(pcc_gui_protocol_submit(owner, NULL, 0, large, PCC_PROTOCOL_BODY, &key) == 0);
        if (!i) first = key;
    }
    CHECK(pcc_gui_protocol_submit(owner, NULL, 0, "x", 1, &out) == 6 && out == 71);
    CHECK(pcc_gui_protocol_request_claim(owner, first) == 0);
    CHECK(pcc_gui_protocol_reply(owner, first, NULL, 0, "x", 1) == 6);
    CHECK(pcc_gui_protocol_cancel(owner, first) == 0); take_without_bytes(owner, first, 3, 0);
    CHECK(pcc_gui_protocol_submit(owner, NULL, 0, "x", 1, &key) == 0);
    free(large); CHECK(pcc_gui_protocol_retire(owner) == 0); counts(0, 0, 0);
    pcc_protocol_next = INT64_MAX - 1; owner = open_owner(); CHECK(owner == INT64_MAX - 1);
    CHECK(pcc_gui_protocol_submit(owner, NULL, 0, NULL, 0, &out) == 6 && out == 71);
    CHECK(pcc_gui_protocol_retire(owner) == 0 && pcc_gui_protocol_open(&out) == 6 && out == 71);
    CHECK(allocations == 0); counts(0, 0, 0);
}
int main(void) { @autoreleasepool {
    byte_round_trip(); concurrent_fifo(); concurrent_completion(); concurrent_retirement(); failure_and_limits();
    puts("PCC_NATIVE_PROTOCOL_OK binary=1 fifo_workers=4 claim=1 retry=1 terminal_race=1 retire_race=1 stale=1 limits=1 allocations=0");
    return 0;
}}
