// Build with PCC_GUI_MEDIA_TEST_LIBRARY for the controlled generated-handler
// integration. The fixture starts no OS access request and opens no window.
#include "../../pcc_gui/native/pcc_gui_metal_render_bridge.m"
#include <dispatch/dispatch.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>

// The injected provider may retain a completion after its document retires,
// just as AVFoundation may. Keys are the broker's immutable request keys.
static pthread_mutex_t fixture_lock = PTHREAD_MUTEX_INITIALIZER;
static int64_t fixture_keys[256];
static PccMediaCompletion fixture_completions[256];

int64_t pcc_gui_test_media_status(int64_t observed, int64_t *out) {
    return pcc_media_status_with(^int64_t(NSInteger *raw) {
        *raw = (NSInteger)observed;
        return 0;
    }, out);
}
int64_t pcc_gui_test_media_ask(int64_t owner, int64_t *out) {
    if (![NSThread isMainThread] || !pcc_media_output(out)) return 2;
    __block PccMediaCompletion callback = nil;
    int64_t key = 0;
    int64_t status = pcc_media_ask_with(owner, ^int64_t(PccMediaCompletion completion) {
        callback = [completion copy];
        return callback ? 0 : 4;
    }, &key);
    if (status) return status;
    if (callback) {
        pthread_mutex_lock(&fixture_lock);
        size_t slot = 0;
        while (slot < 256 && fixture_keys[slot]) slot++;
        if (slot < 256) {
            fixture_keys[slot] = key;
            fixture_completions[slot] = callback;
        }
        pthread_mutex_unlock(&fixture_lock);
        if (slot == 256) pcc_gui_protocol_fail(owner, key, 6);
    }
    *out = key;
    return 0;
}
int64_t pcc_gui_test_media_finish(int64_t key, int64_t granted) {
    if (key <= 0 || (granted != 0 && granted != 1)) return 2;
    PccMediaCompletion callback = nil;
    pthread_mutex_lock(&fixture_lock);
    for (size_t i = 0; i < 256; i++) {
        if (fixture_keys[i] == key) {
            callback = fixture_completions[i];
            fixture_completions[i] = nil;
            fixture_keys[i] = 0;
            break;
        }
    }
    pthread_mutex_unlock(&fixture_lock);
    if (!callback) return 2;
    callback(granted != 0);
    return 0;
}
int64_t pcc_gui_test_media_pending(int64_t *out) {
    if (![NSThread isMainThread] || !pcc_media_output(out)) return 2;
    int64_t count = 0;
    pthread_mutex_lock(&fixture_lock);
    for (size_t i = 0; i < 256; i++) if (fixture_keys[i]) count++;
    pthread_mutex_unlock(&fixture_lock);
    *out = count;
    return 0;
}

