// Native window leases use real AppKit windows. The per-test subclass intercepts
// fullscreen toggles before they can display a window or enter a system Space.
#import <AppKit/AppKit.h>
#import <objc/runtime.h>
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include "../../pcc_gui/native/pcc_gui_fullscreen.h"

void *pcc_gui_metal_window_create(const char *, int64_t, int64_t);
int64_t pcc_gui_metal_window_close(void *);

@interface PCCFullscreenFixture : NSObject
@property(nonatomic) Class original;
@property(nonatomic) BOOL full, visible;
@property(nonatomic) int64_t key, toggles, mode, nestedStatus;
@property(nonatomic, weak) NSWindow *window;
@end
@implementation PCCFullscreenFixture
@end
static char fixture_key;
static NSMutableDictionary<NSValue *, PCCFullscreenFixture *> *fixtures;

static PCCFullscreenFixture *fixture(void *handle) {
    if (![NSThread isMainThread] || !handle) return nil;
    return fixtures[[NSValue valueWithPointer:handle]];
}

static NSWindowStyleMask fixture_mask(NSWindow *window, SEL cmd) {
    PCCFullscreenFixture *state = objc_getAssociatedObject(window, &fixture_key);
    IMP underlying = class_getMethodImplementation(state.original, cmd);
    NSWindowStyleMask flags = ((NSWindowStyleMask (*)(id,SEL))underlying)(window,cmd);
    return (flags & ~NSWindowStyleMaskFullScreen) | (state.full ? NSWindowStyleMaskFullScreen : 0);
}
static BOOL fixture_visible(NSWindow *window, SEL cmd) {
    PCCFullscreenFixture *state = objc_getAssociatedObject(window, &fixture_key);
    return state.visible;
}
static void fixture_toggle(NSWindow *window, SEL cmd, id sender) {
    PCCFullscreenFixture *state = objc_getAssociatedObject(window, &fixture_key);
    state.toggles++;
    if (state.mode == 1) [NSException raise:@"TestFullscreen" format:@"injected toggle failure"];
    if (state.mode == 2) state.nestedStatus = pcc_gui_fullscreen_set(state.key,state.full);
    if (state.mode == 3) state.nestedStatus = pcc_gui_fullscreen_release(state.key);
    [NSNotificationCenter.defaultCenter postNotificationName:
        (state.full ? NSWindowWillExitFullScreenNotification : NSWindowWillEnterFullScreenNotification) object:window];
}

static BOOL install(Class subclass, Class base, SEL selector, IMP implementation) {
    Method m = class_getInstanceMethod(base,selector);
    return m && class_addMethod(subclass,selector,implementation,method_getTypeEncoding(m));
}

int64_t pcc_gui_test_fullscreen_window(int64_t full, int64_t visible, void **out) {
    if (![NSThread isMainThread] || !out || (full & ~1) || (visible & ~1)) return 2;
    void *handle = pcc_gui_metal_window_create("PCC fullscreen fixture",128,96);
    if (!handle) return 4;
    NSWindow *window = (__bridge NSWindow *)handle;
    Class base=object_getClass(window);
    static Class subclass;
    if (!subclass) {
        subclass = objc_allocateClassPair(base,"PCCFullscreenInterceptWindow",0);
        if (!subclass || !install(subclass,base,@selector(styleMask),(IMP)fixture_mask) ||
            !install(subclass,base,@selector(isVisible),(IMP)fixture_visible) ||
            !install(subclass,base,@selector(toggleFullScreen:),(IMP)fixture_toggle)) {
            if (subclass) objc_disposeClassPair(subclass);
            subclass = Nil;
            pcc_gui_metal_window_close(handle);
            return 4;
        }
        objc_registerClassPair(subclass);
    }
    if (class_getSuperclass(subclass)!=base) { pcc_gui_metal_window_close(handle); return 4; }
    window.collectionBehavior |= NSWindowCollectionBehaviorFullScreenPrimary;
    PCCFullscreenFixture *state=[PCCFullscreenFixture new];
    state.window=window; state.original=base; state.full=full; state.visible=visible; state.nestedStatus=-1;
    objc_setAssociatedObject(window,&fixture_key,state,OBJC_ASSOCIATION_RETAIN_NONATOMIC);
    object_setClass(window,subclass);
    if (!fixtures) fixtures=[NSMutableDictionary dictionary];
    fixtures[[NSValue valueWithPointer:handle]]=state;
    *out=handle;
    return 0;
}

