// AppKit ownership only. No source object/callback crosses native notification threads.
#include "pcc_gui_appearance.h"
#include <pthread.h>
#include <limits.h>
#include <math.h>
@interface PccGuiAppearanceEvent : NSObject
@property(nonatomic) int64_t sequence,source,flags;
@end
@implementation PccGuiAppearanceEvent
@end
@interface PccGuiAppearance : NSObject {
 @public pthread_mutex_t lock;
 @public BOOL lockReady,active,dirty,forceSample,scheduled,mutating;
}
@property(nonatomic,strong) NSApplication *application;
@property(nonatomic,strong) NSNotificationCenter *center;
@property(nonatomic,strong) id workspaceToken;
@property(nonatomic,strong) NSAppearance *previous,*installed;
@property(nonatomic,strong) NSMutableArray<PccGuiAppearanceEvent *> *events;
@property(nonatomic,copy) int64_t (^readFlags)(void);
@property(nonatomic) int64_t key,source,flags,sequence,failure;
@property(nonatomic) BOOL rawRegistered,effectiveRegistered,written,hasSample;
@end
static PccGuiAppearance *pcc_appearance_owner;
static BOOL pcc_appearance_opening;
static int64_t pcc_appearance_next=1;
static char pcc_appearance_raw_context,pcc_appearance_effective_context;
static void pcc_appearance_invalidate(PccGuiAppearance *owner);
static BOOL pcc_appearance_output(int64_t *out){return out&&((uintptr_t)out%_Alignof(int64_t))==0;}
static PccGuiAppearance *pcc_appearance_get(int64_t key){return key>0&&pcc_appearance_owner.key==key?pcc_appearance_owner:nil;}
@implementation PccGuiAppearance
- (instancetype)init {self=[super init];if(self){if(pthread_mutex_init(&lock,NULL)!=0)return nil;lockReady=YES;active=YES;}return self;}
- (void)dealloc {if(lockReady)pthread_mutex_destroy(&lock);}
- (void)observeValueForKeyPath:(NSString *)path ofObject:(id)object change:(NSDictionary *)change context:(void *)context {
 if((context==&pcc_appearance_raw_context||context==&pcc_appearance_effective_context)&&object==self.application){pcc_appearance_invalidate(self);return;}[super observeValueForKeyPath:path ofObject:object change:change context:context];
}
@end
static int64_t pcc_appearance_flags(NSApplication *application,NSWorkspace *workspace){
 NSAppearanceName selected=[application.effectiveAppearance bestMatchFromAppearancesWithNames:@[NSAppearanceNameAqua,NSAppearanceNameDarkAqua]];
 int64_t flags=[selected isEqualToString:NSAppearanceNameDarkAqua]?1:0;
 if(workspace.accessibilityDisplayShouldIncreaseContrast)flags|=2;if(workspace.accessibilityDisplayShouldInvertColors)flags|=4;if(workspace.accessibilityDisplayShouldReduceTransparency)flags|=8;if(workspace.accessibilityDisplayShouldDifferentiateWithoutColor)flags|=16;if(workspace.accessibilityDisplayShouldReduceMotion)flags|=32;return flags;
}
static int64_t pcc_appearance_sample(PccGuiAppearance *owner,BOOL force){
 if(owner.failure)return owner.failure;
 @try{int64_t flags=owner.readFlags();if(flags<0||flags>63){owner.failure=4;return 4;}BOOL changed=owner.hasSample&&(force||flags!=owner.flags);owner.flags=flags;owner.hasSample=YES;
  if(changed){if(owner.events.count>=256||owner.sequence==INT64_MAX){owner.failure=6;return 6;}PccGuiAppearanceEvent *event=[PccGuiAppearanceEvent new];if(!event){owner.failure=4;return 4;}event.sequence=owner.sequence++;event.source=owner.source;event.flags=flags;[owner.events addObject:event];}return 0;
 }@catch(NSException *error){owner.failure=4;return 4;}
}
static void pcc_appearance_invalidate(PccGuiAppearance *owner){
 if(!owner)return;BOOL post=NO;pthread_mutex_lock(&owner->lock);
 if(owner->active){owner->dirty=YES;if(!owner->mutating)owner->forceSample=YES;if(!owner->scheduled){owner->scheduled=YES;post=YES;}}
 pthread_mutex_unlock(&owner->lock);if(!post)return;
 __weak PccGuiAppearance *weak=owner;dispatch_async(dispatch_get_main_queue(),^{PccGuiAppearance *held=weak;if(!held)return;
  pthread_mutex_lock(&held->lock);held->scheduled=NO;BOOL run=held->active&&held->dirty;BOOL force=held->forceSample;held->dirty=NO;held->forceSample=NO;pthread_mutex_unlock(&held->lock);
  if(run)pcc_appearance_sample(held,force);
 });
}
static int64_t pcc_appearance_retire(PccGuiAppearance *owner,BOOL restore){
 pthread_mutex_lock(&owner->lock);owner->active=NO;owner->dirty=NO;owner->forceSample=NO;pthread_mutex_unlock(&owner->lock);
 if(owner.rawRegistered){@try{[owner.application removeObserver:owner forKeyPath:@"appearance" context:&pcc_appearance_raw_context];}@catch(NSException *ignored){}owner.rawRegistered=NO;}
 if(owner.effectiveRegistered){@try{[owner.application removeObserver:owner forKeyPath:@"effectiveAppearance" context:&pcc_appearance_effective_context];}@catch(NSException *ignored){}owner.effectiveRegistered=NO;}
 if(owner.workspaceToken){[owner.center removeObserver:owner.workspaceToken];owner.workspaceToken=nil;}
 [owner.events removeAllObjects];int64_t status=0;
 if(restore&&owner.written){@try{if(owner.application.appearance==owner.installed)owner.application.appearance=owner.previous;}@catch(NSException *error){status=4;}}
 owner.readFlags=nil;owner.center=nil;return status;
}
// Private provider seam lets tests inject native observations/registration failure
// without altering accessibility preferences or installing another app delegate.
static int64_t pcc_appearance_open_environment(NSApplication *application,NSNotificationCenter *center,int64_t(^readFlags)(void),int64_t *out){
 if(![NSThread isMainThread]||!pcc_appearance_output(out))return 2;if(!application||!center||!readFlags)return 4;if(pcc_appearance_owner||pcc_appearance_opening)return 5;if(pcc_appearance_next==INT64_MAX)return 6;
 pcc_appearance_opening=YES;PccGuiAppearance *owner=nil;
 @try{owner=[PccGuiAppearance new];if(!owner)return 4;owner.application=application;owner.center=center;owner.readFlags=readFlags;owner.events=[NSMutableArray new];owner.sequence=1;owner.previous=application.appearance;owner.installed=owner.previous;if(!owner.events)return 4;
  if(pcc_appearance_sample(owner,NO)){pcc_appearance_retire(owner,NO);return 4;}
  owner.rawRegistered=YES;[application addObserver:owner forKeyPath:@"appearance" options:0 context:&pcc_appearance_raw_context];owner.effectiveRegistered=YES;[application addObserver:owner forKeyPath:@"effectiveAppearance" options:0 context:&pcc_appearance_effective_context];
  __weak PccGuiAppearance *weak=owner;owner.workspaceToken=[center addObserverForName:NSWorkspaceAccessibilityDisplayOptionsDidChangeNotification object:nil queue:nil usingBlock:^(NSNotification *note){PccGuiAppearance *held=weak;pcc_appearance_invalidate(held);}];if(!owner.workspaceToken){pcc_appearance_retire(owner,NO);return 4;}
  owner.key=pcc_appearance_next++;pcc_appearance_owner=owner;*out=owner.key;return 0;
 }@catch(NSException *error){if(owner)pcc_appearance_retire(owner,NO);return 4;}@finally{pcc_appearance_opening=NO;}
}
int64_t pcc_gui_appearance_open(int64_t *out){if(![NSThread isMainThread]||!pcc_appearance_output(out))return 2;if(!NSApp)return 4;NSApplication *app=NSApp;NSWorkspace *workspace=NSWorkspace.sharedWorkspace;return pcc_appearance_open_environment(app,workspace.notificationCenter,^int64_t{return pcc_appearance_flags(app,workspace);},out);}
int64_t pcc_gui_appearance_set_source(int64_t key,int64_t source){
 if(![NSThread isMainThread]||source<0||source>2)return 2;PccGuiAppearance *owner=pcc_appearance_get(key);if(!owner)return 2;if(owner.failure)return owner.failure;
 pthread_mutex_lock(&owner->lock);BOOL busy=owner->mutating;pthread_mutex_unlock(&owner->lock);if(busy||owner.application.appearance!=owner.installed)return 5;
 NSAppearance *selected=source==0?nil:[NSAppearance appearanceNamed:source==1?NSAppearanceNameAqua:NSAppearanceNameDarkAqua];if(source&&!selected)return 4;
 NSAppearance *oldInstalled=owner.installed;int64_t oldSource=owner.source;BOOL oldWritten=owner.written;int64_t status=0;
 pthread_mutex_lock(&owner->lock);owner->mutating=YES;pthread_mutex_unlock(&owner->lock);owner.source=source;owner.installed=selected;owner.written=YES;
 @try{owner.application.appearance=selected;if(owner.application.appearance!=selected)status=5;}
 @catch(NSException *error){status=4;if(owner.application.appearance==oldInstalled){owner.installed=oldInstalled;owner.source=oldSource;owner.written=oldWritten;}}
 @finally{int64_t sampled=pcc_appearance_sample(owner,NO);if(!status)status=sampled;pthread_mutex_lock(&owner->lock);owner->mutating=NO;pthread_mutex_unlock(&owner->lock);}
 return status;
}
int64_t pcc_gui_appearance_snapshot(int64_t key,int64_t *source,int64_t *flags){
 if(![NSThread isMainThread]||!pcc_appearance_output(source)||!pcc_appearance_output(flags)||source==flags)return 2;PccGuiAppearance *owner=pcc_appearance_get(key);if(!owner)return 2;if(owner->mutating)return 5;int64_t status=pcc_appearance_sample(owner,NO);if(status)return status;*source=owner.source;*flags=owner.flags;return 0;
}
int64_t pcc_gui_appearance_event_peek(int64_t key,int64_t *ready,int64_t *sequence,int64_t *source,int64_t *flags){
 if(![NSThread isMainThread])return 2;int64_t *out[4]={ready,sequence,source,flags};for(int i=0;i<4;i++){if(!pcc_appearance_output(out[i]))return 2;for(int j=0;j<i;j++)if(out[i]==out[j])return 2;}
 PccGuiAppearance *owner=pcc_appearance_get(key);if(!owner)return 2;if(owner.failure)return owner.failure;*ready=owner.events.count?1:0;if(owner.events.count){PccGuiAppearanceEvent *event=owner.events[0];*sequence=event.sequence;*source=event.source;*flags=event.flags;}return 0;
}
int64_t pcc_gui_appearance_event_ack(int64_t key,int64_t sequence){if(![NSThread isMainThread])return 2;PccGuiAppearance *owner=pcc_appearance_get(key);if(!owner||!owner.events.count||owner.events[0].sequence!=sequence)return 2;[owner.events removeObjectAtIndex:0];return 0;}
int64_t pcc_gui_appearance_color(int64_t key,int64_t role,int64_t *r,int64_t *g,int64_t *b,int64_t *a){
 if(![NSThread isMainThread]||role<0||role>3)return 2;int64_t *out[4]={r,g,b,a};for(int i=0;i<4;i++){if(!pcc_appearance_output(out[i]))return 2;for(int j=0;j<i;j++)if(out[i]==out[j])return 2;}
 PccGuiAppearance *owner=pcc_appearance_get(key);if(!owner)return 2;if(owner->mutating)return 5;if(owner.failure)return owner.failure;
 __block NSColor *color=nil;@try{[owner.application.effectiveAppearance performAsCurrentDrawingAppearance:^{NSColor *selected=role==0?NSColor.windowBackgroundColor:role==1?NSColor.labelColor:role==2?NSColor.controlBackgroundColor:NSColor.controlTextColor;color=[selected colorUsingColorSpace:NSColorSpace.sRGBColorSpace];}];if(!color)return 4;CGFloat red,green,blue,alpha;[color getRed:&red green:&green blue:&blue alpha:&alpha];double values[4]={red,green,blue,alpha};int64_t bytes[4];for(int i=0;i<4;i++){if(!isfinite(values[i]))return 4;double v=values[i]<0?0:values[i]>1?1:values[i];bytes[i]=(int64_t)floor(v*255+0.5);}for(int i=0;i<4;i++)*out[i]=bytes[i];return 0;}@catch(NSException *error){return 4;}
}
int64_t pcc_gui_appearance_release(int64_t key){if(![NSThread isMainThread])return 2;PccGuiAppearance *owner=pcc_appearance_get(key);if(!owner)return 2;if(owner->mutating)return 5;pcc_appearance_owner=nil;return pcc_appearance_retire(owner,YES);}
int64_t pcc_gui_appearance_live_count(int64_t *out){if(![NSThread isMainThread]||!pcc_appearance_output(out))return 2;*out=pcc_appearance_owner?1:0;return 0;}
