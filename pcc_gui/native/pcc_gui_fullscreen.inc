// Included by the canonical Metal/AppKit bridge. AppKit never runs source callbacks.
#import <AppKit/AppKit.h>
#include "pcc_gui_fullscreen.h"

@interface PCCFullscreenLease : NSObject
@property(nonatomic) int64_t key;
@property(nonatomic, weak) NSWindow *window;
@property(nonatomic) BOOL active, closed, setting, lastFull;
@property(nonatomic) NSInteger pending;  // -1 idle, 0 leaving, 1 entering
@property(nonatomic) int64_t failure;
@property(nonatomic, strong) NSObject *scheduled;
@property(nonatomic, strong) NSMutableArray *tokens;
@property(nonatomic, strong) NSMutableArray<NSNumber *> *events;
@end
@implementation PCCFullscreenLease
@end

static NSHashTable<NSWindow *> *pcc_fs_windows;
static id pcc_fs_close_token;
static NSMutableDictionary<NSNumber *, PCCFullscreenLease *> *pcc_fs_leases;
static int64_t pcc_fs_next_key = 1;

static void pcc_fs_remove_tokens(PCCFullscreenLease *lease) {
    NSNotificationCenter *center = NSNotificationCenter.defaultCenter;
    for (id token in lease.tokens) [center removeObserver:token];
    [lease.tokens removeAllObjects];
}

static void pcc_fs_publish(PCCFullscreenLease *lease, int64_t kind) {
    if (lease.failure) return;
    if (lease.events.count >= 256) { lease.failure = 6; return; }
    [lease.events addObject:@(kind)];
}

static void pcc_fs_forget_window(NSWindow *window) {
    if (![NSThread isMainThread]) {
        dispatch_async(dispatch_get_main_queue(), ^{ pcc_fs_forget_window(window); });
        return;
    }
    if (![pcc_fs_windows containsObject:window]) return;
    [pcc_fs_windows removeObject:window];
    for (PCCFullscreenLease *lease in pcc_fs_leases.objectEnumerator) {
        if (lease.window != window) continue;
        lease.closed = YES;
        lease.scheduled = nil;
        lease.window = nil;
        lease.pending = -1;
        pcc_fs_publish(lease, 3);
        pcc_fs_remove_tokens(lease);
    }
    if (pcc_fs_windows.count == 0) {
        [NSNotificationCenter.defaultCenter removeObserver:pcc_fs_close_token];
        pcc_fs_close_token = nil;
        pcc_fs_windows = nil;
    }
}

static void pcc_fs_track_window(NSWindow *window) {
    if (![NSThread isMainThread]) return;
    if (!pcc_fs_windows) {
        pcc_fs_windows = [NSHashTable weakObjectsHashTable];
        pcc_fs_close_token = [NSNotificationCenter.defaultCenter
            addObserverForName:NSWindowWillCloseNotification object:nil queue:nil
            usingBlock:^(NSNotification *note) {
                pcc_fs_forget_window(note.object);
            }];
    }
    [pcc_fs_windows addObject:window];
}

static void pcc_fs_notification(PCCFullscreenLease *lease, BOOL did, BOOL full) {
    if (!lease.active || lease.closed) return;
    if (!did) { lease.scheduled = nil; lease.pending = full; return; }
    if (lease.pending != -1 && lease.pending != full) return;
    lease.scheduled = nil;
    lease.pending = -1;
    if (lease.lastFull == full) return;
    lease.lastFull = full;
    pcc_fs_publish(lease, full ? 1 : 2);
}

static void pcc_fs_observe(PCCFullscreenLease *lease, NSNotificationName name,
                           BOOL did, BOOL full) {
    __weak PCCFullscreenLease *weakLease = lease;
    id token = [NSNotificationCenter.defaultCenter addObserverForName:name
        object:lease.window queue:nil usingBlock:^(NSNotification *unused) {
            if ([NSThread isMainThread]) pcc_fs_notification(weakLease, did, full);
            else dispatch_async(dispatch_get_main_queue(), ^{ pcc_fs_notification(weakLease, did, full); });
        }];
    [lease.tokens addObject:token];
}

static BOOL pcc_fs_out(int64_t *word) {
    return word != NULL && (uintptr_t)word % _Alignof(int64_t) == 0;
}

int64_t pcc_gui_fullscreen_acquire(void *handle, int64_t *out) {
    if (![NSThread isMainThread] || !handle || !pcc_fs_out(out)) return 2;
    NSWindow *window = nil;
    for (NSWindow *tracked in pcc_fs_windows) {
        if ((__bridge void *)tracked == handle) { window = tracked; break; }
    }
    if (!window) return 2;
    for (PCCFullscreenLease *lease in pcc_fs_leases.objectEnumerator)
        if (lease.window == window) return 5;
    if (pcc_fs_leases.count >= 256 || pcc_fs_next_key == INT64_MAX) return 6;

    PCCFullscreenLease *lease = [PCCFullscreenLease new];
    lease.key = pcc_fs_next_key++;
    lease.window = window;
    lease.active = YES;
    lease.pending = -1;
    lease.tokens = [NSMutableArray array];
    lease.events = [NSMutableArray array];
    if (!pcc_fs_leases) pcc_fs_leases = [NSMutableDictionary dictionary];
    pcc_fs_leases[@(lease.key)] = lease;
    @try {
        lease.lastFull = (window.styleMask & NSWindowStyleMaskFullScreen) != 0;
        if (!lease.active || lease.closed) { pcc_gui_fullscreen_release(lease.key); return 2; }
        pcc_fs_observe(lease, NSWindowWillEnterFullScreenNotification, NO, YES);
        pcc_fs_observe(lease, NSWindowWillExitFullScreenNotification, NO, NO);
        pcc_fs_observe(lease, NSWindowDidEnterFullScreenNotification, YES, YES);
        pcc_fs_observe(lease, NSWindowDidExitFullScreenNotification, YES, NO);
    } @catch (NSException *exception) {
        pcc_gui_fullscreen_release(lease.key);
        return 4;
    }
    *out = lease.key;
    return 0;
}

