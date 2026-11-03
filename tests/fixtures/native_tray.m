// Interact only with status items, menus, images and windows owned by this test.
#import <AppKit/AppKit.h>
#include <objc/runtime.h>
static int cg_created,cg_released;
static CGImageRef owned_cg_create(size_t w,size_t h,size_t bits,size_t pixel,size_t row,CGColorSpaceRef color,CGBitmapInfo info,CGDataProviderRef provider,const CGFloat *decode,bool interpolate,CGColorRenderingIntent intent){CGImageRef image=CGImageCreate(w,h,bits,pixel,row,color,info,provider,decode,interpolate,intent);if(image)cg_created++;return image;}
static void owned_cg_release(CGImageRef image){if(image)cg_released++;CGImageRelease(image);}
#define CGImageCreate owned_cg_create
#define CGImageRelease owned_cg_release
#include "../../pcc_gui/native/pcc_gui_metal_render_bridge.m"
#undef CGImageCreate
#undef CGImageRelease
static id reject_image_init(id self,SEL selector,CGImageRef image,NSSize size){@throw [NSException exceptionWithName:@"OwnedImageInitFailure" reason:@"fixture" userInfo:nil];}
#include <pthread.h>
static void verify(BOOL ok,const char *expression,int line){if(!ok){fprintf(stderr,"tray assertion %d: %s\n",line,expression);exit(90);}}
#define CHECK(x) verify((x),#x,__LINE__)
static void schedule(NSTimer *timer){[[NSRunLoop currentRunLoop]addTimer:timer forMode:NSEventTrackingRunLoopMode];[[NSRunLoop currentRunLoop]addTimer:timer forMode:NSDefaultRunLoopMode];}
static int drain_menu(int64_t key){int count=0;for(;;){int64_t ready=0,seq=0,kind=0,item=0,command=0;CHECK(pcc_gui_menu_event_peek(key,&ready,&seq,&kind,&item,&command)==0);if(!ready)return count;CHECK(pcc_gui_menu_event_ack(key,seq)==0);count++;}}
static void *wrong_thread(void *raw){int64_t value=71;CHECK(pcc_gui_tray_live_count(&value)==2&&value==71);CHECK(pcc_gui_tray_release(*(int64_t *)raw)==2);CHECK(pcc_gui_native_image_empty(&value)==2&&value==71);return NULL;}
@interface PccTrayPicture : NSView
@property(nonatomic,strong) NSImage *image;
@end
@implementation PccTrayPicture
- (void)drawRect:(NSRect)dirty{[[NSColor colorWithCalibratedWhite:0.95 alpha:1]setFill];NSRectFill(self.bounds);[self.image drawInRect:NSMakeRect(170,100,280,250) fromRect:NSZeroRect operation:NSCompositingOperationSourceOver fraction:1];[@"Owned NativeImage / Tray" drawAtPoint:NSMakePoint(32,394) withAttributes:@{NSFontAttributeName:[NSFont systemFontOfSize:25],NSForegroundColorAttributeName:NSColor.blackColor}];}
@end
int main(int argc,char **argv){@autoreleasepool{
 CHECK(argc==3);[NSApplication sharedApplication];int64_t out=71,width=0,height=0,scale=0,is_template=0,empty=0;
 CHECK(pcc_gui_native_image_empty(&empty)==0);CHECK(pcc_gui_native_image_template(empty,1)==0);CHECK(pcc_gui_native_image_info(empty,&width,&height,&scale,&is_template)==0&&width==0&&height==0&&scale==1&&is_template==0);
 unsigned char bytes[80];memset(bytes,0,sizeof bytes);for(int y=0;y<4;y++)for(int x=0;x<4;x++){unsigned char *p=bytes+y*20+x*4;p[0]=x<2?220:30;p[1]=x<2?35:175;p[2]=y<2?55:220;p[3]=y<2?255:140;}
 Method initializer=class_getInstanceMethod(NSImage.class,@selector(initWithCGImage:size:));IMP original=method_setImplementation(initializer,(IMP)reject_image_init);int created_before=cg_created,released_before=cg_released;@try{CHECK(pcc_gui_native_image_rgba(bytes,80,4,4,20,1,&out)==4&&out==71);}@finally{method_setImplementation(initializer,original);}CHECK(cg_created==created_before+1&&cg_released==released_before+1);
 int64_t image=0;CHECK(pcc_gui_native_image_rgba(bytes,80,4,4,20,1,&image)==0);CHECK(pcc_gui_native_image_info(image,&width,&height,&scale,&is_template)==0&&width==4&&height==4&&scale==1);memset(bytes,0,sizeof bytes);CHECK(((const unsigned char *)pcc_native_image_get(image).backing.bytes)[0]==220);
 CHECK(pcc_gui_native_image_rgba(bytes,80,4097,1,20,1,&out)==6&&out==71);CHECK(pcc_gui_native_image_rgba(bytes,80,4,4,0,1,&out)==2&&out==71);CHECK(pcc_gui_native_image_info(image,&out,&out,&out,&out)==2&&out==71);
 CHECK(pcc_gui_native_image_template(image,1)==0);CHECK(pcc_gui_native_image_info(image,&width,&height,&scale,&is_template)==0&&is_template==1);CHECK(pcc_gui_native_image_template(image,0)==0);
 int64_t loaded=0;NSString *copyPath=[[NSString stringWithUTF8String:argv[1]]stringByAppendingString:@".input.png"];CHECK([[NSFileManager defaultManager]copyItemAtPath:[NSString stringWithUTF8String:argv[2]] toPath:copyPath error:nil]);NSData *path=[copyPath dataUsingEncoding:NSUTF8StringEncoding];CHECK(pcc_gui_native_image_path(path.bytes,(int64_t)path.length,&loaded)==0);CHECK(pcc_gui_native_image_info(loaded,&width,&height,&scale,&is_template)==0&&width==3&&height==2);CHECK([[@"changed" dataUsingEncoding:NSUTF8StringEncoding]writeToFile:copyPath atomically:YES]);CHECK(pcc_native_image_get(loaded).backing.length>7);CHECK(pcc_gui_native_image_release(loaded)==0);
 const unsigned char invalid[1]={255};CHECK(pcc_gui_native_image_path(invalid,1,&out)==3&&out==71);CHECK(pcc_gui_native_image_path("",0,&loaded)==0);CHECK(pcc_gui_native_image_release(loaded)==0);
 void *handle=pcc_gui_metal_window_create("PCC owned image and tray",640,480);CHECK(handle!=NULL);CHECK(pcc_gui_metal_window_show(handle)==0);NSWindow *window=(__bridge NSWindow *)handle;PccTrayPicture *picture=[[PccTrayPicture alloc]initWithFrame:NSMakeRect(0,0,640,480)];picture.image=pcc_native_image_get(image).native;window.contentView=picture;
 int64_t tray=0,other=0;CHECK(pcc_gui_tray_create(image,&tray)==0);CHECK(pcc_gui_tray_create(0,&other)==0);PccGuiTray *owned=pcc_tray_get(tray);CHECK(owned.native.button.image==picture.image);CHECK(pcc_gui_native_image_release(image)==0);CHECK(pcc_gui_native_image_release(image)==2);CHECK(owned.native.button.image!=nil);
 CHECK(pcc_gui_tray_tooltip(tray,"Owned native fixture",20)==0);CHECK([owned.native.button.toolTip isEqualToString:@"Owned native fixture"]);
 int64_t menu=0,item=0;CHECK(pcc_gui_menu_create(&menu)==0);CHECK(pcc_gui_menu_insert(menu,0,0,71,"Owned selection",15,&item)==0);CHECK(pcc_gui_tray_menu(tray,menu)==0);CHECK(pcc_gui_tray_menu(other,menu)==5);CHECK(pcc_gui_menu_release(menu)==5);CHECK(pcc_gui_menu_set_application(menu)==5);CHECK(owned.native.menu==nil&&owned.native.button.target==owned);
 int64_t parent=0,submenuItem=0;CHECK(pcc_gui_menu_create(&parent)==0);CHECK(pcc_gui_menu_insert(parent,0,2,0,"Parent",6,&submenuItem)==0);CHECK(pcc_gui_menu_item_submenu(submenuItem,menu)==5);CHECK(pcc_gui_menu_release(parent)==0);
 [owned.native.button performClick:nil];int64_t ready=0,sequence=0,kind=0,flags=0;CHECK(pcc_gui_tray_event_peek(tray,&ready,&sequence,&kind,&flags)==0&&ready==1&&kind==1);int64_t again=sequence;CHECK(pcc_gui_tray_event_peek(tray,&ready,&sequence,&kind,&flags)==0&&sequence==again);CHECK(pcc_gui_tray_event_ack(tray,sequence+5)==2);CHECK(pcc_gui_tray_event_ack(tray,sequence)==0);CHECK(pcc_gui_tray_event_ack(tray,sequence)==2);
 [window display];[picture display];NSBitmapImageRep *capture=[picture bitmapImageRepForCachingDisplayInRect:picture.bounds];CHECK(capture!=nil);[picture cacheDisplayInRect:picture.bounds toBitmapImageRep:capture];NSData *png=[capture representationUsingType:NSBitmapImageFileTypePNG properties:@{}];CHECK(png.length>1000&&[png writeToFile:[NSString stringWithUTF8String:argv[1]] atomically:YES]);
 __block BOOL chosen=NO;NSTimer *choose=[NSTimer timerWithTimeInterval:0.15 repeats:NO block:^(NSTimer *timer){CHECK(pcc_gui_tray_menu(other,menu)==5);CHECK(pcc_gui_menu_release(menu)==5);[pcc_menu_get(menu).native performActionForItemAtIndex:0];chosen=YES;CHECK(pcc_gui_menu_cancel(menu)==0);}];schedule(choose);CHECK(pcc_gui_tray_popup(tray)==0&&chosen);[choose invalidate];CHECK(drain_menu(menu)>=3);
 pthread_t thread;CHECK(pthread_create(&thread,NULL,wrong_thread,&tray)==0);CHECK(pthread_join(thread,NULL)==0);
 __block BOOL retired=NO;NSTimer *retire=[NSTimer timerWithTimeInterval:0.15 repeats:NO block:^(NSTimer *timer){CHECK(pcc_gui_tray_release(tray)==0);CHECK(pcc_gui_tray_release(tray)==2);retired=YES;}];schedule(retire);CHECK(pcc_gui_tray_popup(tray)==0&&retired);[retire invalidate];CHECK(owned.native==nil&&owned.retiring);CHECK(pcc_menu_get(menu).externalOwner==nil);CHECK(drain_menu(menu)>=2);CHECK(pcc_gui_menu_release(menu)==0);
 [window close];CHECK(pcc_gui_tray_tooltip(other,"survives window close",21)==0);PccGuiTray *remaining=pcc_tray_get(other);for(int i=0;i<257;i++)pcc_tray_publish(remaining,1,0);out=71;CHECK(pcc_gui_tray_event_peek(other,&out,&sequence,&kind,&flags)==6&&out==71);CHECK(pcc_gui_tray_release(other)==0);pcc_tray_publish(remaining,1,0);CHECK(remaining.events.count==0);
 CHECK(pcc_gui_native_image_release(empty)==0);CHECK(pcc_gui_native_image_live_count(&out)==0&&out==0);CHECK(pcc_gui_tray_live_count(&out)==0&&out==0);int64_t menus=0,items=0;CHECK(pcc_gui_menu_live_count(&menus,&items)==0&&menus==0&&items==0);CHECK(pcc_gui_metal_window_close(handle)==0);
 puts("PCC_NATIVE_IMAGE_TRAY_OK copy=1 init_failure=1 path=1 image_lease=1 menu_owner=1 click=1 popup=1 deferred_release=1 window_lifetime=1 overflow=1 thread=1 counts=0");
}return 0;}
