// Generic host for an original-source translated renderer. No JS/Python engine.
#include "pcc_gui_document.h"
#ifndef PCC_DOCUMENT_DEFAULT_STATUS
#define PCC_DOCUMENT_DEFAULT_STATUS @"Document ready"
#endif
#ifndef PCC_DOCUMENT_DEFAULT_OPENING
#define PCC_DOCUMENT_DEFAULT_OPENING @"Opening document…"
#endif
#import <AppKit/AppKit.h>
#import <CoreText/CoreText.h>
#include <signal.h>
#include <sys/resource.h>
#include <unistd.h>
extern void *pcc_gui_metal_window_create(const char *, int64_t, int64_t);
extern int64_t pcc_gui_metal_window_show(void *);
extern int64_t pcc_gui_metal_run_loop_pump(void);
extern int64_t pcc_gui_metal_window_is_closed(void *);
extern int64_t pcc_gui_metal_window_close(void *);
extern int64_t pcc_gui_metal_window_capture(void *, const char *);
@interface T2PreviewDelegate : NSObject <NSApplicationDelegate>
@property(weak) NSWindow *window;
@end
@implementation T2PreviewDelegate
- (NSApplicationTerminateReply)applicationShouldTerminate:
    (NSApplication *)sender {
  [self.window close];
  return NSTerminateCancel;
}
@end
// Image bytes are immutable bundle resources. Match the renderer's ordered
// digest list to that same catalog before passing the live DOM to AppKit.
static NSData *documentFrame(NSData *wire, NSArray *catalog, NSDictionary **document) {
  NSMutableDictionary *frame = [NSJSONSerialization JSONObjectWithData:wire
                                       options:NSJSONReadingMutableContainers error:nil];
  if (![frame isKindOfClass:NSMutableDictionary.class]) return nil;
  id refs = frame[@"image_refs"];
  if (refs) {
    if (![refs isKindOfClass:NSArray.class] || [refs count] != catalog.count) return nil;
    for (NSUInteger i = 0; i < catalog.count; i++) {
      NSDictionary *asset = catalog[i];
      if (![refs[i] isEqual:@[asset[@"sha256"], asset[@"pixels_sha256"]]]) return nil;
    }
    frame[@"images"] = catalog;
    [frame removeObjectForKey:@"image_refs"];
    wire = [NSJSONSerialization dataWithJSONObject:frame options:0 error:nil];
  }
  *document = frame;
  return wire;
}
int main(int argc, const char **argv) {
  @autoreleasepool {
    NSTimeInterval enteredAt = NSProcessInfo.processInfo.systemUptime;
    [NSApplication sharedApplication];
    [NSApp setActivationPolicy:NSApplicationActivationPolicyRegular];
    [NSApp finishLaunching];
    NSString *resources = NSBundle.mainBundle.resourcePath;
    NSString *renderer =
        [resources stringByAppendingPathComponent:@"translated-renderer"];
    NSString *capture = nil, *receipt = nil, *snapshot = nil;
    NSMutableArray<NSString *> *exercise = [NSMutableArray array];
    NSArray *buttons = NSBundle.mainBundle.infoDictionary[@"TAGDocumentButtons"];
    NSString *passwordID = NSBundle.mainBundle.infoDictionary[@"TAGDocumentPasswordInput"];
    BOOL clicks = [buttons isKindOfClass:NSArray.class] && buttons.count > 0;
    BOOL once = NO;
    int64_t requestedWidth = 600, requestedHeight = 700;
    for (int i = 1; i < argc; i++) {
      if (strcmp(argv[i], "--renderer") == 0 && i + 1 < argc)
        renderer = [NSString stringWithUTF8String:argv[++i]];
      else if (strcmp(argv[i], "--capture") == 0 && i + 1 < argc)
        capture = [NSString stringWithUTF8String:argv[++i]];
      else if (strcmp(argv[i], "--receipt") == 0 && i + 1 < argc)
        receipt = [NSString stringWithUTF8String:argv[++i]];
      else if (strcmp(argv[i], "--snapshot") == 0 && i + 1 < argc)
        snapshot = [NSString stringWithUTF8String:argv[++i]];
      else if (strcmp(argv[i], "--width") == 0 && i + 1 < argc)
        requestedWidth = atoll(argv[++i]);
      else if (strcmp(argv[i], "--height") == 0 && i + 1 < argc)
        requestedHeight = atoll(argv[++i]);
      else if (strcmp(argv[i], "--activate") == 0 && i + 1 < argc)
        [exercise addObject:[NSString stringWithUTF8String:argv[++i]]];
      else if (strcmp(argv[i], "--exercise-password") == 0)
        [exercise addObject:@"@test-password"];
      else if (strcmp(argv[i], "--once") == 0)
        once = YES;
    }
    if ((clicks && snapshot) || (exercise.count && (!clicks || !once))) {
      fprintf(stderr, "Click exercise requires a live interactive one-shot window.\n");
      return 2;
    }
    if (!clicks && !snapshot) {
      NSString *candidate =
          [resources stringByAppendingPathComponent:@"initial-frame.json"];
      if ([[NSFileManager defaultManager] fileExistsAtPath:candidate])
        snapshot = candidate;
    }
    for (NSString *name in
         [[NSFileManager defaultManager] contentsOfDirectoryAtPath:resources
                                                             error:nil])
      if ([@[ @"ttf", @"otf", @"woff2" ] containsObject:name.pathExtension])
        CTFontManagerRegisterFontsForURL(
            (__bridge CFURLRef)[NSURL
                fileURLWithPath:[resources
                                    stringByAppendingPathComponent:name]],
            kCTFontManagerScopeProcess, NULL);
    NSString *loadingTitle =
        NSBundle.mainBundle.infoDictionary[@"CFBundleDisplayName"]
            ?: @"Translated preview";
    void *handle = pcc_gui_metal_window_create(loadingTitle.UTF8String,
                                               requestedWidth, requestedHeight);
    if (!handle)
      return 2;
    NSWindow *window = (__bridge NSWindow *)handle;
    window.styleMask |= NSWindowStyleMaskResizable;
    window.appearance = [NSAppearance appearanceNamed:NSAppearanceNameAqua];
    window.collectionBehavior |= NSWindowCollectionBehaviorFullScreenPrimary;
    T2PreviewDelegate *delegate = [T2PreviewDelegate new];
    delegate.window = window;
    NSApp.delegate = delegate;
    NSMenu *menu = [NSMenu new], *appMenu = [NSMenu new];
    NSMenuItem *app = [NSMenuItem new];
    app.submenu = appMenu;
    [appMenu addItemWithTitle:@"Quit Preview"
                       action:@selector(terminate:)
                keyEquivalent:@"q"];
    [menu addItem:app];
    NSMenuItem *editItem = [NSMenuItem new];
    NSMenu *editMenu = [[NSMenu alloc] initWithTitle:@"Edit"];
    [editMenu addItemWithTitle:@"Paste" action:@selector(paste:) keyEquivalent:@"v"];
    [editMenu addItemWithTitle:@"Select All" action:@selector(selectAll:) keyEquivalent:@"a"];
    editItem.submenu = editMenu;
    [menu addItem:editItem];
    NSApp.mainMenu = menu;
    NSView *placeholder =
        [[NSView alloc] initWithFrame:window.contentView.bounds];
    placeholder.wantsLayer = YES;
    placeholder.layer.backgroundColor = NSColor.windowBackgroundColor.CGColor;
    placeholder.autoresizingMask = NSViewWidthSizable | NSViewHeightSizable;
    [window.contentView addSubview:placeholder];
    NSTextField *loading = [NSTextField labelWithString:@"Opening application…"];
    loading.frame = NSMakeRect(0, NSMidY(placeholder.bounds) - 28, NSWidth(placeholder.bounds), 26);
    loading.autoresizingMask = NSViewWidthSizable | NSViewMinYMargin | NSViewMaxYMargin;
    loading.alignment = NSTextAlignmentCenter;
    loading.font = [NSFont systemFontOfSize:17 weight:NSFontWeightMedium];
    [placeholder addSubview:loading];
    NSProgressIndicator *spinner = [[NSProgressIndicator alloc] initWithFrame:
        NSMakeRect(NSMidX(placeholder.bounds) - 9, NSMidY(placeholder.bounds) + 6, 18, 18)];
    spinner.style = NSProgressIndicatorStyleSpinning;
    spinner.controlSize = NSControlSizeSmall;
    spinner.autoresizingMask = NSViewMinXMargin | NSViewMaxXMargin | NSViewMinYMargin | NSViewMaxYMargin;
    [placeholder addSubview:spinner];
    [spinner startAnimation:nil];
    pcc_gui_metal_window_show(handle);
    NSTimeInterval windowShownAt = receipt ? NSProcessInfo.processInfo.systemUptime : 0;
    NSTask *task = [NSTask new];
    task.executableURL = [NSURL fileURLWithPath:renderer];
    NSMutableDictionary *environment =
        [NSProcessInfo.processInfo.environment mutableCopy];
    environment[@"TAGC_PRESENTATION"] = @"1";
    if (clicks) {
      environment[@"TAGC_DOCUMENT_CLICKS"] = @"1";
    } else {
      [environment removeObjectForKey:@"TAGC_DOCUMENT_CLICKS"];
    }
    NSData *catalogBytes = [NSData dataWithContentsOfFile:[resources stringByAppendingPathComponent:@"image-catalog.json"]];
    NSArray *catalog = catalogBytes ? [NSJSONSerialization JSONObjectWithData:catalogBytes options:0 error:nil] : nil;
    [environment removeObjectForKey:@"TAGC_FRAME_IMAGE_REFS"];
    if ([catalog isKindOfClass:NSArray.class]) environment[@"TAGC_FRAME_IMAGE_REFS"] = @"1";
    task.environment = environment;
    NSPipe *commands = [NSPipe pipe];
    if (clicks) task.standardInput = commands;
    task.arguments = @[];
    NSPipe *output = [NSPipe pipe], *errors = [NSPipe pipe];
    task.standardOutput = output;
    task.standardError = errors;
    NSLock *lock = [NSLock new];
    NSMutableData *buffer = [NSMutableData data],
                  *diagnostic = [NSMutableData data];
    __block BOOL overflow = NO;
    if (snapshot) {
      NSData *cached = [NSData dataWithContentsOfFile:snapshot];
      if (cached) {
        [buffer appendData:[@"T2_BROWSER_FRAME "
                               dataUsingEncoding:NSUTF8StringEncoding]];
        [buffer appendData:cached];
        [buffer appendData:[@"\n" dataUsingEncoding:NSUTF8StringEncoding]];
      }
    }
    output.fileHandleForReading.readabilityHandler = ^(NSFileHandle *file) {
      NSData *data = file.availableData;
      [lock lock];
      if (buffer.length + data.length <= 16 * 1024 * 1024)
        [buffer appendData:data];
      else
        overflow = YES;
      [lock unlock];
      if (!data.length)
        file.readabilityHandler = nil;
    };
    errors.fileHandleForReading.readabilityHandler = ^(NSFileHandle *file) {
      NSData *data = file.availableData;
      [lock lock];
      if (diagnostic.length + data.length <= 1024 * 1024)
        [diagnostic appendData:data];
      [lock unlock];
      if (!data.length)
        file.readabilityHandler = nil;
    };
    NSError *error = nil;
    BOOL launched = [task launchAndReturnError:&error];
    if (!launched) {
      [spinner stopAnimation:nil];
      loading.stringValue = @"The translated renderer could not start.";
      fprintf(stderr, "%s\n", error.description.UTF8String);
    } else
      setpriority(PRIO_PROCESS, task.processIdentifier, 15);
    BOOL presented = NO, captured = NO, awaitingFrame = NO;
    uint32_t generation = 0;
    NSUInteger exercised = 0;
    NSDate *start = [NSDate date];
    NSTimeInterval launchedAt = NSProcessInfo.processInfo.systemUptime;
    NSTimeInterval requestedAt = launchedAt, receivedAt = 0, presentBegin = 0, presentEnd = 0;
    NSData *frame = nil;
    NSDictionary *currentDocument = nil;
    NSString *pendingButtonID = nil;
    BOOL waitingForNavigation = NO;
    NSProgressIndicator *navigationSpinner = [NSProgressIndicator new];
    navigationSpinner.style = NSProgressIndicatorStyleSpinning;
    navigationSpinner.controlSize = NSControlSizeSmall;
    navigationSpinner.autoresizingMask = NSViewMinXMargin | NSViewMinYMargin;
    while (!pcc_gui_metal_window_is_closed(handle)) { @autoreleasepool {
      pcc_gui_metal_run_loop_pump();
      [lock lock];
      BOOL tooBig = overflow;
      NSData *line = nil;
      if (buffer.length && !tooBig) {
        const uint8_t *start = buffer.bytes;
        const uint8_t *end = memchr(start, '\n', buffer.length);
        if (end) {
          NSUInteger count = end - start;
          line = [buffer subdataWithRange:NSMakeRange(0, count)];
          [buffer replaceBytesInRange:NSMakeRange(0, count + 1) withBytes:NULL length:0];
        }
      }
      [lock unlock];
      if (tooBig) { pcc_gui_document_status(handle, "Renderer output exceeded limit."); break; }
      if (line) {
        NSData *prefix = [@"T2_BROWSER_FRAME " dataUsingEncoding:NSUTF8StringEncoding];
        if (line.length >= prefix.length && memcmp(line.bytes, prefix.bytes, prefix.length) == 0) {
            if (receipt) receivedAt = NSProcessInfo.processInfo.systemUptime;
            frame = [line subdataWithRange:NSMakeRange(prefix.length, line.length - prefix.length)];
            NSDictionary *data = nil;
            frame = documentFrame(frame, catalog, &data);
            NSInteger passwordNode = -1;
            if (clicks && passwordID) {
              for (NSDictionary *node in data[@"nodes"])
                if ([node[@"attributes"][@"id"] isEqual:passwordID]) passwordNode = [node[@"index"] integerValue];
            }
            if (receipt) presentBegin = NSProcessInfo.processInfo.systemUptime;
            int rc = frame ? pcc_gui_document_present_with_password(handle, frame.bytes, frame.length, passwordNode) : 3;
            if (receipt) presentEnd = NSProcessInfo.processInfo.systemUptime;
            if (rc == 0) {
              presented = YES;
              captured = NO;
              awaitingFrame = NO;
              generation++;
              waitingForNavigation = NO;
              [navigationSpinner stopAnimation:nil];
              [navigationSpinner removeFromSuperview];
              currentDocument = data;
              [spinner stopAnimation:nil];
              [placeholder removeFromSuperview];
              if (clicks) {
                for (NSDictionary *node in data[@"nodes"]) {
                  if ([buttons containsObject:node[@"attributes"][@"id"] ?: @""])
                    pcc_gui_document_enable_button(handle, [node[@"index"] longLongValue]);
                }
                NSString *status = NSBundle.mainBundle.infoDictionary[@"PCCDocumentStatus"] ?: PCC_DOCUMENT_DEFAULT_STATUS;
                pcc_gui_document_status(handle, status.UTF8String);
              }
              NSString *title = data[@"title"];
              if (title.length)
                window.title =
                    [title stringByAppendingString:@" — translated preview"];
              [window displayIfNeeded];
            } else {
              [spinner stopAnimation:nil];
              loading.stringValue = @"The translated document could not be presented.";
              if (presented) pcc_gui_document_status(handle, "The view could not be updated.");
              if (once) { presented = NO; break; }
            }
        } else if (!presented) {
          NSString *phase = [[NSString alloc] initWithData:line encoding:NSUTF8StringEncoding];
          if ([phase hasPrefix:@"t2p-browser-replay: original main IPC handlers installed"])
            loading.stringValue = @"Starting window…";
          if ([phase isEqual:@"t2p-browser-replay: original preload initialization completed"])
            loading.stringValue = NSBundle.mainBundle.infoDictionary[@"PCCDocumentOpeningLabel"] ?: PCC_DOCUMENT_DEFAULT_OPENING;
        }
      }
      if (presented && !captured) {
        [window displayIfNeeded];
        pcc_gui_metal_run_loop_pump();
        NSTimeInterval displayedAt = receipt ? NSProcessInfo.processInfo.systemUptime : 0;
        NSString *frameReceipt = generation <= 1 ? receipt : [receipt stringByAppendingFormat:@".%u", generation];
        NSString *frameCapture = generation <= 1 ? capture : [[capture stringByDeletingPathExtension] stringByAppendingFormat:@".%u.png", generation];
        if (capture)
          pcc_gui_metal_window_capture(handle,
                                       frameCapture.fileSystemRepresentation);
        if (receipt) {
          [frame writeToFile:[frameReceipt stringByAppendingString:@".frame.json"]
                  atomically:YES];
          NSDictionary *data = [NSJSONSerialization JSONObjectWithData:frame
                                                               options:0
                                                                 error:nil];
          NSMutableArray *rects = [NSMutableArray array];
          for (NSDictionary *node in data[@"nodes"]) {
            NSString *identifier = node[@"attributes"][@"id"];
            if (identifier.length) {
              double r[4];
              if (pcc_gui_document_rect(handle, [node[@"index"] longLongValue],
                                        r) == 0)
                [rects addObject:@{
                  @"id" : identifier,
                  @"x" : @(r[0]),
                  @"y" : @(r[1]),
                  @"width" : @(r[2]),
                  @"height" : @(r[3])
                }];
            }
          }
          NSDictionary *result = @{
            @"translated_document_presented" : @YES,
            @"node_count" : @(pcc_gui_document_node_count(handle)),
            @"width" : @(window.contentView.bounds.size.width),
            @"height" : @(window.contentView.bounds.size.height),
            @"interactive_application" : @NO,
            @"frame_number" : @(generation),
            @"elapsed_seconds" : @(NSProcessInfo.processInfo.systemUptime - launchedAt),
            @"native_timing" : @{
              @"main_to_window_shown_seconds" : @(windowShownAt - enteredAt),
              @"main_to_renderer_launch_seconds" : @(launchedAt - enteredAt),
              @"request_to_frame_received_seconds" : @(receivedAt - requestedAt),
              @"decode_and_bind_seconds" : @(presentBegin - receivedAt),
              @"pcc_gui_document_present_seconds" : @(presentEnd - presentBegin),
              @"present_to_display_pump_seconds" : @(displayedAt - presentEnd),
              @"frame_received_to_display_pump_seconds" : @(displayedAt - receivedAt)
            },
            @"rects" : rects
          };
          [[NSJSONSerialization dataWithJSONObject:result
                                           options:NSJSONWritingPrettyPrinted
                                             error:nil] writeToFile:frameReceipt
                                                         atomically:YES];
        }
        captured = YES;
        if (once && exercised == exercise.count)
          break;
        if (once && clicks && exercised < exercise.count) {
          NSString *identifier = exercise[exercised++];
          NSDictionary *data = [NSJSONSerialization JSONObjectWithData:frame options:0 error:nil];
          BOOL sent = NO;
          if ([identifier isEqual:@"@test-password"] && passwordID) {
            NSView *document = window.contentView.subviews.lastObject;
            for (NSView *child in document.subviews) {
              if (![child isKindOfClass:NSSecureTextField.class]) continue;
              NSSecureTextField *field = (NSSecureTextField *)child;
              NSPoint center = NSMakePoint(NSMidX(field.bounds), NSMidY(field.bounds));
              NSPoint hitPoint = [field convertPoint:center toView:window.contentView];
              if ([window.contentView hitTest:hitPoint] != field) continue;
              NSPoint point = [field convertPoint:center toView:nil];
              for (NSNumber *kind in @[@(NSEventTypeLeftMouseUp), @(NSEventTypeLeftMouseDown)]) {
                NSEvent *event = [NSEvent mouseEventWithType:kind.unsignedIntegerValue location:point
                    modifierFlags:0 timestamp:NSProcessInfo.processInfo.systemUptime windowNumber:window.windowNumber
                    context:nil eventNumber:0 clickCount:1 pressure:1];
                [NSApp postEvent:event atStart:YES];
              }
              pcc_gui_metal_run_loop_pump();
              NSTextView *editor = (NSTextView *)field.currentEditor;
              if (!editor || window.firstResponder != editor) continue;
              [editor insertText:@"fixture-only" replacementRange:NSMakeRange(0, 0)];
              sent = YES;
              break;
            }
          }
          for (NSDictionary *node in data[@"nodes"]) {
            if (![node[@"attributes"][@"id"] isEqual:identifier] || ![buttons containsObject:identifier]) continue;
            double box[4];
            if (pcc_gui_document_rect(handle, [node[@"index"] longLongValue], box) || box[2] <= 0 || box[3] <= 0) continue;
            NSView *view = window.contentView.subviews.lastObject;
            NSPoint point = [view convertPoint:NSMakePoint(box[0]+box[2]/2, box[1]+box[3]/2) toView:nil];
            NSPoint contentPoint = [window.contentView convertPoint:point fromView:nil];
            NSView *hit = [window.contentView hitTest:contentPoint];
            if (hit != view) continue;
            for (NSNumber *kind in @[@(NSEventTypeLeftMouseDown), @(NSEventTypeLeftMouseUp)]) {
              NSEvent *event = [NSEvent mouseEventWithType:kind.unsignedIntegerValue location:point modifierFlags:0 timestamp:NSProcessInfo.processInfo.systemUptime windowNumber:window.windowNumber context:nil eventNumber:0 clickCount:1 pressure:1];
              if (event.type == NSEventTypeLeftMouseDown) [hit mouseDown:event];
              else [hit mouseUp:event];
            }
            sent = YES;
            break;
          }
          if (!sent) { presented = NO; break; }
        }
      }
      if (clicks && presented && task.running) {
        int64_t index = pcc_gui_document_take_click(handle);
        if (index >= 0 && (NSUInteger)index < [currentDocument[@"nodes"] count]) {
          NSString *identifier = currentDocument[@"nodes"][index][@"attributes"][@"id"];
          if (!pendingButtonID && [buttons containsObject:identifier]) pendingButtonID = identifier;
        }
        if (!awaitingFrame) {
          uint8_t input[8192];
          uint32_t length = 0;
          int64_t edited = pcc_gui_document_take_password_edit(handle, input, sizeof(input), &length);
          NSInteger target = edited;
          if (edited < 0 && pendingButtonID) {
            for (NSDictionary *node in currentDocument[@"nodes"]) {
              if (![node[@"attributes"][@"id"] isEqual:pendingButtonID] || node[@"attributes"][@"disabled"]) continue;
              double box[4];
              NSInteger number = [node[@"index"] integerValue];
              if (!pcc_gui_document_rect(handle, number, box) && box[2] > 0 && box[3] > 0) target = number;
            }
            pendingButtonID = nil;
          }
          if (target >= 0) {
            uint32_t tag = (uint32_t)target | (edited >= 0 ? 0x80000000u : 0u);
            uint32_t words[3] = {CFSwapInt32HostToLittle(generation), CFSwapInt32HostToLittle(tag),
                                 CFSwapInt32HostToLittle(length)};
            NSMutableData *record = [NSMutableData dataWithBytes:words length:edited >= 0 ? 12 : 8];
            if (edited >= 0) [record appendBytes:input length:length];
            BOOL sent = [commands.fileHandleForWriting writeData:record error:nil];
            if (edited >= 0) {
              for (uint32_t i = 0; i < length; ++i) ((volatile uint8_t *)input)[i] = 0;
              [record resetBytesInRange:NSMakeRange(12, length)];
            }
            if (!sent) { presented = NO; break; }
            if (receipt) requestedAt = NSProcessInfo.processInfo.systemUptime;
            awaitingFrame = YES;
            waitingForNavigation = edited < 0;
            start = [NSDate date];
          }
        }
      }
      if (awaitingFrame && !task.running && !line) {
        [navigationSpinner stopAnimation:nil];
        [navigationSpinner removeFromSuperview];
        waitingForNavigation = NO;
        awaitingFrame = NO;
        pcc_gui_document_status(handle, "Renderer stopped before the view was updated.");
        if (once) { presented = NO; break; }
      }
      if (waitingForNavigation && -start.timeIntervalSinceNow > .5 && !navigationSpinner.superview) {
        NSView *document = window.contentView.subviews.lastObject;
        navigationSpinner.frame = NSMakeRect(NSWidth(document.bounds)-25, NSHeight(document.bounds)-23, 16, 16);
        [document addSubview:navigationSpinner];
        [navigationSpinner startAnimation:nil];
      }
      if (clicks && once && presented && (!task.running || -start.timeIntervalSinceNow > 200) && exercised > generation-1) {
        presented = NO; break;
      }
      if (!presented && !task.running && -start.timeIntervalSinceNow > 2) {
        [spinner stopAnimation:nil];
        loading.stringValue = @"Renderer stopped before a document was ready. "
                              @"See the diagnostic log.";
        if (once)
          break;
      }
      if (-start.timeIntervalSinceNow > 180 && !presented) {
        [spinner stopAnimation:nil];
        loading.stringValue = @"Renderer timed out.";
        if (once)
          break;
      }
      [NSThread sleepForTimeInterval:.01];
    }}
    if (clicks) [commands.fileHandleForWriting closeFile];
    if (task.running) {
      [task terminate];
      for (int i = 0; i < 50 && task.running; i++)
        [NSThread sleepForTimeInterval:.01];
      if (task.running)
        kill(task.processIdentifier, SIGKILL);
    }
    if (launched) [task waitUntilExit];
    output.fileHandleForReading.readabilityHandler = nil;
    errors.fileHandleForReading.readabilityHandler = nil;
    [output.fileHandleForReading closeFile];
    [errors.fileHandleForReading closeFile];
    if (receipt) {
      [lock lock];
      [diagnostic writeToFile:[receipt stringByAppendingString:@".stderr"]
                   atomically:YES];
      [lock unlock];
    }
    pcc_gui_metal_window_close(handle);
    NSApp.delegate = nil;
    return presented && (!exercise.count || (generation == exercise.count + 1 && !awaitingFrame)) ? 0 : 1;
  }
}
