#import <AppKit/AppKit.h>
#import <QuartzCore/QuartzCore.h>
#include <stdint.h>
#include <stdio.h>
void *pcc_gui_metal_window_create(const char *, int64_t, int64_t);
int64_t pcc_gui_metal_window_close(void *);
int64_t pcc_gui_metal_window_text(void *, const char *, void *, int64_t, int64_t, int64_t);
int64_t pcc_gui_metal_pane_set(void *, const char *, void *, int64_t, int64_t, int64_t);
int64_t pcc_gui_metal_lifecycle_install(void *, uint64_t, void *);
int64_t pcc_gui_metal_lifecycle_probe(void *, const char *);
static int callbacks = 0;
static int32_t termination_status = 0;
static uint64_t expected_window = 0;
static int wrong_window = 0;
static int32_t receive(int32_t kind, uint64_t window, const void *payload,
                       uint64_t length, int32_t flags, int32_t code) {
  callbacks++;
  if (window != expected_window) wrong_window++;
  return kind == 7 ? termination_status : 0;
}
int main(void) {
  for (int i = 0; i < 3; i++) {
    __weak NSWindow *observed;
    __weak NSView *observed_content;
    __weak NSTextField *observed_text;
    __weak NSScrollView *observed_pane;
    __weak CALayer *observed_layer;
    @autoreleasepool {
      void *handle = pcc_gui_metal_window_create("window ownership", 320, 200);
      if (!handle) return 1;
      NSWindow *window = (__bridge NSWindow *)handle;
      observed = window;
      observed_content = [window contentView];
      expected_window = 77 + i;
      if (pcc_gui_metal_lifecycle_install(handle, expected_window, (void *)receive)) return 2;
      if (pcc_gui_metal_lifecycle_probe(handle, "/tmp/opened.txt")) return 3;
      int64_t label[5] = {0, 2, 2, 0, 0};
      if (pcc_gui_metal_window_text(handle, "label", label, 5, 12, 0xff000000)) return 7;
      int64_t text[5] = {20, 2, 20, 0, 0};
      if (pcc_gui_metal_window_text(handle, "text", text, 4, 12, 0xff000000)) return 8;
      int64_t spec[5] = {0, 4, 0, 0, 0};
      int64_t pane[5] = {2, 40, 200, 100, (int64_t)(intptr_t)spec};
      if (pcc_gui_metal_pane_set(handle, "text", pane, 4, 1, 0)) return 9;
      for (NSView *view in [[window contentView] subviews]) {
        if ([view isKindOfClass:[NSTextField class]]) observed_text = (NSTextField *)view;
        else if ([view isKindOfClass:[NSScrollView class]]) observed_pane = (NSScrollView *)view;
        else if ([[view layer] isKindOfClass:[CAMetalLayer class]]) observed_layer = [view layer];
      }
      // The same slots must belong to each new window, never the previous tree.
      if (observed_text == nil || observed_pane == nil || observed_layer == nil) return 10;
      if ([observed_text window] != window || [observed_pane window] != window) return 11;
      if ([[observed_layer sublayers] count] != 1) return 12;
      id delegate = [NSApp delegate];
      termination_status = -116;
      if ([delegate applicationShouldTerminate:NSApp] != NSTerminateCancel) return 13;
      termination_status = 1;
      if ([delegate applicationShouldTerminate:NSApp] != NSTerminateCancel) return 14;
      termination_status = 0;
      if ([delegate applicationShouldTerminate:NSApp] != NSTerminateNow) return 15;
      if (pcc_gui_metal_window_close(handle)) return 4;
      if ([NSApp delegate] == delegate || [window delegate] == delegate) return 16;
      // A previously retained delegate must no longer reach the retired sink.
      int after_close = callbacks;
      [delegate applicationShouldHandleReopen:NSApp hasVisibleWindows:NO];
      [delegate windowDidResize:[NSNotification notificationWithName:NSWindowDidResizeNotification object:window]];
      if (callbacks != after_close) return 17;
      if (pcc_gui_metal_lifecycle_probe(handle, "/tmp/stale.txt") != 2) return 18;
    }
    if (observed != nil) return 5;
    if (observed_content != nil || observed_text != nil || observed_pane != nil || observed_layer != nil) return 19;
  }
  if (callbacks < 18 || wrong_window != 0) return 6;
  puts("PCC_WINDOW_CLOSE_OWNERSHIP_OK cycles=3 retained_windows=0");
  puts("PCC_WINDOW_REOPEN_CACHE_OK stale_callbacks=0 retained_views=0");
  return 0;
}
