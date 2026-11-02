// One canonical AppKit implementation. Native state owns no Python/T2 graph.
#include "pcc_gui_dialog.h"
#include <limits.h>
@interface PccGuiMessageBox : NSObject
@property(nonatomic,strong) NSAlert *alert;
@property(nonatomic,strong) NSMutableArray<NSString *> *labels;
@property(nonatomic,strong) NSWindow *parent;
@property(nonatomic,strong) id closingObserver;
@property(nonatomic,assign) NSModalSession modal;
@property(nonatomic) int64_t key,phase,defaultId,cancelId,response,checked;
@property(nonatomic) NSInteger selected;
@property(nonatomic,strong) NSString *title;
- (void)clicked:(NSButton *)button;
@end
static NSMutableDictionary<NSNumber *,PccGuiMessageBox *> *pcc_dialogs;
static int64_t pcc_dialog_next=1,pcc_dialog_active=0;
static BOOL pcc_dialog_pumping=NO;
static PccGuiMessageBox *pcc_dialog_get(int64_t key){return key>0?pcc_dialogs[@(key)]:nil;}
static void pcc_dialog_finish(PccGuiMessageBox *box,NSInteger code){
 if(box.phase!=1)return;
 box.response=code>=NSAlertFirstButtonReturn&&code<NSAlertFirstButtonReturn+(NSInteger)box.labels.count?code-NSAlertFirstButtonReturn:box.cancelId;
 box.checked=box.alert.showsSuppressionButton&&box.alert.suppressionButton.state==NSControlStateValueOn;
 box.phase=2;[box.alert.window orderOut:nil];
 if(box.closingObserver){[[NSNotificationCenter defaultCenter] removeObserver:box.closingObserver];box.closingObserver=nil;}
 box.parent=nil;if(pcc_dialog_active==box.key)pcc_dialog_active=0;
}
@implementation PccGuiMessageBox
- (void)clicked:(NSButton *)button {
 if(self.phase!=1)return;
 self.selected=NSAlertFirstButtonReturn+button.tag;
 if(self.parent)[self.parent endSheet:self.alert.window returnCode:self.selected];
 else if(self.modal&&NSApp.modalWindow==self.alert.window)[NSApp stopModalWithCode:self.selected];
}
@end
static NSString *pcc_dialog_text(const void *bytes,int64_t length){return [[NSString alloc] initWithBytes:bytes length:(NSUInteger)length encoding:NSUTF8StringEncoding];}
int64_t pcc_gui_message_box_create(int64_t style,int64_t defaultId,int64_t cancelId,int64_t checked,int64_t *out){
 if(![NSThread isMainThread]||!out||style<0||style>2||defaultId< -1||defaultId>31||cancelId<0||cancelId>31||(checked!=0&&checked!=1))return 2;
 if(!NSApp)return 4;
 if(pcc_dialog_next==INT64_MAX)return 6;
 @autoreleasepool{
  PccGuiMessageBox *box=[PccGuiMessageBox new];box.alert=[NSAlert new];box.labels=[NSMutableArray new];box.title=@"";box.defaultId=defaultId;box.cancelId=cancelId;box.checked=checked;box.selected=NSModalResponseContinue;
  if(!box||!box.alert||!box.labels)return 4;
  box.alert.alertStyle=style==0?NSAlertStyleInformational:style==1?NSAlertStyleWarning:NSAlertStyleCritical;
  box.alert.messageText=@"";box.alert.informativeText=@"";
  if(!pcc_dialogs)pcc_dialogs=[NSMutableDictionary new];
  if(!pcc_dialogs)return 4;box.key=pcc_dialog_next++;pcc_dialogs[@(box.key)]=box;*out=box.key;return 0;
 }
}
int64_t pcc_gui_message_box_text(int64_t key,int64_t field,const void *bytes,int64_t length){
 if(![NSThread isMainThread]||length<0||(length&&!bytes)||field<0||field>3)return 2;
 PccGuiMessageBox *box=pcc_dialog_get(key);if(!box||box.phase!=0)return 2;if(length>1048576)return 6;
 @autoreleasepool{NSString *value=pcc_dialog_text(bytes,length);if(!value)return 3;
  if(field==0)box.title=value;else if(field==1)box.alert.messageText=value;else if(field==2)box.alert.informativeText=value;else{box.alert.showsSuppressionButton=value.length!=0;box.alert.suppressionButton.title=value;box.alert.suppressionButton.state=box.checked?NSControlStateValueOn:NSControlStateValueOff;}
  return 0;
 }
}
int64_t pcc_gui_message_box_button(int64_t key,const void *bytes,int64_t length){
 if(![NSThread isMainThread]||length<0||(length&&!bytes))return 2;
 PccGuiMessageBox *box=pcc_dialog_get(key);if(!box||box.phase!=0)return 2;if(length>1048576||box.labels.count>=32)return 6;
 @autoreleasepool{NSString *value=pcc_dialog_text(bytes,length);if(!value)return 3;[box.labels addObject:value];return 0;}
}
int64_t pcc_gui_message_box_begin(int64_t key,void *parent){
 if(![NSThread isMainThread]||pcc_dialog_pumping)return 2;
 PccGuiMessageBox *box=pcc_dialog_get(key);if(!box||box.phase!=0)return 2;if(pcc_dialog_active)return 5;
 NSWindow *owner=nil;
 if(parent){for(NSWindow *candidate in NSApp.windows)if((__bridge void *)candidate==parent){owner=candidate;break;}if(!owner)return 2;if(owner.attachedSheet)return 5;}
 NSUInteger count=box.labels.count?box.labels.count:1;
 if(box.defaultId>=(int64_t)count||box.cancelId>=(int64_t)count||(box.checked&&!box.alert.showsSuppressionButton))return 2;
 @autoreleasepool{@try{
  if(box.labels.count==0)[box.labels addObject:@"OK"];
  for(NSUInteger i=0;i<box.labels.count;i++){NSButton *button=[box.alert addButtonWithTitle:box.labels[i]];button.tag=(NSInteger)i;button.target=box;button.action=@selector(clicked:);button.keyEquivalent=@"";}
  if(box.defaultId>=0)box.alert.buttons[(NSUInteger)box.defaultId].keyEquivalent=@"\r";
  if(box.cancelId!=box.defaultId)box.alert.buttons[(NSUInteger)box.cancelId].keyEquivalent=@"\e";
  box.alert.window.title=box.title;box.parent=owner;box.phase=1;pcc_dialog_active=box.key;
  if(owner){
   __weak PccGuiMessageBox *weakBox=box;
   box.closingObserver=[[NSNotificationCenter defaultCenter] addObserverForName:NSWindowWillCloseNotification object:owner queue:nil usingBlock:^(NSNotification *note){PccGuiMessageBox *held=weakBox;if(held&&held.phase==1)pcc_gui_message_box_cancel(held.key);}];
   [box.alert beginSheetModalForWindow:owner completionHandler:^(NSModalResponse response){PccGuiMessageBox *held=weakBox;if(held)pcc_dialog_finish(held,response);}];
  }else{box.modal=[NSApp beginModalSessionForWindow:box.alert.window];if(!box.modal){box.phase=3;pcc_dialog_active=0;return 4;}[box.alert.window makeKeyAndOrderFront:nil];}
  return 0;
 }@catch(NSException *error){if(box.modal){[NSApp endModalSession:box.modal];box.modal=NULL;}if(box.closingObserver){[[NSNotificationCenter defaultCenter]removeObserver:box.closingObserver];box.closingObserver=nil;}box.parent=nil;box.phase=3;pcc_dialog_active=0;[box.alert.window orderOut:nil];return 4;}}
}
int64_t pcc_gui_message_box_poll(int64_t key,int64_t *ready,int64_t *response,int64_t *checked){
 if(![NSThread isMainThread]||!ready||!response||!checked||ready==response||ready==checked||response==checked)return 2;
 PccGuiMessageBox *box=pcc_dialog_get(key);if(!box||box.phase==0)return 2;if(box.phase==3)return 4;if(pcc_dialog_pumping)return 5;
 @autoreleasepool{
  if(box.phase==1&&box.modal){
   if(NSApp.modalWindow&&NSApp.modalWindow!=box.alert.window)return 5;
   pcc_dialog_pumping=YES;NSInteger result=box.selected;
   @try{if(result==NSModalResponseContinue)result=[NSApp runModalSession:box.modal];if(box.selected!=NSModalResponseContinue)result=box.selected;
    if(result!=NSModalResponseContinue){[NSApp endModalSession:box.modal];box.modal=NULL;pcc_dialog_finish(box,result);}
   }@finally{pcc_dialog_pumping=NO;}
  }
  *ready=box.phase==2;if(box.phase==2){*response=box.response;*checked=box.checked;}return 0;
 }
}
int64_t pcc_gui_message_box_cancel(int64_t key){
 if(![NSThread isMainThread])return 2;PccGuiMessageBox *box=pcc_dialog_get(key);if(!box||box.phase==0)return 2;if(box.phase==2)return 0;
 box.selected=NSAlertFirstButtonReturn+box.cancelId;
 if(box.parent)[box.parent endSheet:box.alert.window returnCode:box.selected];else if(box.modal&&NSApp.modalWindow==box.alert.window)[NSApp stopModalWithCode:box.selected];return 0;
}
int64_t pcc_gui_message_box_release(int64_t key){
 if(![NSThread isMainThread])return 2;PccGuiMessageBox *box=pcc_dialog_get(key);if(!box)return 2;if(box.phase==1||pcc_dialog_pumping)return 5;
 [pcc_dialogs removeObjectForKey:@(key)];return 0;
}
int64_t pcc_gui_message_box_live_count(int64_t *out){if(![NSThread isMainThread]||!out)return 2;*out=(int64_t)pcc_dialogs.count;return 0;}
