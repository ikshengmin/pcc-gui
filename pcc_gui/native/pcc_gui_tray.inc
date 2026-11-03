// App-owned status items reuse canonical image leases and menu graph ownership.
#include "pcc_gui_tray.h"
@class PccGuiTray;
@interface PccGuiTrayEvent : NSObject
@property(nonatomic) int64_t sequence,kind,flags;
@end
@implementation PccGuiTrayEvent
@end
@interface PccGuiTray : NSObject
@property(nonatomic,strong) NSStatusItem *native;
@property(nonatomic,strong) NSImage *image;
@property(nonatomic,strong) PccGuiMenu *menu;
@property(nonatomic,strong) NSMutableArray<PccGuiTrayEvent *> *events;
@property(nonatomic) int64_t key,sequence,failure;
@property(nonatomic) BOOL retiring;
- (void)clicked:(id)sender;
@end
static NSMutableDictionary<NSNumber *,PccGuiTray *> *pcc_trays;
static int64_t pcc_tray_next=1;
static PccGuiTray *pcc_tray_get(int64_t key){return key>0?pcc_trays[@(key)]:nil;}
static void pcc_tray_finish(PccGuiTray *tray){
 if(tray.menu.externalOwner==tray)tray.menu.externalOwner=nil;tray.menu=nil;
 tray.native.button.target=nil;tray.native.button.action=NULL;
 if(tray.native)[[NSStatusBar systemStatusBar]removeStatusItem:tray.native];tray.native=nil;tray.image=nil;[tray.events removeAllObjects];
}
static void pcc_tray_publish(PccGuiTray *tray,int64_t kind,int64_t flags){
 if(!tray||tray.retiring||pcc_tray_get(tray.key)!=tray||tray.failure)return;
 if(tray.events.count>=256||tray.sequence==INT64_MAX){tray.failure=6;return;}
 PccGuiTrayEvent *event=[PccGuiTrayEvent new];if(!event){tray.failure=4;return;}event.sequence=tray.sequence++;event.kind=kind;event.flags=flags;[tray.events addObject:event];
}
@implementation PccGuiTray
- (void)clicked:(id)sender {if(sender!=self.native.button)return;NSEvent *event=NSApp.currentEvent;NSEventModifierFlags m=event.modifierFlags;int64_t flags=0;if(m&NSEventModifierFlagShift)flags|=1;if(m&NSEventModifierFlagControl)flags|=2;if(m&NSEventModifierFlagOption)flags|=4;if(m&NSEventModifierFlagCommand)flags|=8;pcc_tray_publish(self,event.type==NSEventTypeRightMouseUp?2:1,flags);}
@end
int64_t pcc_gui_tray_create(int64_t imageKey,int64_t *out){
 if(![NSThread isMainThread]||!pcc_menu_output(out)||imageKey<0)return 2;if(!NSApp)return 4;PccGuiNativeImage *image=imageKey?pcc_native_image_get(imageKey):nil;if(imageKey&&!image)return 2;
 if(pcc_tray_next==INT64_MAX||pcc_trays.count>=256)return 6;
 @autoreleasepool{PccGuiTray *tray=nil;@try{tray=[PccGuiTray new];if(!tray)return 4;tray.native=[[NSStatusBar systemStatusBar]statusItemWithLength:NSSquareStatusItemLength];tray.events=[NSMutableArray new];if(!tray.native||!tray.native.button||!tray.events){pcc_tray_finish(tray);return 4;}
 tray.image=image.native;tray.native.button.image=tray.image;tray.native.button.target=tray;tray.native.button.action=@selector(clicked:);[tray.native.button sendActionOn:NSEventMaskLeftMouseUp|NSEventMaskRightMouseUp];tray.sequence=1;
 if(!pcc_trays)pcc_trays=[NSMutableDictionary new];if(!pcc_trays){pcc_tray_finish(tray);return 4;}tray.key=pcc_tray_next++;pcc_trays[@(tray.key)]=tray;*out=tray.key;return 0;
 }@catch(NSException *error){if(tray)pcc_tray_finish(tray);return 4;}}
}
int64_t pcc_gui_tray_set_image(int64_t key,int64_t imageKey){
 if(![NSThread isMainThread]||imageKey<0)return 2;PccGuiTray *tray=pcc_tray_get(key);PccGuiNativeImage *image=imageKey?pcc_native_image_get(imageKey):nil;if(!tray||(imageKey&&!image))return 2;
 @try{NSImage *selected=image.native;tray.native.button.image=selected;tray.image=selected;return 0;}@catch(NSException *error){return 4;}
}
int64_t pcc_gui_tray_tooltip(int64_t key,const void *bytes,int64_t length){if(![NSThread isMainThread])return 2;PccGuiTray *tray=pcc_tray_get(key);if(!tray)return 2;NSString *text=nil;int64_t status=pcc_menu_text(bytes,length,&text);if(status)return status;@try{tray.native.button.toolTip=text;return 0;}@catch(NSException *error){return 4;}}
int64_t pcc_gui_tray_menu(int64_t key,int64_t menuKey){
 if(![NSThread isMainThread])return 2;PccGuiTray *tray=pcc_tray_get(key);PccGuiMenu *menu=menuKey?pcc_menu_get(menuKey):nil;if(!tray||(menuKey&&!menu))return 2;
 if((tray.menu&&pcc_menu_busy(tray.menu))||(menu&&pcc_menu_busy(menu)))return 5;
 if(menu&&(menu.parent||menu.key==pcc_menu_application||(menu.externalOwner&&menu.externalOwner!=tray)||menu.events.count))return 5;
 if(tray.menu.externalOwner==tray)tray.menu.externalOwner=nil;tray.menu=menu;if(menu)menu.externalOwner=tray;return 0;
}
int64_t pcc_gui_tray_popup(int64_t key){
 if(![NSThread isMainThread])return 2;PccGuiTray *tray=pcc_tray_get(key);if(!tray||!tray.menu)return 2;if(tray.failure)return tray.failure;
 int64_t status=0;@try{NSView *view=tray.native.button;status=pcc_menu_track_view(tray.menu,view,NSMakePoint(NSMinX(view.bounds),NSMinY(view.bounds)),-1,tray);}@finally{if(tray.retiring)pcc_tray_finish(tray);}return status;
}
int64_t pcc_gui_tray_event_peek(int64_t key,int64_t *ready,int64_t *sequence,int64_t *kind,int64_t *flags){
 if(![NSThread isMainThread])return 2;int64_t *out[4]={ready,sequence,kind,flags};for(int i=0;i<4;i++){if(!pcc_menu_output(out[i]))return 2;for(int j=0;j<i;j++)if(out[i]==out[j])return 2;}
 PccGuiTray *tray=pcc_tray_get(key);if(!tray)return 2;if(tray.failure)return tray.failure;*ready=tray.events.count?1:0;if(tray.events.count){PccGuiTrayEvent *event=tray.events[0];*sequence=event.sequence;*kind=event.kind;*flags=event.flags;}return 0;
}
int64_t pcc_gui_tray_event_ack(int64_t key,int64_t sequence){if(![NSThread isMainThread])return 2;PccGuiTray *tray=pcc_tray_get(key);if(!tray||!tray.events.count||tray.events[0].sequence!=sequence)return 2;[tray.events removeObjectAtIndex:0];return 0;}
int64_t pcc_gui_tray_release(int64_t key){
 if(![NSThread isMainThread])return 2;PccGuiTray *tray=pcc_tray_get(key);if(!tray)return 2;
 BOOL tracking=tray.menu&&tray.menu.tracking;if(tray.menu&&pcc_menu_busy(tray.menu)&&!tracking)return 5;
 tray.retiring=YES;tray.native.button.target=nil;tray.native.button.action=NULL;[tray.events removeAllObjects];[pcc_trays removeObjectForKey:@(key)];
 if(tracking){pcc_gui_menu_cancel(tray.menu.key);return 0;}pcc_tray_finish(tray);return 0;
}
int64_t pcc_gui_tray_live_count(int64_t *out){if(![NSThread isMainThread]||!pcc_menu_output(out))return 2;*out=(int64_t)pcc_trays.count;return 0;}