int64_t pcc_gui_test_fullscreen_complete(void *handle, int64_t full) {
    PCCFullscreenFixture *state=fixture(handle);
    if (!state || (full & ~1)) return 2;
    state.full = full;
    [NSNotificationCenter.defaultCenter postNotificationName:
        (full ? NSWindowDidEnterFullScreenNotification : NSWindowDidExitFullScreenNotification)
        object:state.window];
    return 0;
}

int64_t pcc_gui_test_fullscreen_stats(void *handle,int64_t *count,int64_t *nested) {
    PCCFullscreenFixture *state=fixture(handle);
    if (!state || !count || !nested || count==nested) return 2;
    *count=state.toggles; *nested=state.nestedStatus;
    return 0;
}

int64_t pcc_gui_test_fullscreen_close(void *handle) {
    PCCFullscreenFixture *state=fixture(handle);
    if (!state) return 2;
    NSWindow *window=state.window;
    [fixtures removeObjectForKey:[NSValue valueWithPointer:handle]];
    if (!fixtures.count) fixtures=nil;
    object_setClass(window,state.original);
    objc_setAssociatedObject(window,&fixture_key,nil,OBJC_ASSOCIATION_RETAIN_NONATOMIC);
    return pcc_gui_metal_window_close(handle);
}

#ifndef PCC_GUI_FULLSCREEN_TEST_LIBRARY
@interface PCCFullscreenOtherDelegate : NSObject <NSWindowDelegate>
@end
@implementation PCCFullscreenOtherDelegate
@end
struct Worker { int64_t key,status,out; };
static void *worker(void *arg) {
    struct Worker *v=arg;
    @autoreleasepool { v->status=pcc_gui_fullscreen_take(v->key,&v->out); }
    return NULL;
}
static void pump(void) {
    [[NSRunLoop mainRunLoop] runUntilDate:[NSDate dateWithTimeIntervalSinceNow:0.04]];
}