int64_t pcc_gui_fullscreen_state(int64_t key, int64_t *closed, int64_t *full) {
    if (![NSThread isMainThread] || !pcc_fs_out(closed) || !pcc_fs_out(full) || closed == full) return 2;
    PCCFullscreenLease *lease = pcc_fs_leases[@(key)];
    if (!lease) return 2;
    BOOL observed = NO;
    @try {
        observed = (lease.window.styleMask & NSWindowStyleMaskFullScreen) != 0;
    } @catch (NSException *exception) { return 4; }
    if (!lease.active) return 2;
    *closed = lease.closed;
    *full = lease.closed ? 0 : observed;
    return 0;
}

static int64_t pcc_fs_toggle(PCCFullscreenLease *lease, BOOL full) {
    NSWindow *window = lease.window;
    if (!lease.active || lease.closed || !window) return 2;
    @try {
        BOOL current = (window.styleMask & NSWindowStyleMaskFullScreen) != 0;
        BOOL capable = (window.collectionBehavior & NSWindowCollectionBehaviorFullScreenPrimary) != 0;
        if (!lease.active || lease.closed) return 2;
        if (lease.pending != full) return 5;
        if (current == full || !capable) { lease.pending = -1; return 0; }
        [window toggleFullScreen:nil];
    } @catch (NSException *exception) { lease.pending = -1; return 4; }
    return 0;
}

int64_t pcc_gui_fullscreen_set(int64_t key, int64_t full) {
    if (![NSThread isMainThread] || (full != 0 && full != 1)) return 2;
    PCCFullscreenLease *lease = pcc_fs_leases[@(key)];
    if (!lease || lease.closed) return 2;
    if (lease.failure) return lease.failure;
    if (lease.setting) return 5;
    if (lease.pending != -1) return lease.pending == full ? 0 : 5;
    lease.setting = YES;
    @try {
        NSWindow *window = lease.window;
        BOOL current = (window.styleMask & NSWindowStyleMaskFullScreen) != 0;
        BOOL capable = (window.collectionBehavior & NSWindowCollectionBehaviorFullScreenPrimary) != 0;
        if (!lease.active || lease.closed) return 2;
        if (lease.pending != -1) return lease.pending == full ? 0 : 5;
        if (current == full || !capable) return 0;
        BOOL visible = window.visible;
        if (!lease.active || lease.closed) return 2;
        if (lease.pending != -1) return lease.pending == full ? 0 : 5;
        lease.pending = full;
        if (!visible) return pcc_fs_toggle(lease, full);
        // Electron defers a visible window's toggle beyond the current AppKit turn.
        NSObject *ticket = [NSObject new];
        lease.scheduled = ticket;
        __weak PCCFullscreenLease *weakLease = lease;
        dispatch_async(dispatch_get_main_queue(), ^{
            PCCFullscreenLease *live = weakLease;
            if (!live.active || live.closed || live.scheduled != ticket) return;
            live.scheduled = nil;
            int64_t status = pcc_fs_toggle(live, full);
            if (live.active && !live.closed && status != 0) live.failure = status;
        });
        return 0;
    } @catch (NSException *exception) { return 4; }
    @finally { lease.setting = NO; }
}

int64_t pcc_gui_fullscreen_take(int64_t key, int64_t *out) {
    if (![NSThread isMainThread] || !pcc_fs_out(out)) return 2;
    PCCFullscreenLease *lease = pcc_fs_leases[@(key)];
    if (!lease) return 2;
    if (lease.failure) return lease.failure;
    NSNumber *event = lease.events.firstObject;
    if (event) [lease.events removeObjectAtIndex:0];
    *out = event.longLongValue;
    return 0;
}

int64_t pcc_gui_fullscreen_release(int64_t key) {
    if (![NSThread isMainThread]) return 2;
    PCCFullscreenLease *lease = pcc_fs_leases[@(key)];
    if (!lease) return 2;
    lease.active = NO;
    lease.scheduled = nil;
    [pcc_fs_leases removeObjectForKey:@(key)];
    pcc_fs_remove_tokens(lease);
    if (pcc_fs_leases.count == 0) pcc_fs_leases = nil;
    return 0;
}

int64_t pcc_gui_fullscreen_live_count(int64_t *out) {
    if (![NSThread isMainThread] || !pcc_fs_out(out)) return 2;
    *out = (int64_t)pcc_fs_leases.count;
    return 0;
}
