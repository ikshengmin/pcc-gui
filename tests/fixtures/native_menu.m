// Inspect and interact only with menus/windows owned by this test process.
#include "../../pcc_gui/native/pcc_gui_metal_render_bridge.m"
#include <pthread.h>
#include <dlfcn.h>
#include <unistd.h>
static void verify(BOOL value,const char *expression,int line){if(!value){fprintf(stderr,"menu assertion %d: %s\n",line,expression);exit(90);}}
#define CHECK(value) verify((value),#value,__LINE__)
static int64_t create_menu(void){int64_t key=0;CHECK(pcc_gui_menu_create(&key)==0&&key>0);return key;}
static int64_t add_item(int64_t menu,int64_t index,int64_t kind,int64_t command,const char *label){int64_t key=0;CHECK(pcc_gui_menu_insert(menu,index,kind,command,label,(int64_t)strlen(label),&key)==0);return key;}
static int drain(int64_t menu,int64_t *selected){int count=0;for(;;){int64_t ready=-1,sequence=-2,kind=-3,item=-4,command=-5;CHECK(pcc_gui_menu_event_peek(menu,&ready,&sequence,&kind,&item,&command)==0);if(!ready){CHECK(sequence==-2&&kind==-3&&item==-4&&command==-5);return count;}int64_t again=0;CHECK(pcc_gui_menu_event_peek(menu,&again,&sequence,&kind,&item,&command)==0&&again==1);if(kind==2)*selected=command;CHECK(pcc_gui_menu_event_ack(menu,sequence+10000)==2);CHECK(pcc_gui_menu_event_ack(menu,sequence)==0);CHECK(pcc_gui_menu_event_ack(menu,sequence)==2);count++;}}
static void *wrong_thread(void *raw){int64_t output=71;CHECK(pcc_gui_menu_count(*(int64_t *)raw,&output)==2&&output==71);return NULL;}
static NSPoint captured_point;
static int cancel_calls;
@interface PccMenuCoordinateProbe : NSMenu
@end
@implementation PccMenuCoordinateProbe
- (BOOL)popUpMenuPositioningItem:(NSMenuItem *)item atLocation:(NSPoint)point inView:(NSView *)view {captured_point=point;return NO;}
- (void)cancelTracking {cancel_calls++;}
@end
@interface PccMenuFlippedView : NSView
@end
@implementation PccMenuFlippedView
- (BOOL)isFlipped{return YES;}
@end
static BOOL capture_owned_menu(const char *path){
 typedef CGImageRef(*Capture)(CGRect,CGWindowListOption,CGWindowID,CGWindowImageOption);
 Capture capture=(Capture)dlsym(RTLD_DEFAULT,"CGWindowListCreateImage");if(!capture)return NO;
 CFArrayRef list=CGWindowListCopyWindowInfo(kCGWindowListOptionOnScreenOnly,kCGNullWindowID);if(!list)return NO;
 BOOL saved=NO;NSMutableArray *owned=[NSMutableArray new];int candidate=0;
 for(NSDictionary *row in (__bridge NSArray *)list){
  if([row[(__bridge NSString *)kCGWindowOwnerPID] intValue]!=getpid()||[row[(__bridge NSString *)kCGWindowLayer] intValue]<=0)continue;
  [owned addObject:row];
  CGWindowID key=[row[(__bridge NSString *)kCGWindowNumber] unsignedIntValue];CGImageRef image=capture(CGRectNull,kCGWindowListOptionIncludingWindow,key,kCGWindowImageBoundsIgnoreFraming);
  if(!image)continue;
  size_t width=CGImageGetWidth(image),height=CGImageGetHeight(image);
  if(width>80&&height>40&&width<=4096&&height<=4096){
   NSBitmapImageRep *bitmap=[[NSBitmapImageRep alloc]initWithCGImage:image];NSData *png=[bitmap representationUsingType:NSBitmapImageFileTypePNG properties:@{}];NSString *output=[NSString stringWithUTF8String:path];
   [png writeToFile:[output stringByAppendingFormat:@".candidate-%d.png",candidate++] atomically:YES];
   // A menu's shadow window is a separate compositor surface. Require actual
   // content beyond one opaque/alpha channel before choosing a visual receipt.
   BOOL content=NO;if(CGImageGetBitsPerPixel(image)==32){CFDataRef pixels=CGDataProviderCopyData(CGImageGetDataProvider(image));size_t stride=CGImageGetBytesPerRow(image),bright=0;if(pixels&&(size_t)CFDataGetLength(pixels)>=stride*height){const UInt8 *bytes=CFDataGetBytePtr(pixels);for(size_t y=0;y<height;y++)for(size_t x=0;x<width*4;x++)if(bytes[y*stride+x]>128)bright++;content=bright>width*height+128;}if(pixels)CFRelease(pixels);}
   if(content&&!saved)saved=[png writeToFile:output atomically:YES];
  }
  CGImageRelease(image);
 }
 NSData *metadata=[NSJSONSerialization dataWithJSONObject:owned options:NSJSONWritingPrettyPrinted error:NULL];[metadata writeToFile:[[NSString stringWithUTF8String:path]stringByAppendingString:@".windows.json"] atomically:YES];
 CFRelease(list);return saved;
}
int main(int argc,char **argv){@autoreleasepool{
 CHECK(argc==2);[NSApplication sharedApplication];
 void *handle=pcc_gui_metal_window_create("PCC owned native menu",640,480);CHECK(handle!=NULL);NSWindow *window=(__bridge NSWindow *)handle;CHECK(pcc_gui_metal_window_show(handle)==0);
 int64_t root=create_menu(),child=create_menu(),other=create_menu(),first=add_item(root,0,0,41,"Open project"),checked=add_item(root,1,0,42,"Remember choice"),separator=add_item(root,2,1,0,""),sub=add_item(root,3,2,0,"More actions");
 int64_t leaf=add_item(child,0,0,43,"Nested action");CHECK(pcc_gui_menu_item_state(checked,7,8,"r",1)==0);CHECK(pcc_gui_menu_item_text(first,1,"Open an owned project",21)==0);
 CHECK(pcc_gui_menu_item_submenu(sub,child)==0);CHECK(pcc_gui_menu_release(child)==5);
 int64_t loop=add_item(child,1,2,0,"Cycle");CHECK(pcc_gui_menu_item_submenu(loop,root)==2);CHECK(pcc_gui_menu_remove(child,1)==0);CHECK(pcc_gui_menu_item_text(loop,0,"x",1)==2);
 int64_t spare=add_item(other,0,2,0,"Already owned");CHECK(pcc_gui_menu_item_submenu(spare,child)==5);
 int64_t count=-1;CHECK(pcc_gui_menu_count(root,&count)==0&&count==4);CHECK(pcc_gui_menu_count(root,NULL)==2);
 int64_t out=77;const unsigned char invalid[]={0xff};CHECK(pcc_gui_menu_insert(root,9,0,1,"x",1,&out)==2&&out==77);CHECK(pcc_gui_menu_item_text(first,0,invalid,1)==3);CHECK(pcc_gui_menu_item_text(first,0,NULL,0)==0);CHECK(pcc_gui_menu_item_text(first,0,"Open project",12)==0);
 CHECK(pcc_gui_menu_item_state(first,8,0,NULL,0)==2);CHECK(pcc_gui_menu_event_peek(root,&out,&out,&count,&leaf,&separator)==2);
 pthread_t thread;CHECK(pthread_create(&thread,NULL,wrong_thread,&root)==0);CHECK(pthread_join(thread,NULL)==0);
 NSMenu *previous=NSApp.mainMenu;CHECK(pcc_gui_menu_set_application(root)==0);CHECK(NSApp.mainMenu==pcc_menu_get(root).native);CHECK(pcc_gui_menu_release(root)==5);
 void *second=pcc_gui_metal_window_create("PCC second owner",400,300);CHECK(second!=NULL&&NSApp.mainMenu==pcc_menu_get(root).native);CHECK(pcc_gui_metal_window_close(second)==0);
 CHECK(pcc_gui_menu_set_application(0)==0&&NSApp.mainMenu==previous);
 CHECK(pcc_gui_menu_set_application(root)==0);NSMenu *foreign=[[NSMenu alloc]initWithTitle:@"Foreign owner"];NSApp.mainMenu=foreign;CHECK(pcc_gui_menu_set_application(other)==5);CHECK(pcc_gui_menu_set_application(0)==0&&NSApp.mainMenu==foreign);NSApp.mainMenu=previous;
 PccGuiMenu *probe=pcc_menu_get(other);NSMenu *native=probe.native;probe.native=[PccMenuCoordinateProbe new];NSView *original=window.contentView;
 [original setBounds:NSMakeRect(17,23,100,150)];CHECK(pcc_gui_menu_popup(other,handle,7,11,-1)==0);CHECK(captured_point.x==24&&captured_point.y==162);
 PccMenuFlippedView *flipped=[[PccMenuFlippedView alloc]initWithFrame:NSMakeRect(0,0,100,150)];window.contentView=flipped;[flipped setBounds:NSMakeRect(17,23,100,150)];CHECK(pcc_gui_menu_popup(other,handle,7,11,-1)==0);CHECK(captured_point.x==24&&captured_point.y==34);
 CHECK(pcc_gui_menu_cancel(other)==0&&cancel_calls==0);window.contentView=original;[original setBounds:NSMakeRect(0,0,640,480)];probe.native=native;
 CHECK(pcc_gui_menu_popup(root,(void *)1,0,0,-1)==2);
 __block BOOL selected=NO,screenshot=NO,busy=NO;
 NSTimer *choose=[NSTimer timerWithTimeInterval:0.20 repeats:NO block:^(NSTimer *timer){
  busy=pcc_gui_menu_cancel(other)==5&&pcc_gui_menu_release(root)==5&&pcc_gui_menu_item_state(first,3,0,NULL,0)==5;
  screenshot=capture_owned_menu(argv[1]);[pcc_menu_get(root).native performActionForItemAtIndex:0];selected=YES;CHECK(pcc_gui_menu_cancel(root)==0);
 }];
 [[NSRunLoop mainRunLoop]addTimer:choose forMode:NSEventTrackingRunLoopMode];[[NSRunLoop mainRunLoop]addTimer:choose forMode:NSRunLoopCommonModes];
 CHECK(pcc_gui_menu_popup(root,handle,40,60,-1)==0);CHECK(selected&&busy&&screenshot);[choose invalidate];
 CHECK(pcc_gui_menu_remove(root,0)==5);int64_t command=0;int events=drain(root,&command);CHECK(events>=3&&command==41);
 // AppKit can start tracking an installed menu without entering our popup API.
 __block BOOL native_owned=NO;NSTimer *native_cancel=[NSTimer timerWithTimeInterval:0.10 repeats:NO block:^(NSTimer *timer){native_owned=pcc_menu_tracking==0&&pcc_gui_menu_cancel(other)==5&&pcc_menu_open_count>0;CHECK(pcc_gui_menu_cancel(root)==0);}];
 [[NSRunLoop mainRunLoop]addTimer:native_cancel forMode:NSEventTrackingRunLoopMode];[[NSRunLoop mainRunLoop]addTimer:native_cancel forMode:NSRunLoopCommonModes];
 [pcc_menu_get(root).native popUpMenuPositioningItem:nil atLocation:NSMakePoint(40,420) inView:window.contentView];[native_cancel invalidate];CHECK(native_owned);CHECK(drain(root,&command)>=2);
 // A parent's close notification cancels only this owned tracking operation.
 __block BOOL parent_closed=NO;NSTimer *closing=[NSTimer timerWithTimeInterval:0.10 repeats:NO block:^(NSTimer *timer){[window close];parent_closed=YES;}];
 [[NSRunLoop mainRunLoop]addTimer:closing forMode:NSEventTrackingRunLoopMode];[[NSRunLoop mainRunLoop]addTimer:closing forMode:NSRunLoopCommonModes];
 CHECK(pcc_gui_menu_popup(root,handle,40,60,-1)==0&&parent_closed);[closing invalidate];command=0;CHECK(drain(root,&command)>=2&&command==0);
 CHECK(pcc_gui_menu_remove(root,0)==0);CHECK(pcc_gui_menu_item_text(first,0,"retired",7)==2);CHECK(pcc_gui_menu_release(root)==0);CHECK(pcc_gui_menu_count(root,&count)==2);CHECK(pcc_menu_get(child).parent==nil);CHECK(pcc_gui_menu_release(child)==0);CHECK(pcc_gui_menu_release(other)==0);
 int64_t overflow=create_menu();add_item(overflow,0,0,71,"Overflow");for(int i=0;i<257;i++)[pcc_menu_get(overflow).native performActionForItemAtIndex:0];
 int64_t ready=11,sequence=12,kind=13,item=14,token=15;CHECK(pcc_gui_menu_event_peek(overflow,&ready,&sequence,&kind,&item,&token)==6);CHECK(ready==11&&sequence==12&&kind==13&&item==14&&token==15);CHECK(pcc_gui_menu_release(overflow)==0);
 int64_t menus=-1,items=-1;CHECK(pcc_gui_menu_live_count(&menus,&items)==0&&menus==0&&items==0);CHECK(pcc_menu_open_count==0&&pcc_menu_tracking==0);CHECK(pcc_gui_metal_window_close(handle)==0);
 printf("PCC_NATIVE_MENU_OK popup=2 parent_close=1 window_menu=1 origin=2 overflow=1 stale=1 thread=1 counts=0\n");return 0;
}}
