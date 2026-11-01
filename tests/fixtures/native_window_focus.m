#import <AppKit/AppKit.h>
#include <stdint.h>
#include <stdio.h>
#include <pthread.h>

void *pcc_gui_metal_window_create(const char *, int64_t, int64_t);
int64_t pcc_gui_metal_window_show(void *);
int64_t pcc_gui_metal_window_close(void *);
int64_t pcc_gui_metal_run_loop_pump(void);
int64_t pcc_gui_metal_window_focus_state(void *, int32_t *, int32_t *);

typedef struct { void *window; int64_t status; int32_t key; int32_t active; } Worker;
static void *off_main(void *raw) {
  Worker *worker = raw;
  worker->status = pcc_gui_metal_window_focus_state(worker->window,
                                                  &worker->key, &worker->active);
  return NULL;
}
static int snapshot(void *handle, int expected_key, int require_active) {
  int32_t words[] = {0x12345678, -7, -9, 0x10203040};
  if (pcc_gui_metal_window_focus_state(handle, &words[1], &words[2])) return 0;
  NSWindow *window = (__bridge NSWindow *)handle;
  return words[0] == 0x12345678 && words[3] == 0x10203040 &&
         words[1] == expected_key && words[1] == (int32_t)[window isKeyWindow] &&
         words[2] == (int32_t)[NSApp isActive] && (!require_active || words[2] == 1);
}
static int activate(void *handle) {
  if (pcc_gui_metal_window_show(handle)) return 0;
  for (int i = 0; i < 100; i++) {
    pcc_gui_metal_run_loop_pump();
    if (snapshot(handle, 1, 1)) return 1;
  }
  return 0;
}
int main(void) {
  @autoreleasepool { [NSApplication sharedApplication]; [NSApp finishLaunching]; }
  int32_t key = -7, active = -9;
  if (pcc_gui_metal_window_focus_state(NULL, &key, &active) != 2 || key != -7 || active != -9) return 1;
  for (int cycle = 0; cycle < 3; cycle++) {
    __weak NSWindow *first_observed;
    __weak NSWindow *second_observed;
    @autoreleasepool {
      void *first = pcc_gui_metal_window_create("PCC focus A", 240, 120);
      void *second = pcc_gui_metal_window_create("PCC focus B", 240, 120);
      if (!first || !second) return 2;
      first_observed = (__bridge NSWindow *)first;
      second_observed = (__bridge NSWindow *)second;
      if (!snapshot(first, 0, 0) || !snapshot(second, 0, 0)) return 3;
      if (pcc_gui_metal_window_focus_state(first, NULL, &active) != 2 || active != -9) return 4;
      if (pcc_gui_metal_window_focus_state(first, &key, NULL) != 2 || key != -7) return 5;
      Worker worker = {first, 0, -7, -9}; pthread_t thread;
      if (pthread_create(&thread, NULL, off_main, &worker)) return 6;
      if (pthread_join(thread, NULL) || worker.status != 2 || worker.key != -7 || worker.active != -9) return 7;
      if (!activate(first) || !snapshot(second, 0, 1)) return 8;
      if (!activate(second) || !snapshot(first, 0, 1)) return 9;
      [(__bridge NSWindow *)second orderOut:nil];
      pcc_gui_metal_run_loop_pump();
      if (!snapshot(second, 0, 0)) return 10;
      if (pcc_gui_metal_window_close(second)) return 11;
      if (!activate(first) || pcc_gui_metal_window_close(first)) return 12;
    }
    // AppKit can retain shown windows until native close events are serviced.
    // Keep both observations weak and bound the drain without reusing handles.
    for (int attempt = 0; attempt < 100; attempt++) {
      @autoreleasepool { pcc_gui_metal_run_loop_pump(); }
      if (first_observed == nil && second_observed == nil) break;
    }
    if (first_observed != nil || second_observed != nil) return 13;
  }
  puts("PCC_NATIVE_WINDOW_FOCUS_OK cycles=3 windows=6 rejected_worker=1 outputs_preserved=1");
  return 0;
}
