#include "pcc_gui_document.h"
#import <AppKit/AppKit.h>
#include <assert.h>
extern void *pcc_gui_metal_window_create(const char *, int64_t, int64_t);
extern int64_t pcc_gui_metal_window_close(void *);
extern int64_t pcc_gui_metal_window_is_closed(void *);
static NSDictionary *rule(NSString *name, NSString *value) {
  return @{
    @"name" : name,
    @"value" : value,
    @"important" : @NO,
    @"ids" : @0,
    @"classes" : @0,
    @"types" : @0
  };
}
static NSDictionary *node(int index, int parent, NSString *tag,
                          NSArray *children, NSArray *styles) {
  return @{
    @"index" : @(index),
    @"parent" : @(parent),
    @"tag" : tag,
    @"name" : tag.length ? tag : @"#document",
    @"text" : @"",
    @"attributes" : @{},
    @"children" : children,
    @"styles" : styles
  };
}
int main(void) {
  @autoreleasepool {
    [NSApplication sharedApplication];
    void *window = pcc_gui_metal_window_create("Document fixture", 300, 200);
    assert(window);
    assert(pcc_gui_metal_window_is_closed(window) == 0);
    [(__bridge NSWindow *)window orderOut:nil];
    assert(pcc_gui_metal_window_is_closed(window) == 0);
    NSArray *nodes = @[
      node(0, -1, @"", @[ @1 ], @[]),
      node(1, 0, @"div", @[ @2, @3 ],
           @[
             rule(@"display", @"flex"), rule(@"flex-direction", @"column"),
             rule(@"width", @"100%"), rule(@"height", @"100%"),
             rule(@"padding", @"10px"), rule(@"gap", @"8px")
           ]),
      node(2, 1, @"button", @[], @[ rule(@"height", @"20px") ]),
      node(3, 1, @"div", @[], @[ rule(@"flex", @"1") ])
    ];
    NSDictionary *input = @{
      @"schema" : @"t2-browser-presentation-v1",
      @"width" : @300,
      @"height" : @200,
      @"nodes" : nodes
    };
    NSData *data = [NSJSONSerialization dataWithJSONObject:input
                                                   options:0
                                                     error:nil];
    assert(pcc_gui_document_present(window, data.bytes, data.length) == 0);
    double box[4];
    assert(pcc_gui_document_rect(window, 2, box) == 0);
    assert(box[0] == 10 && box[1] == 10 && box[2] == 280 && box[3] == 20);
    assert(pcc_gui_document_rect(window, 3, box) == 0);
    assert(box[1] == 38 && box[3] == 152);
    assert(pcc_gui_document_present(window, (const uint8_t *)"{}", 2) == 3);
    assert(pcc_gui_document_node_count(window) == 4);
    NSWindow *native = (__bridge NSWindow *)window;
    NSView *view = native.contentView.subviews.lastObject;
    assert(pcc_gui_document_enable_button(window, 1) != 0);
    assert(pcc_gui_document_enable_button(window, 2) == 0);
    NSPoint point = [view convertPoint:NSMakePoint(12, 12) toView:nil];
    NSEvent *(^mouse)(NSEventType,NSPoint) = ^NSEvent *(NSEventType kind, NSPoint location) {
      return [NSEvent mouseEventWithType:kind location:location modifierFlags:0 timestamp:0
                           windowNumber:native.windowNumber context:nil eventNumber:0 clickCount:1 pressure:1];
    };
    [view mouseDown:mouse(NSEventTypeLeftMouseDown,point)];
    [view mouseUp:mouse(NSEventTypeLeftMouseUp,NSMakePoint(-1,-1))];
    assert(pcc_gui_document_take_click(window) == -1);
    [view mouseDown:mouse(NSEventTypeLeftMouseDown,point)];
    [view mouseUp:mouse(NSEventTypeLeftMouseUp,point)];
    assert(pcc_gui_document_take_click(window) == 2);
    assert(pcc_gui_document_take_click(window) == -1);
    [view mouseDown:mouse(NSEventTypeLeftMouseDown,point)];
    [view mouseUp:mouse(NSEventTypeLeftMouseUp,point)];
    assert(pcc_gui_document_present(window, data.bytes, data.length) == 0);
    assert(pcc_gui_document_take_click(window) == -1);
    pcc_gui_metal_window_close(window);
    assert(pcc_gui_metal_window_is_closed(window) == 1);
    assert(pcc_gui_document_node_count(window) == -1);
    puts("document presentation ownership/layout passed");
    return 0;
  }
}
