// Canonical owned AppKit menu graph. Native state contains no source callbacks.
#include "pcc_gui_menu.h"
#include <limits.h>
@class PccGuiMenu;
@interface PccGuiMenuEvent : NSObject
@property(nonatomic) int64_t sequence,kind,item,command;
@end
@implementation PccGuiMenuEvent
@end
@interface PccGuiMenuItem : NSObject
@property(nonatomic,strong) NSMenuItem *native;
@property(nonatomic,weak) PccGuiMenu *owner;
@property(nonatomic,strong) PccGuiMenu *child;
@property(nonatomic) int64_t key,kind,command;
- (void)selected:(id)sender;
@end
@interface PccGuiMenu : NSObject<NSMenuDelegate>
@property(nonatomic,strong) NSMenu *native;
@property(nonatomic,strong) NSMutableArray<PccGuiMenuItem *> *items;
@property(nonatomic,strong) NSMutableArray<PccGuiMenuEvent *> *events;
@property(nonatomic,weak) PccGuiMenuItem *parent;
@property(nonatomic) int64_t key,failure;
@property(nonatomic) BOOL tracking,open;
@end
static NSMutableDictionary<NSNumber *,PccGuiMenu *> *pcc_menus;
static NSMutableDictionary<NSNumber *,PccGuiMenuItem *> *pcc_menu_items;
static int64_t pcc_menu_next=1,pcc_menu_sequence=1,pcc_menu_application=0,pcc_menu_tracking=0,pcc_menu_open_count=0;
static NSMenu *pcc_menu_previous_application;
static PccGuiMenu *pcc_menu_get(int64_t key){return key>0?pcc_menus[@(key)]:nil;}
static PccGuiMenuItem *pcc_menu_item(int64_t key){return key>0?pcc_menu_items[@(key)]:nil;}
static PccGuiMenu *pcc_menu_root(PccGuiMenu *menu){while(menu.parent)menu=menu.parent.owner;return menu;}
static BOOL pcc_menu_busy(PccGuiMenu *menu){PccGuiMenu *root=pcc_menu_root(menu);return root.tracking||pcc_menu_tracking!=0||pcc_menu_open_count!=0;}
static int64_t pcc_menu_text(const void *bytes,int64_t length,NSString **out){
 if(length<0||(length&&!bytes))return 2;if(length>1048576)return 6;
 NSString *value=[[NSString alloc]initWithBytes:bytes length:(NSUInteger)length encoding:NSUTF8StringEncoding];if(!value)return 3;*out=value;return 0;
}
static void pcc_menu_event(PccGuiMenu *menu,int64_t kind,PccGuiMenuItem *item){
 PccGuiMenu *root=pcc_menu_root(menu);if(!root||root.failure)return;
 if(root.events.count>=256||pcc_menu_sequence==INT64_MAX){root.failure=6;[root.native cancelTracking];return;}
 PccGuiMenuEvent *event=[PccGuiMenuEvent new];if(!event){root.failure=4;[root.native cancelTracking];return;}
 event.sequence=pcc_menu_sequence++;event.kind=kind;event.item=item?item.key:menu.key;event.command=item?item.command:0;[root.events addObject:event];
}
@implementation PccGuiMenuItem
- (void)selected:(id)sender {
 PccGuiMenu *owner=self.owner;
 if(owner&&pcc_menu_item(self.key)==self&&self.native.enabled&&!self.native.hidden&&self.kind==0)pcc_menu_event(owner,2,self);
}
@end
@implementation PccGuiMenu
- (void)menuWillOpen:(NSMenu *)menu {if(menu==self.native){if(!self.open){self.open=YES;pcc_menu_open_count++;}pcc_menu_event(self,1,nil);}}
- (void)menuDidClose:(NSMenu *)menu {if(menu==self.native){if(self.open){self.open=NO;pcc_menu_open_count--;}pcc_menu_event(self,3,nil);}}
@end
static BOOL pcc_menu_output(int64_t *value){return value&&((uintptr_t)value%_Alignof(int64_t))==0;}
int64_t pcc_gui_menu_create(int64_t *out){
 if(![NSThread isMainThread]||!pcc_menu_output(out))return 2;if(!NSApp)return 4;
 if(pcc_menu_next==INT64_MAX||pcc_menus.count>=256)return 6;
 @autoreleasepool{@try{
  PccGuiMenu *menu=[PccGuiMenu new];menu.native=[[NSMenu alloc]initWithTitle:@""];menu.items=[NSMutableArray new];menu.events=[NSMutableArray new];
  if(!menu||!menu.native||!menu.items||!menu.events)return 4;
  menu.native.autoenablesItems=NO;menu.native.delegate=menu;
  if(!pcc_menus)pcc_menus=[NSMutableDictionary new];if(!pcc_menu_items)pcc_menu_items=[NSMutableDictionary new];
  if(!pcc_menus||!pcc_menu_items)return 4;menu.key=pcc_menu_next++;pcc_menus[@(menu.key)]=menu;*out=menu.key;return 0;
 }@catch(NSException *error){return 4;}}
}
int64_t pcc_gui_menu_insert(int64_t key,int64_t index,int64_t kind,int64_t command,const void *bytes,int64_t length,int64_t *out){
 if(![NSThread isMainThread]||!pcc_menu_output(out)||kind<0||kind>2)return 2;
 PccGuiMenu *menu=pcc_menu_get(key);if(!menu||index<0||(uint64_t)index>menu.items.count)return 2;if(pcc_menu_busy(menu)||pcc_menu_root(menu).events.count)return 5;
 if(pcc_menu_next==INT64_MAX||menu.items.count>=1024||pcc_menu_items.count>=16384)return 6;
 @autoreleasepool{NSString *title=nil;int64_t status=pcc_menu_text(bytes,length,&title);if(status)return status;
  @try{PccGuiMenuItem *item=[PccGuiMenuItem new];item.native=kind==1?[NSMenuItem separatorItem]:[[NSMenuItem alloc]initWithTitle:title action:kind==0?@selector(selected:):NULL keyEquivalent:@""];
   if(!item||!item.native)return 4;item.owner=menu;item.key=pcc_menu_next++;item.command=command;item.kind=kind;item.native.target=kind==0?item:nil;
   [menu.native insertItem:item.native atIndex:(NSInteger)index];[menu.items insertObject:item atIndex:(NSUInteger)index];pcc_menu_items[@(item.key)]=item;*out=item.key;return 0;
  }@catch(NSException *error){return 4;}
 }
}
static void pcc_menu_detach(PccGuiMenuItem *item){if(item.child){item.native.submenu=nil;item.child.parent=nil;item.child=nil;}}
int64_t pcc_gui_menu_remove(int64_t key,int64_t index){
 if(![NSThread isMainThread])return 2;PccGuiMenu *menu=pcc_menu_get(key);if(!menu||index<0||(uint64_t)index>=menu.items.count)return 2;if(pcc_menu_busy(menu)||pcc_menu_root(menu).events.count)return 5;
 @autoreleasepool{@try{PccGuiMenuItem *item=menu.items[(NSUInteger)index];[menu.native removeItemAtIndex:(NSInteger)index];pcc_menu_detach(item);item.native.target=nil;item.owner=nil;[pcc_menu_items removeObjectForKey:@(item.key)];[menu.items removeObjectAtIndex:(NSUInteger)index];return 0;}@catch(NSException *error){return 4;}}
}
int64_t pcc_gui_menu_item_text(int64_t key,int64_t field,const void *bytes,int64_t length){
 if(![NSThread isMainThread]||field<0||field>1)return 2;PccGuiMenuItem *item=pcc_menu_item(key);if(!item)return 2;if(pcc_menu_busy(item.owner))return 5;
 @autoreleasepool{NSString *value=nil;int64_t status=pcc_menu_text(bytes,length,&value);if(status)return status;@try{if(field==0)item.native.title=value;else item.native.toolTip=value;return 0;}@catch(NSException *error){return 4;}}
}
int64_t pcc_gui_menu_item_state(int64_t key,int64_t flags,int64_t modifiers,const void *bytes,int64_t length){
 if(![NSThread isMainThread]||flags<0||flags>7||modifiers<0||modifiers>15)return 2;PccGuiMenuItem *item=pcc_menu_item(key);if(!item)return 2;if(pcc_menu_busy(item.owner))return 5;
 @autoreleasepool{NSString *value=nil;int64_t status=pcc_menu_text(bytes,length,&value);if(status)return status;
  NSEventModifierFlags mask=0;if(modifiers&1)mask|=NSEventModifierFlagShift;if(modifiers&2)mask|=NSEventModifierFlagControl;if(modifiers&4)mask|=NSEventModifierFlagOption;if(modifiers&8)mask|=NSEventModifierFlagCommand;
  @try{item.native.enabled=(flags&1)!=0;item.native.hidden=(flags&2)==0;item.native.state=(flags&4)?NSControlStateValueOn:NSControlStateValueOff;item.native.keyEquivalent=value;item.native.keyEquivalentModifierMask=mask;return 0;}@catch(NSException *error){return 4;}
 }
}
int64_t pcc_gui_menu_item_submenu(int64_t key,int64_t childKey){
 if(![NSThread isMainThread])return 2;PccGuiMenuItem *item=pcc_menu_item(key);PccGuiMenu *child=childKey?pcc_menu_get(childKey):nil;if(!item||item.kind!=2||(childKey&&!child))return 2;
 PccGuiMenu *root=pcc_menu_root(item.owner);if(pcc_menu_busy(root)||root.events.count)return 5;
 if(child){if(child==item.child)return 0;if(child.parent||child.key==pcc_menu_application||pcc_menu_root(child).events.count)return 5;for(PccGuiMenu *at=item.owner;at;at=at.parent.owner)if(at==child)return 2;}
 @autoreleasepool{@try{pcc_menu_detach(item);if(child){item.native.submenu=child.native;item.child=child;child.parent=item;}return 0;}@catch(NSException *error){return 4;}}
}
int64_t pcc_gui_menu_count(int64_t key,int64_t *out){if(![NSThread isMainThread]||!pcc_menu_output(out))return 2;PccGuiMenu *menu=pcc_menu_get(key);if(!menu)return 2;*out=(int64_t)menu.native.numberOfItems;return 0;}
int64_t pcc_gui_menu_set_application(int64_t key){
 if(![NSThread isMainThread])return 2;if(pcc_menu_tracking||pcc_menu_open_count)return 5;PccGuiMenu *menu=key?pcc_menu_get(key):nil;if(key&&!menu)return 2;if(menu&&menu.parent)return 5;
 @autoreleasepool{@try{
  PccGuiMenu *old=pcc_menu_get(pcc_menu_application);
  if(!key){if(old&&NSApp.mainMenu==old.native)NSApp.mainMenu=pcc_menu_previous_application;pcc_menu_application=0;pcc_menu_previous_application=nil;return 0;}
  if(old&&NSApp.mainMenu!=old.native)return 5;
  if(!old)pcc_menu_previous_application=NSApp.mainMenu;
  NSApp.mainMenu=menu.native;pcc_menu_application=key;return 0;
 }@catch(NSException *error){return 4;}}
}
int64_t pcc_gui_menu_popup(int64_t key,void *parent,int64_t x,int64_t y,int64_t positioning){
 if(![NSThread isMainThread]||!parent||x< -1000000||x>1000000||y< -1000000||y>1000000)return 2;
 PccGuiMenu *menu=pcc_menu_get(key);if(!menu||positioning< -1||positioning>=(int64_t)menu.items.count)return 2;if(menu.parent||pcc_menu_busy(menu)||menu.events.count)return 5;if(menu.failure)return menu.failure;
 NSWindow *window=nil;for(NSWindow *candidate in NSApp.windows)if((__bridge void *)candidate==parent){window=candidate;break;}if(!window||!window.contentView)return 2;
 @autoreleasepool{
  __weak PccGuiMenu *weakMenu=menu;id observer=[[NSNotificationCenter defaultCenter]addObserverForName:NSWindowWillCloseNotification object:window queue:nil usingBlock:^(NSNotification *note){PccGuiMenu *owned=weakMenu;if(owned.tracking)[owned.native cancelTracking];}];
  if(!observer)return 4;menu.tracking=YES;pcc_menu_tracking=key;int64_t status=0;
  @try{NSView *view=window.contentView;NSPoint point=NSMakePoint((CGFloat)x,view.isFlipped?(CGFloat)y:NSHeight(view.bounds)-(CGFloat)y);NSMenuItem *selected=positioning>=0?menu.items[(NSUInteger)positioning].native:nil;[menu.native popUpMenuPositioningItem:selected atLocation:point inView:view];}
  @catch(NSException *error){status=4;}
  @finally{[[NSNotificationCenter defaultCenter]removeObserver:observer];menu.tracking=NO;pcc_menu_tracking=0;}
  return menu.failure?menu.failure:status;
 }
}
int64_t pcc_gui_menu_cancel(int64_t key){if(![NSThread isMainThread])return 2;PccGuiMenu *menu=pcc_menu_get(key);if(!menu)return 2;PccGuiMenu *root=pcc_menu_root(menu);if(pcc_menu_tracking&&pcc_menu_tracking!=root.key)return 5;[root.native cancelTracking];return 0;}
int64_t pcc_gui_menu_event_peek(int64_t key,int64_t *ready,int64_t *sequence,int64_t *kind,int64_t *item,int64_t *command){
 int64_t *outputs[5]={ready,sequence,kind,item,command};if(![NSThread isMainThread])return 2;
 for(int i=0;i<5;i++){if(!pcc_menu_output(outputs[i]))return 2;for(int j=0;j<i;j++)if(outputs[i]==outputs[j])return 2;}
 PccGuiMenu *menu=pcc_menu_get(key);if(!menu)return 2;menu=pcc_menu_root(menu);if(menu.failure)return menu.failure;
 *ready=menu.events.count?1:0;if(menu.events.count){PccGuiMenuEvent *event=menu.events[0];*sequence=event.sequence;*kind=event.kind;*item=event.item;*command=event.command;}return 0;
}
int64_t pcc_gui_menu_event_ack(int64_t key,int64_t sequence){if(![NSThread isMainThread])return 2;PccGuiMenu *menu=pcc_menu_get(key);if(!menu)return 2;menu=pcc_menu_root(menu);if(menu.events.count==0||menu.events[0].sequence!=sequence)return 2;[menu.events removeObjectAtIndex:0];return 0;}
int64_t pcc_gui_menu_release(int64_t key){
 if(![NSThread isMainThread])return 2;PccGuiMenu *menu=pcc_menu_get(key);if(!menu)return 2;if(menu.parent||pcc_menu_busy(menu)||pcc_menu_application==key)return 5;
 @autoreleasepool{@try{for(PccGuiMenuItem *item in menu.items){pcc_menu_detach(item);item.native.target=nil;item.owner=nil;[pcc_menu_items removeObjectForKey:@(item.key)];}menu.native.delegate=nil;[menu.native removeAllItems];[menu.items removeAllObjects];[menu.events removeAllObjects];[pcc_menus removeObjectForKey:@(key)];return 0;}@catch(NSException *error){return 4;}}
}
int64_t pcc_gui_menu_live_count(int64_t *menus,int64_t *items){if(![NSThread isMainThread]||!pcc_menu_output(menus)||!pcc_menu_output(items)||menus==items)return 2;*menus=(int64_t)pcc_menus.count;*items=(int64_t)pcc_menu_items.count;return 0;}
