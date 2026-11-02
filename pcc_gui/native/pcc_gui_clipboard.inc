// Included exactly once by the canonical AppKit bridge; no T2/Python graph
// enters native storage. Clipboard data persists independently of open leases.
#include "pcc_gui_clipboard.h"
#include <limits.h>
static NSMutableDictionary<NSNumber *, NSPasteboard *> *pcc_clipboard_boards;
static NSMutableDictionary<NSNumber *, NSData *> *pcc_clipboard_snapshots;
static int64_t pcc_clipboard_next_key = 1;
static const int64_t pcc_clipboard_max_bytes = 64 * 1024 * 1024;

static BOOL pcc_clipboard_init(void) {
  if (!pcc_clipboard_boards) pcc_clipboard_boards = [NSMutableDictionary new];
  if (!pcc_clipboard_snapshots) pcc_clipboard_snapshots = [NSMutableDictionary new];
  return pcc_clipboard_boards != nil && pcc_clipboard_snapshots != nil;
}
static NSPasteboard *pcc_clipboard_board(int64_t key) {
  return key > 0 ? pcc_clipboard_boards[@(key)] : nil;
}
static int64_t pcc_clipboard_publish(NSPasteboard *board, int64_t *out) {
  if (!board || !pcc_clipboard_init()) return 4;
  if (pcc_clipboard_next_key == INT64_MAX) return 6;
  int64_t key = pcc_clipboard_next_key++;
  pcc_clipboard_boards[@(key)] = board;
  *out = key;
  return 0;
}
int64_t pcc_gui_clipboard_open_general(int64_t *out) {
  if (![NSThread isMainThread] || !out) return 2;
  @autoreleasepool { return pcc_clipboard_publish([NSPasteboard generalPasteboard], out); }
}
int64_t pcc_gui_clipboard_open_named(const void *bytes, int64_t length, int64_t *out) {
  if (![NSThread isMainThread] || !out || !bytes || length <= 0) return 2;
  if (length > 4096) return 6;
  @autoreleasepool {
    NSString *name = [[NSString alloc] initWithBytes:bytes length:(NSUInteger)length encoding:NSUTF8StringEncoding];
    if (!name) return 3;
    if ([name isEqualToString:NSPasteboardNameGeneral] || [name isEqualToString:NSPasteboardNameFind] ||
        [name isEqualToString:NSPasteboardNameDrag] || [name isEqualToString:NSPasteboardNameFont] ||
        [name isEqualToString:NSPasteboardNameRuler]) return 2;
    return pcc_clipboard_publish([NSPasteboard pasteboardWithName:name], out);
  }
}
int64_t pcc_gui_clipboard_close(int64_t key) {
  if (![NSThread isMainThread] || !pcc_clipboard_board(key)) return 2;
  [pcc_clipboard_boards removeObjectForKey:@(key)];
  return 0;
}
int64_t pcc_gui_clipboard_write_utf8(int64_t key, const void *bytes, int64_t length) {
  if (![NSThread isMainThread] || length < 0 || (length && !bytes)) return 2;
  NSPasteboard *board = pcc_clipboard_board(key);
  if (!board) return 2;
  if (length > pcc_clipboard_max_bytes) return 6;
  @autoreleasepool {
    NSString *text = [[NSString alloc] initWithBytes:bytes length:(NSUInteger)length encoding:NSUTF8StringEncoding];
    if (!text) return 3;
    NSPasteboardItem *item = [NSPasteboardItem new];
    if (![item setString:text forType:NSPasteboardTypeString]) return 4;
    [board clearContents];
    return [board writeObjects:@[item]] ? 0 : 4;
  }
}
int64_t pcc_gui_clipboard_clear(int64_t key) {
  if (![NSThread isMainThread]) return 2;
  NSPasteboard *board = pcc_clipboard_board(key);
  if (!board) return 2;
  [board clearContents];
  return 0;
}
int64_t pcc_gui_clipboard_snapshot(int64_t key, int64_t *out, int64_t *length_out) {
  if (![NSThread isMainThread] || !out || !length_out || out == length_out) return 2;
  NSPasteboard *board = pcc_clipboard_board(key);
  if (!board) return 2;
  @autoreleasepool {
    NSString *text = [board stringForType:NSPasteboardTypeString];
    NSData *data = text ? [text dataUsingEncoding:NSUTF8StringEncoding allowLossyConversion:NO] : [NSData data];
    if (!data) return 3;
    if (data.length > (NSUInteger)pcc_clipboard_max_bytes || pcc_clipboard_next_key == INT64_MAX) return 6;
    int64_t id = pcc_clipboard_next_key++;
    pcc_clipboard_snapshots[@(id)] = data;
    *out = id; *length_out = (int64_t)data.length;
    return 0;
  }
}
int64_t pcc_gui_clipboard_snapshot_copy(int64_t key, void *out, int64_t capacity) {
  if (![NSThread isMainThread] || key <= 0 || capacity < 0) return 2;
  NSData *data = pcc_clipboard_snapshots[@(key)];
  if (!data || (data.length && !out)) return 2;
  if ((uint64_t)capacity < data.length) return 5;
  if (data.length) memcpy(out, data.bytes, data.length);
  return 0;
}
int64_t pcc_gui_clipboard_snapshot_release(int64_t key) {
  if (![NSThread isMainThread] || key <= 0 || !pcc_clipboard_snapshots[@(key)]) return 2;
  [pcc_clipboard_snapshots removeObjectForKey:@(key)];
  return 0;
}
int64_t pcc_gui_clipboard_live_counts(int64_t *boards, int64_t *snapshots) {
  if (![NSThread isMainThread] || !boards || !snapshots || boards == snapshots) return 2;
  *boards = (int64_t)pcc_clipboard_boards.count; *snapshots = (int64_t)pcc_clipboard_snapshots.count;
  return 0;
}