#define CHECK(expr) do { if (!(expr)) { fprintf(stderr,"fullscreen check failed at line %d\n",__LINE__); return 1; } } while(0)
int main(void) {
    @autoreleasepool {
        int64_t owner=-1, other=-1, closed=-1, full=-1, kind=-1, count=-1, nested=-1;
        void *ordinary=pcc_gui_metal_window_create("PCC ordinary hidden",160,120);
        CHECK(ordinary && ![(__bridge NSWindow *)ordinary isVisible]);
        CHECK(pcc_gui_fullscreen_acquire(ordinary,&owner)==0 && owner>0);
        CHECK(pcc_gui_fullscreen_state(owner,&closed,&full)==0 && !closed && !full);
        CHECK(pcc_gui_fullscreen_set(owner,0)==0 && pcc_gui_fullscreen_take(owner,&kind)==0 && !kind);
        CHECK(pcc_gui_metal_window_close(ordinary)==0);
        CHECK(pcc_gui_fullscreen_state(owner,&closed,&full)==0 && closed && !full);
        CHECK(pcc_gui_fullscreen_take(owner,&kind)==0 && kind==3);
        CHECK(pcc_gui_fullscreen_acquire(ordinary,&other)==2 && other==-1);
        CHECK(pcc_gui_fullscreen_release(owner)==0 && pcc_gui_fullscreen_release(owner)==2);
        CHECK(pcc_gui_fullscreen_acquire((void *)(uintptr_t)0x1234,&other)==2 && other==-1);

        void *handle=NULL,*sibling=NULL;
        CHECK(pcc_gui_test_fullscreen_window(1,0,&handle)==0 && pcc_gui_test_fullscreen_window(0,0,&sibling)==0);
        PCCFullscreenOtherDelegate *delegate=[PCCFullscreenOtherDelegate new];
        [(__bridge NSWindow *)handle setDelegate:delegate];
        CHECK(pcc_gui_fullscreen_acquire(handle,&owner)==0 && pcc_gui_fullscreen_acquire(handle,&other)==5 && other==-1);
        CHECK(pcc_gui_fullscreen_acquire(sibling,&other)==0 && other!=owner);
        CHECK(pcc_gui_fullscreen_state(owner,&closed,&full)==0 && !closed && full);
        struct Worker value={owner,-1,17};pthread_t thread;
        CHECK(pthread_create(&thread,NULL,worker,&value)==0 && pthread_join(thread,NULL)==0);
        CHECK(value.status==2 && value.out==17);
        CHECK(pcc_gui_fullscreen_state(owner,&full,&full)==2 && full==1);
        fixture(handle).key=owner; fixture(handle).mode=2;
        CHECK(pcc_gui_fullscreen_set(owner,0)==0 && pcc_gui_fullscreen_set(owner,0)==0);
        CHECK(pcc_gui_fullscreen_set(owner,1)==5);
        CHECK(pcc_gui_test_fullscreen_stats(handle,&count,&nested)==0 && count==1 && nested==5);
        CHECK(pcc_gui_test_fullscreen_complete(handle,0)==0 && pcc_gui_test_fullscreen_complete(handle,0)==0);
        CHECK(pcc_gui_fullscreen_take(owner,&kind)==0 && kind==2 && pcc_gui_fullscreen_take(owner,&kind)==0 && !kind);
        CHECK(pcc_gui_fullscreen_take(other,&kind)==0 && !kind);
        CHECK(pcc_gui_fullscreen_state(owner,&closed,&full)==0 && !closed && !full);
        fixture(handle).mode=1; CHECK(pcc_gui_fullscreen_set(owner,1)==4);
        fixture(handle).mode=0; CHECK(pcc_gui_fullscreen_set(owner,1)==0);
        CHECK(pcc_gui_test_fullscreen_complete(handle,1)==0 && pcc_gui_fullscreen_take(owner,&kind)==0 && kind==1);
        CHECK([(__bridge NSWindow *)handle delegate]==delegate);
        CHECK(pcc_gui_test_fullscreen_close(handle)==0 && pcc_gui_fullscreen_take(owner,&kind)==0 && kind==3);
        CHECK(pcc_gui_fullscreen_set(owner,0)==2 && pcc_gui_fullscreen_release(owner)==0);
        CHECK(pcc_gui_test_fullscreen_close(sibling)==0 && pcc_gui_fullscreen_release(other)==0);

        // A visible toggle waits for the next main turn. Retirement clears its ticket.
        CHECK(pcc_gui_test_fullscreen_window(1,1,&handle)==0);
        CHECK(pcc_gui_fullscreen_acquire(handle,&owner)==0 && pcc_gui_fullscreen_set(owner,0)==0);
        CHECK(pcc_gui_test_fullscreen_stats(handle,&count,&nested)==0 && count==0);
        CHECK(pcc_gui_fullscreen_release(owner)==0);
        pump();
        CHECK(pcc_gui_test_fullscreen_stats(handle,&count,&nested)==0 && count==0);
        CHECK(pcc_gui_fullscreen_acquire(handle,&owner)==0 && pcc_gui_fullscreen_set(owner,0)==0);
        pump();
        CHECK(pcc_gui_test_fullscreen_stats(handle,&count,&nested)==0 && count==1);
        CHECK(pcc_gui_test_fullscreen_complete(handle,0)==0 && pcc_gui_fullscreen_take(owner,&kind)==0 && kind==2);
        fixture(handle).mode=3; fixture(handle).key=owner;
        CHECK(pcc_gui_fullscreen_set(owner,1)==0); pump();
        CHECK(pcc_gui_test_fullscreen_stats(handle,&count,&nested)==0 && nested==0);
        kind=99;CHECK(pcc_gui_fullscreen_take(owner,&kind)==2 && kind==99);
        CHECK(pcc_gui_test_fullscreen_close(handle)==0);
        CHECK(pcc_gui_fullscreen_live_count(&count)==0 && count==0);
        puts("PCC_FULLSCREEN_OK hidden=1 isolated=1 deferred=1 reentrant=1 duplicate=1 closed=1 live=0 space_changes=0");
    }
    return 0;
}
#endif