#ifndef PCC_GUI_MEDIA_TEST_LIBRARY
#define CHECK(x) do { if (!(x)) { fprintf(stderr, "media assertion %d: %s\n", __LINE__, #x); exit(90); } } while (0)
static int64_t open_owner(void) {
    int64_t owner = -1;
    CHECK(pcc_gui_protocol_open(&owner) == 0 && owner > 0);
    return owner;
}
static int64_t ask(int64_t owner) {
    int64_t key = -1;
    CHECK(pcc_gui_test_media_ask(owner, &key) == 0 && key > owner);
    return key;
}
static void counts(int64_t owners, int64_t requests, int64_t bytes, int64_t callbacks) {
    int64_t o = -1, r = -1, b = -1, c = -1;
    CHECK(pcc_gui_protocol_live_counts(&o, &r, &b) == 0);
    CHECK(pcc_gui_test_media_pending(&c) == 0);
    CHECK(o == owners && r == requests && b == bytes && c == callbacks);
}
static void pending(int64_t owner, int64_t key) {
    int64_t ready = 77, kind = 78, code = 79, meta = 80, body = 81;
    CHECK(pcc_gui_protocol_response_peek(owner, key, &ready, &kind, &code, &meta, &body) == 0);
    CHECK(!ready && kind == 78 && code == 79 && meta == 80 && body == 81);
}
static void take(int64_t owner, int64_t key, int64_t expected_kind, int64_t expected_code, int expected_byte) {
    int64_t ready = 0, kind = 0, code = 0, meta = -1, body = -1;
    CHECK(pcc_gui_protocol_response_peek(owner, key, &ready, &kind, &code, &meta, &body) == 0);
    CHECK(ready && kind == expected_kind && code == expected_code && meta == 0);
    CHECK(body == (expected_kind == 1 ? 1 : 0));
    unsigned char result = 0xce;
    if (body) {
        kind = 71; code = 72;
        CHECK(pcc_gui_protocol_response_take(owner, key, NULL, 0, &result, 0, &kind, &code) == 5);
        CHECK(result == 0xce && kind == 71 && code == 72);
    }
    CHECK(pcc_gui_protocol_response_take(owner, key, NULL, 0, body ? &result : NULL, body,
                                         &kind, &code) == 0);
    CHECK(kind == expected_kind && code == expected_code);
    if (body) CHECK(result == expected_byte);
    CHECK(pcc_gui_protocol_response_take(owner, key, NULL, 0, NULL, 0, &kind, &code) == 2);
}
static void worker(void (^action)(void)) {
    dispatch_group_t group = dispatch_group_create();
    dispatch_group_async(group, dispatch_get_global_queue(QOS_CLASS_DEFAULT, 0), ^{
        CHECK(![NSThread isMainThread]); action();
    });
    CHECK(dispatch_group_wait(group, dispatch_time(DISPATCH_TIME_NOW, 5 * NSEC_PER_SEC)) == 0);
}
static void status_cases(void) {
    for (int value = 0; value < 4; value++) {
        int64_t observed = -1;
        CHECK(pcc_gui_test_media_status(value, &observed) == 0 && observed == value);
    }
    int64_t out = -1;
    CHECK(pcc_gui_test_media_status(91, &out) == 0 && out == PCC_GUI_MICROPHONE_UNKNOWN);
    out = 71;
    CHECK(pcc_media_status_with(^int64_t(NSInteger *raw) { return 4; }, &out) == 4 && out == 71);
    CHECK(pcc_media_status_with(^int64_t(NSInteger *raw) {
        @throw [NSException exceptionWithName:@"TestStatusFailure" reason:@"injected" userInfo:nil];
    }, &out) == 4 && out == 71);
    CHECK(pcc_gui_test_media_status(0, NULL) == 2);
    _Alignas(int64_t) unsigned char unaligned[16];
    CHECK(pcc_gui_test_media_status(0, (int64_t *)(unaligned+1)) == 2);
}
static void request_cases(void) {
    int64_t owner = open_owner(), key = ask(owner);
    pending(owner, key); counts(1, 1, 0, 1);
    worker(^{ CHECK(pcc_gui_test_media_finish(key, 1) == 0); });
    CHECK(pcc_gui_test_media_finish(key, 0) == 2);
    counts(1, 1, 1, 0); take(owner, key, 1, 0, 1);
    key = ask(owner); int64_t denied = key;
    worker(^{ CHECK(pcc_gui_test_media_finish(denied, 0) == 0); });
    take(owner, key, 1, 0, 0);

    // The first terminal result survives duplicate or throwing native starts.
    CHECK(pcc_media_ask_with(owner, ^int64_t(PccMediaCompletion complete) {
        complete(YES); complete(NO);
        @throw [NSException exceptionWithName:@"TestAfterCompletion" reason:@"injected" userInfo:nil];
    }, &key) == 0);
    take(owner, key, 1, 0, 1);
    CHECK(pcc_media_ask_with(owner, ^int64_t(PccMediaCompletion complete) { return 4; }, &key) == 0);
    take(owner, key, 2, 4, 0);
    CHECK(pcc_media_ask_with(owner, ^int64_t(PccMediaCompletion complete) {
        @throw [NSException exceptionWithName:@"TestBeforeCompletion" reason:@"injected" userInfo:nil];
    }, &key) == 0);
    take(owner, key, 2, 4, 0);

    int64_t earlier = 0, out = 71;
    CHECK(pcc_gui_protocol_submit(owner, "x", 1, NULL, 0, &earlier) == 0);
    CHECK(pcc_media_ask_with(owner, ^int64_t(PccMediaCompletion complete) { CHECK(0); return 0; }, &out) == 5 && out == 71);
    counts(1, 1, 1, 0);
    CHECK(pcc_gui_protocol_cancel(owner, earlier) == 0); take(owner, earlier, 3, 0, 0);
    worker(^{
        int64_t local = 71;
        CHECK(pcc_media_status_with(^int64_t(NSInteger *raw) { CHECK(0); return 0; }, &local) == 2 && local == 71);
        CHECK(pcc_media_ask_with(owner, ^int64_t(PccMediaCompletion complete) { CHECK(0); return 0; }, &local) == 2 && local == 71);
    });
    CHECK(pcc_gui_protocol_retire(owner) == 0); counts(0, 0, 0, 0);
}
static void retirement_cases(void) {
    int64_t owner = open_owner(), cancelled = ask(owner);
    CHECK(pcc_gui_protocol_cancel(owner, cancelled) == 0);
    worker(^{ CHECK(pcc_gui_test_media_finish(cancelled, 1) == 0); });
    take(owner, cancelled, 3, 0, 0);
    int64_t old = ask(owner);
    CHECK(pcc_gui_protocol_retire(owner) == 0); counts(0, 0, 0, 1);
    int64_t replacement = open_owner(), fresh = ask(replacement);
    CHECK(replacement > old && fresh > replacement);
    worker(^{ CHECK(pcc_gui_test_media_finish(old, 1) == 0); });
    pending(replacement, fresh); counts(1, 1, 0, 1);
    worker(^{ CHECK(pcc_gui_test_media_finish(fresh, 0) == 0); });
    take(replacement, fresh, 1, 0, 0);
    int64_t out = 71;
    CHECK(pcc_media_ask_with(replacement, ^int64_t(PccMediaCompletion complete) {
        CHECK(pcc_gui_protocol_retire(replacement) == 0); complete(YES); return 0;
    }, &out) == 2 && out == 71);
    counts(0, 0, 0, 0);
}
static void racing_completions(void) {
    int64_t owner = open_owner(), key = -1;
    __block PccMediaCompletion callback = nil;
    CHECK(pcc_media_ask_with(owner, ^int64_t(PccMediaCompletion complete) {
        callback = [complete copy]; return 0;
    }, &key) == 0 && callback);
    dispatch_group_t group = dispatch_group_create();
    dispatch_queue_t queue = dispatch_get_global_queue(QOS_CLASS_DEFAULT, 0);
    dispatch_group_async(group, queue, ^{ CHECK(![NSThread isMainThread]); callback(YES); });
    dispatch_group_async(group, queue, ^{ CHECK(![NSThread isMainThread]); callback(NO); });
    CHECK(dispatch_group_wait(group, dispatch_time(DISPATCH_TIME_NOW, 5 * NSEC_PER_SEC)) == 0);
    int64_t kind = 0, code = 0; unsigned char result = 0xce;
    CHECK(pcc_gui_protocol_response_take(owner, key, NULL, 0, &result, 1, &kind, &code) == 0);
    CHECK(kind == 1 && code == 0 && (result == 0 || result == 1));
    CHECK(pcc_gui_protocol_response_take(owner, key, NULL, 0, NULL, 0, &kind, &code) == 2);
    callback = nil; CHECK(pcc_gui_protocol_retire(owner) == 0); counts(0, 0, 0, 0);
}
static void completion_capacity(void) {
    int64_t filled = open_owner(), owner = open_owner(), key = 0;
    unsigned char *bytes = calloc(PCC_PROTOCOL_BODY, 1); CHECK(bytes != NULL);
    for (int i = 0; i < PCC_PROTOCOL_TOTAL / PCC_PROTOCOL_BODY; i++) {
        CHECK(pcc_gui_protocol_submit(filled, NULL, 0, bytes, PCC_PROTOCOL_BODY, &key) == 0);
    }
    free(bytes);
    int64_t pending_key = ask(owner);
    worker(^{ CHECK(pcc_gui_test_media_finish(pending_key, 1) == 0); });
    take(owner, pending_key, 2, 6, 0);
    CHECK(pcc_gui_protocol_retire(filled) == 0 && pcc_gui_protocol_retire(owner) == 0);
    counts(0, 0, 0, 0);
}
int main(int argc, const char **argv) { @autoreleasepool {
    CHECK(argc == 1 || (argc == 2 && strcmp(argv[1], "--injected-only") == 0));
    int64_t observed = -1;
    if (argc == 1) {
        CHECK(pcc_gui_media_microphone_status(&observed) == 0);
        CHECK(observed >= PCC_GUI_MICROPHONE_NOT_DETERMINED && observed <= PCC_GUI_MICROPHONE_UNKNOWN);
    }
    status_cases(); request_cases(); retirement_cases(); racing_completions(); completion_capacity();
    printf("PCC_NATIVE_MEDIA_OK readonly_status=%lld injected_ask=1 worker=1 duplicate=1 failure=1 cancel=1 retire=1 capacity=1 counts=0 real_asks=0\n", (long long)observed);
    return 0;
}}
#endif
