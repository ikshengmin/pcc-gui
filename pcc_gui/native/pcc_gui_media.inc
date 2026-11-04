// The AVFoundation completion owns only native request identities. Resolution,
// cancellation, storage limits and document retirement belong to the protocol queue.
#import <AVFoundation/AVCaptureDevice.h>
#include <dlfcn.h>
#include "pcc_gui_media.h"
#include "pcc_gui_protocol.h"

typedef void (^PccMediaCompletion)(BOOL granted);
typedef int64_t (^PccMediaReader)(NSInteger *status);
typedef int64_t (^PccMediaStarter)(PccMediaCompletion completion);

// Resolve the named OS framework when the capability is selected. Existing
// consumers of the canonical bridge do not have to link AVFoundation. The
// successful framework handle remains loaded for the lifetime of the process.
static void *pcc_media_framework;
static Class pcc_media_device;
static NSString *pcc_media_audio;
static BOOL pcc_media_loading;
static int64_t pcc_media_load(void) {
    if (pcc_media_framework) return 0;
    if (pcc_media_loading) return 4;
    pcc_media_loading = YES;
    void *handle = NULL;
    @try {
        handle = dlopen("/System/Library/Frameworks/AVFoundation.framework/AVFoundation",
                        RTLD_NOW | RTLD_LOCAL);
        if (!handle) return 4;
        Class device = NSClassFromString(@"AVCaptureDevice");
        const CFStringRef *audio = dlsym(handle, "AVMediaTypeAudio");
        if (!device || !audio || !*audio ||
            ![device respondsToSelector:@selector(authorizationStatusForMediaType:)] ||
            ![device respondsToSelector:@selector(requestAccessForMediaType:completionHandler:)]) return 4;
        pcc_media_audio = (__bridge NSString *)*audio;
        pcc_media_device = device;
        pcc_media_framework = handle;
        handle = NULL;
        return 0;
    } @finally {
        if (handle) dlclose(handle);
        pcc_media_loading = NO;
    }
}

static BOOL pcc_media_output(int64_t *out) {
    return out && (uintptr_t)out % _Alignof(int64_t) == 0;
}
static int64_t pcc_media_status_with(PccMediaReader reader, int64_t *out) {
    if (![NSThread isMainThread] || !pcc_media_output(out)) return 2;
    if (!reader) return 4;
    @autoreleasepool { @try {
        NSInteger raw = 0;
        if (reader(&raw) != 0) return 4;
        switch (raw) {
            case AVAuthorizationStatusNotDetermined: *out = PCC_GUI_MICROPHONE_NOT_DETERMINED; break;
            case AVAuthorizationStatusRestricted: *out = PCC_GUI_MICROPHONE_RESTRICTED; break;
            case AVAuthorizationStatusDenied: *out = PCC_GUI_MICROPHONE_DENIED; break;
            case AVAuthorizationStatusAuthorized: *out = PCC_GUI_MICROPHONE_GRANTED; break;
            default: *out = PCC_GUI_MICROPHONE_UNKNOWN; break;
        }
        return 0;
    } @catch (NSException *error) { return 4; } }
}
int64_t pcc_gui_media_microphone_status(int64_t *out) {
    return pcc_media_status_with(^int64_t(NSInteger *raw) {
        if (pcc_media_load() != 0) return 4;
        *raw = [pcc_media_device authorizationStatusForMediaType:pcc_media_audio];
        return 0;
    }, out);
}

static int64_t pcc_media_ask_with(int64_t owner, PccMediaStarter starter, int64_t *out) {
    if (![NSThread isMainThread] || !pcc_media_output(out)) return 2;
    if (!starter) return 4;
    int64_t request = 0, status = pcc_protocol_begin_operation(owner, &request);
    if (status) return status;
    @autoreleasepool {
        @try {
            status = starter(^(BOOL granted) {
                unsigned char decision = granted ? 1 : 0;
                int64_t result = pcc_gui_protocol_reply(owner, request, NULL, 0, &decision, 1);
                if (result == 4 || result == 6) pcc_gui_protocol_fail(owner, request, result);
            });
        } @catch (NSException *error) { status = 4; }
        if (status) pcc_gui_protocol_fail(owner, request, 4);
    }
    // A provider can finish synchronously, throw after finishing, or reenter
    // retirement. Publish the key only while its original owner still exists.
    int64_t ready, kind, code, metadata_len, body_len;
    status = pcc_gui_protocol_response_peek(owner, request, &ready, &kind, &code,
                                            &metadata_len, &body_len);
    if (status) return status;
    *out = request;
    return 0;
}
int64_t pcc_gui_media_microphone_ask(int64_t owner, int64_t *out) {
    return pcc_media_ask_with(owner, ^int64_t(PccMediaCompletion completion) {
        id usage = [NSBundle.mainBundle objectForInfoDictionaryKey:@"NSMicrophoneUsageDescription"];
        if (![usage isKindOfClass:NSString.class] ||
            ![(NSString *)usage stringByTrimmingCharactersInSet:NSCharacterSet.whitespaceAndNewlineCharacterSet].length)
            return 4;
        if (pcc_media_load() != 0) return 4;
        [pcc_media_device requestAccessForMediaType:pcc_media_audio completionHandler:completion];
        return 0;
    }, out);
}
