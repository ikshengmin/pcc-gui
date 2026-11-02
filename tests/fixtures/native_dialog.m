// Fixed native interaction fixture. Only this process's own windows are used.
#import <AppKit/AppKit.h>
#include <assert.h>
#include <pthread.h>
#include "../../pcc_gui/native/pcc_gui_metal_render_bridge.m"
static int64_t key_new(void){int64_t key=-9;assert(pcc_gui_message_box_create(1,0,1,0,&key)==0);assert(key>0);assert(pcc_gui_message_box_text(key,0,"PCC dialog ABI probe",20)==0);assert(pcc_gui_message_box_text(key,1,"Owned native message",20)==0);assert(pcc_gui_message_box_text(key,2,"Automatic test; no application action",37)==0);assert(pcc_gui_message_box_text(key,3,"Remember this choice",20)==0);assert(pcc_gui_message_box_button(key,"Continue",8)==0);assert(pcc_gui_message_box_button(key,"Cancel",6)==0);return key;}
static void spin(void){[[NSRunLoop currentRunLoop]runUntilDate:[NSDate dateWithTimeIntervalSinceNow:0.01]];NSEvent *e;while((e=[NSApp nextEventMatchingMask:NSEventMaskAny untilDate:[NSDate distantPast] inMode:NSDefaultRunLoopMode dequeue:YES]))[NSApp sendEvent:e];}
static void wait_ready(int64_t key,int64_t response,int64_t checked){int64_t ready=0,r=-99,c=-99;for(int i=0;i<300&&!ready;i++){spin();assert(pcc_gui_message_box_poll(key,&ready,&r,&c)==0);}assert(ready==1&&r==response&&c==checked);assert(pcc_gui_message_box_poll(key,&ready,&r,&c)==0&&r==response);}
static void *worker(void *unused){int64_t out=91,a=92,b=93;assert(pcc_gui_message_box_create(0,0,0,0,&out)==2&&out==91);assert(pcc_gui_message_box_text(1,0,"x",1)==2);assert(pcc_gui_message_box_button(1,"x",1)==2);assert(pcc_gui_message_box_begin(1,NULL)==2);assert(pcc_gui_message_box_poll(1,&out,&a,&b)==2&&out==91&&a==92&&b==93);assert(pcc_gui_message_box_cancel(1)==2);assert(pcc_gui_message_box_release(1)==2);assert(pcc_gui_message_box_live_count(&out)==2&&out==91);return NULL;}
int main(int argc,const char **argv){@autoreleasepool{
 [NSApplication sharedApplication];[NSApp setActivationPolicy:NSApplicationActivationPolicyAccessory];[NSApp finishLaunching];
 pthread_t thread;assert(pthread_create(&thread,NULL,worker,NULL)==0);pthread_join(thread,NULL);
 int64_t key=key_new(),ready=11,response=12,checked=13;
 const unsigned char bad[]={0xff};assert(pcc_gui_message_box_text(key,1,bad,1)==3);assert([pcc_dialog_get(key).alert.messageText isEqualToString:@"Owned native message"]);
 assert(pcc_gui_message_box_begin(key,(void *)0x1234)==2);assert(pcc_gui_message_box_begin(key,NULL)==0);assert(pcc_gui_message_box_release(key)==5);
 assert(pcc_gui_message_box_poll(key,&ready,&response,&checked)==0&&ready==0&&response==12&&checked==13);
 assert(pcc_gui_message_box_poll(key,&ready,&ready,&checked)==2);
 PccGuiMessageBox *box=pcc_dialog_get(key);box.alert.suppressionButton.state=NSControlStateValueOn;
 for(int i=0;i<5;i++)spin();
 if(argc>1){NSView *view=box.alert.window.contentView;[view display];NSBitmapImageRep *rep=[view bitmapImageRepForCachingDisplayInRect:view.bounds];[view cacheDisplayInRect:view.bounds toBitmapImageRep:rep];assert([[rep representationUsingType:NSBitmapImageFileTypePNG properties:@{}]writeToFile:[NSString stringWithUTF8String:argv[1]] atomically:YES]);}
 [box.alert.buttons[0] performClick:nil];wait_ready(key,0,1);assert(pcc_gui_message_box_cancel(key)==0);assert(pcc_gui_message_box_release(key)==0);assert(pcc_gui_message_box_release(key)==2);
 assert(pcc_gui_message_box_poll(key,&ready,&response,&checked)==2);
 NSWindow *parent=[[NSWindow alloc]initWithContentRect:NSMakeRect(100,100,360,180) styleMask:NSWindowStyleMaskTitled|NSWindowStyleMaskClosable backing:NSBackingStoreBuffered defer:NO];parent.releasedWhenClosed=NO;[parent makeKeyAndOrderFront:nil];
 for(int i=0;i<4;i++){
  int64_t current=key_new();assert(current>key);assert(pcc_gui_message_box_begin(current,(__bridge void *)parent)==0);
  int64_t busy=key_new();assert(pcc_gui_message_box_begin(busy,NULL)==5);assert(pcc_gui_message_box_release(busy)==0);
  if(i==3)[parent close];else if(i%2)[pcc_dialog_get(current).alert.buttons[1] performClick:nil];else assert(pcc_gui_message_box_cancel(current)==0);
  wait_ready(current,1,0);assert(pcc_gui_message_box_release(current)==0);
 }
 int64_t count=-1;assert(pcc_gui_message_box_live_count(&count)==0&&count==0);
 puts("PCC_NATIVE_DIALOG_OK top_level=1 sheets=4 pending=1 stale=1 thread=1 parent_close=1 counts=0");
 }return 0;}
