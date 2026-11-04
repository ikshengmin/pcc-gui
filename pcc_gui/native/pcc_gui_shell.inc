// Desktop URL launches and file selection use AppKit on the UI thread.
// The system completion holds queue identities only, never source callbacks.
#import <AppKit/AppKit.h>
#include <stdlib.h>
#include <string.h>
#include "pcc_gui_shell.h"
#include "pcc_gui_protocol.h"

typedef BOOL (^PccShellLookup)(NSURL *);
typedef void (^PccShellCompletion)(BOOL);
typedef void (^PccShellLauncher)(NSURL *, BOOL, PccShellCompletion);
typedef void (^PccShellSelector)(NSString *);

static int64_t pcc_shell_text(const void *bytes, int64_t length, NSString **out) {
    if (length < 0 || (length && !bytes)) return 2;
    if (length > 64 * 1024) return 6;
    if (length && memchr(bytes, 0, (size_t)length)) return 2;
    *out = length ? [[NSString alloc] initWithBytes:bytes length:(NSUInteger)length
                                            encoding:NSUTF8StringEncoding] : @"";
    return *out ? 0 : 2;
}
static int64_t pcc_shell_open_with(int64_t owner, const void *bytes, int64_t length,
        int64_t activate, int64_t *out, PccShellLookup lookup, PccShellLauncher launch) {
    if (![NSThread isMainThread] || !pcc_protocol_outputs(&out, 1) ||
        (activate != 0 && activate != 1)) return 2;
    if (!lookup || !launch) return 4;
    @autoreleasepool {
        int64_t request = 0;
        @try {
            NSString *text;
            int64_t status = pcc_shell_text(bytes, length, &text);
            if (status) return status;
            status = pcc_protocol_begin_operation(owner, &request);
            if (status) return status;
            NSURL *url = [NSURL URLWithString:text];
            if (!url.scheme.length) {
                pcc_gui_protocol_fail(owner, request, PCC_GUI_SHELL_INVALID_URL);
            } else if (!lookup(url)) {
                pcc_gui_protocol_fail(owner, request, PCC_GUI_SHELL_NO_APPLICATION);
            } else {
                // Native provider lookup can reenter UI code and retire the
                // lease. Do not launch if it cancelled or consumed our request.
                int64_t ready, kind, code, metadata, body;
                status = pcc_gui_protocol_response_peek(owner, request, &ready, &kind, &code, &metadata, &body);
                if (status) return status;
                if (!ready) launch(url, activate != 0, ^(BOOL succeeded) {
                    if (succeeded) pcc_gui_protocol_reply(owner, request, NULL, 0, NULL, 0);
                    else pcc_gui_protocol_fail(owner, request, PCC_GUI_SHELL_OPEN_FAILED);
                });
            }
        } @catch (NSException *error) {
            if (!request) return 4;
            pcc_gui_protocol_fail(owner, request, 4);
        }
        int64_t ready, kind, code, metadata, body;
        int64_t status = pcc_gui_protocol_response_peek(owner, request, &ready, &kind, &code, &metadata, &body);
        if (status) return status;
        *out = request;
        return 0;
    }
}

int64_t pcc_gui_shell_open_external(int64_t owner, const void *url, int64_t length,
                                    int64_t activate, int64_t *out) {
    return pcc_shell_open_with(owner, url, length, activate, out, ^BOOL(NSURL *value) {
        return [NSWorkspace.sharedWorkspace URLForApplicationToOpenURL:value] != nil;
    }, ^(NSURL *value, BOOL activates, PccShellCompletion complete) {
        NSWorkspaceOpenConfiguration *config = [NSWorkspaceOpenConfiguration configuration];
        config.activates = activates;
        [NSWorkspace.sharedWorkspace openURL:value configuration:config
                            completionHandler:^(NSRunningApplication *app, NSError *error) {
            complete(error == nil);
        }];
    });
}

static int64_t pcc_shell_reveal_with(int64_t owner, const void *bytes, int64_t length,
                                     PccShellSelector select) {
    if (![NSThread isMainThread]) return 2;
    if (!select) return 4;
    @autoreleasepool { @try {
        int64_t ready, key, metadata, body;
        int64_t status = pcc_gui_protocol_request_peek(owner, &ready, &key, &metadata, &body);
        if (status) return status;
        NSString *path;
        status = pcc_shell_text(bytes, length, &path);
        if (status) return status;
        if (![path hasPrefix:@"/"]) {
            char *absolute = realpath(path.UTF8String, NULL);
            @try { path = absolute ? [NSString stringWithUTF8String:absolute] : @""; }
            @finally { free(absolute); }
        }
        if (path) select(path);
        return 0;
    } @catch (NSException *error) { return 4; } }
}
int64_t pcc_gui_shell_show_item_in_folder(int64_t owner, const void *path, int64_t length) {
    return pcc_shell_reveal_with(owner, path, length, ^(NSString *value) {
        [NSWorkspace.sharedWorkspace selectFile:value inFileViewerRootedAtPath:@""];
    });
}
