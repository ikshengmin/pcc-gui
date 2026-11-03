// Only this process's appearance/windows and private notification providers.
#include "../../pcc_gui/native/pcc_gui_metal_render_bridge.m"
#include <pthread.h>
static void verify(BOOL ok,const char *expression,int line){if(!ok){fprintf(stderr,"appearance assertion %d: %s\n",line,expression);exit(90);}}
#define CHECK(x) verify((x),#x,__LINE__)
static void pump(void){[[NSRunLoop currentRunLoop]runUntilDate:[NSDate dateWithTimeIntervalSinceNow:0.04]];}
static int drain(int64_t key){int count=0;for(;;){int64_t ready=0,seq=0,source=0,flags=0;CHECK(pcc_gui_appearance_event_peek(key,&ready,&seq,&source,&flags)==0);if(!ready)return count;CHECK(pcc_gui_appearance_event_ack(key,seq+10000)==2);CHECK(pcc_gui_appearance_event_ack(key,seq)==0);count++;}}
@interface FakeAppearanceApp : NSObject {
 NSAppearance *_raw;
}
@property(nonatomic,strong) NSAppearance *appearance;
@property(nonatomic,readonly) NSAppearance *effectiveAppearance;
@property(nonatomic) int registered,removed,failMode;
@property(nonatomic) int64_t releaseOnRead,releasedStatus;
@end
@implementation FakeAppearanceApp
+ (NSSet *)keyPathsForValuesAffectingEffectiveAppearance{return [NSSet setWithObject:@"appearance"];}
- (NSAppearance *)appearance{if(self.releaseOnRead){int64_t key=self.releaseOnRead;self.releaseOnRead=0;self.releasedStatus=pcc_gui_appearance_release(key);}return _raw;}
- (void)setAppearance:(NSAppearance *)value{_raw=value;}
- (NSAppearance *)effectiveAppearance{return _raw?:[NSAppearance appearanceNamed:NSAppearanceNameAqua];}
- (void)addObserver:(NSObject *)observer forKeyPath:(NSString *)path options:(NSKeyValueObservingOptions)options context:(void *)context {
 if([path isEqualToString:@"effectiveAppearance"]&&self.failMode==1)@throw [NSException exceptionWithName:@"OwnedRegistrationFailure" reason:@"before" userInfo:nil];
 [super addObserver:observer forKeyPath:path options:options context:context];self.registered++;
 if([path isEqualToString:@"effectiveAppearance"]&&self.failMode==2)@throw [NSException exceptionWithName:@"OwnedRegistrationFailure" reason:@"after" userInfo:nil];
}
- (void)removeObserver:(NSObject *)observer forKeyPath:(NSString *)path context:(void *)context {[super removeObserver:observer forKeyPath:path context:context];self.removed++;}
@end
static void *notify_worker(void *raw){@autoreleasepool{NSNotificationCenter *center=CFBridgingRelease(raw);[center postNotificationName:NSWorkspaceAccessibilityDisplayOptionsDidChangeNotification object:nil];}return NULL;}
static void *wrong_thread(void *raw){int64_t out=71;CHECK(pcc_gui_appearance_live_count(&out)==2&&out==71);CHECK(pcc_gui_appearance_set_source(*(int64_t *)raw,2)==2);CHECK(pcc_gui_appearance_release(*(int64_t *)raw)==2);return NULL;}
@interface AppearancePicture : NSView
@end
@implementation AppearancePicture
- (void)drawRect:(NSRect)rect{[NSColor.windowBackgroundColor setFill];NSRectFill(self.bounds);[@"Owned application appearance" drawAtPoint:NSMakePoint(32,390) withAttributes:@{NSFontAttributeName:[NSFont systemFontOfSize:25],NSForegroundColorAttributeName:NSColor.labelColor}];[NSColor.controlAccentColor setFill];NSRectFill(NSMakeRect(32,160,576,160));[@"Native dynamic colors" drawAtPoint:NSMakePoint(60,220) withAttributes:@{NSFontAttributeName:[NSFont systemFontOfSize:24],NSForegroundColorAttributeName:NSColor.whiteColor}];}
@end
static void capture(AppearancePicture *view,NSString *path){[view display];NSBitmapImageRep *bitmap=[view bitmapImageRepForCachingDisplayInRect:view.bounds];CHECK(bitmap!=nil);[view cacheDisplayInRect:view.bounds toBitmapImageRep:bitmap];NSData *png=[bitmap representationUsingType:NSBitmapImageFileTypePNG properties:@{}];CHECK(png.length>1000&&[png writeToFile:path atomically:YES]);}
int main(int argc,char **argv){@autoreleasepool{
 CHECK(argc==2);[NSApplication sharedApplication];NSNotificationCenter *center=[NSNotificationCenter new];int64_t key=0,out=71,source=-1,flags=-1;
 for(int mode=1;mode<=2;mode++){@autoreleasepool{FakeAppearanceApp *fake=[FakeAppearanceApp new];fake.failMode=mode;CHECK(pcc_appearance_open_environment((NSApplication *)fake,center,^int64_t{return 0;},&out)==4&&out==71);CHECK(fake.registered==fake.removed);CHECK(pcc_gui_appearance_live_count(&out)==0&&out==0);out=71;}}
 FakeAppearanceApp *fake=[FakeAppearanceApp new];__block int64_t nativeFlags=0;__block int samples=0;CHECK(pcc_appearance_open_environment((NSApplication *)fake,center,^int64_t{CHECK([NSThread isMainThread]);samples++;return nativeFlags;},&key)==0);CHECK(samples==1);CHECK(pcc_gui_appearance_open(&out)==5&&out==71);
 fake.releaseOnRead=key;CHECK(pcc_gui_appearance_set_source(key,2)==0);CHECK(fake.releasedStatus==5&&pcc_appearance_get(key)!=nil);CHECK([fake.appearance.name isEqualToString:NSAppearanceNameDarkAqua]);pump();drain(key);
 pthread_t worker;nativeFlags=1;int before=samples;CHECK(pthread_create(&worker,NULL,notify_worker,(void *)CFBridgingRetain(center))==0);CHECK(pthread_join(worker,NULL)==0);CHECK(samples==before);pump();
 int64_t ready=0,sequence=0;CHECK(pcc_gui_appearance_event_peek(key,&ready,&sequence,&source,&flags)==0&&ready==1&&flags==1);int64_t first=sequence;nativeFlags=22;[center postNotificationName:NSWorkspaceAccessibilityDisplayOptionsDidChangeNotification object:nil];pump();CHECK(pcc_gui_appearance_event_peek(key,&ready,&sequence,&source,&flags)==0&&flags==1&&sequence==first);CHECK(pcc_gui_appearance_event_ack(key,sequence)==0);CHECK(pcc_gui_appearance_event_peek(key,&ready,&sequence,&source,&flags)==0&&flags==22);CHECK(pcc_gui_appearance_event_ack(key,sequence)==0);
 CHECK(pcc_gui_appearance_snapshot(key,&source,&flags)==0&&source==2&&flags==22);CHECK(pcc_gui_appearance_snapshot(key,&out,&out)==2&&out==71);
 PccGuiAppearance *held=pcc_appearance_get(key);nativeFlags=0;pcc_appearance_invalidate(held);CHECK(pcc_gui_appearance_release(key)==0);before=samples;pump();CHECK(samples==before&&held.events.count==0&&!held->active);CHECK(fake.appearance==nil);CHECK(fake.registered==fake.removed);
 // A queued sampler may observe retirement by its native provider; no sample
 // may publish after that retirement, and outputs must remain unchanged.
 __block int64_t reentrantKey=0;__block BOOL retireSample=NO;FakeAppearanceApp *retiring=[FakeAppearanceApp new];CHECK(pcc_appearance_open_environment((NSApplication *)retiring,center,^int64_t{if(retireSample){retireSample=NO;CHECK(pcc_gui_appearance_release(reentrantKey)==0);}return 1;},&key)==0);reentrantKey=key;CHECK(reentrantKey>0&&pcc_appearance_get(reentrantKey)!=nil);retireSample=YES;source=71;flags=72;CHECK(pcc_gui_appearance_snapshot(reentrantKey,&source,&flags)==2&&source==71&&flags==72);CHECK(!retireSample&&pcc_appearance_owner==nil);
 int64_t reopened=pcc_appearance_open_environment((NSApplication *)fake,center,^int64_t{return 0;},&key);if(reopened)fprintf(stderr,"appearance reopen status=%lld owner=%p opening=%d registrations=%d removals=%d\n",reopened,pcc_appearance_owner,pcc_appearance_opening,fake.registered,fake.removed);CHECK(reopened==0);held=pcc_appearance_get(key);for(int i=0;i<257;i++)pcc_appearance_sample(held,YES);out=71;CHECK(pcc_gui_appearance_event_peek(key,&out,&sequence,&source,&flags)==6&&out==71);CHECK(pcc_gui_appearance_release(key)==0);
 NSAppearance *previous=NSApp.appearance;CHECK(pcc_gui_appearance_open(&key)==0);CHECK(pcc_gui_appearance_set_source(key,1)==0);CHECK(pcc_gui_appearance_snapshot(key,&source,&flags)==0&&source==1&&(flags&1)==0);pump();drain(key);
 void *handle=pcc_gui_metal_window_create("PCC owned appearance",640,480);CHECK(handle!=NULL);CHECK(pcc_gui_metal_window_show(handle)==0);NSWindow *window=(__bridge NSWindow *)handle;AppearancePicture *picture=[[AppearancePicture alloc]initWithFrame:NSMakeRect(0,0,640,480)];window.contentView=picture;[window display];
 int64_t r=0,g=0,b=0,a=0;NSAppearance *drawing=NSAppearance.currentDrawingAppearance;CHECK(pcc_gui_appearance_color(key,0,&r,&g,&b,&a)==0);int64_t light=r+g+b;CHECK(NSAppearance.currentDrawingAppearance==drawing);capture(picture,[[NSString stringWithUTF8String:argv[1]]stringByAppendingString:@"-light.png"]);
 CHECK(pcc_gui_appearance_set_source(key,2)==0);CHECK(pcc_gui_appearance_snapshot(key,&source,&flags)==0&&source==2&&(flags&1)==1);pump();drawing=NSAppearance.currentDrawingAppearance;CHECK(pcc_gui_appearance_color(key,0,&r,&g,&b,&a)==0&&r+g+b<light);capture(picture,[[NSString stringWithUTF8String:argv[1]]stringByAppendingString:@"-dark.png"]);CHECK(NSAppearance.currentDrawingAppearance==drawing);
 window.appearance=[NSAppearance appearanceNamed:NSAppearanceNameAqua];CHECK(([[window.effectiveAppearance bestMatchFromAppearancesWithNames:@[NSAppearanceNameAqua,NSAppearanceNameDarkAqua]]isEqualToString:NSAppearanceNameAqua]));
 CHECK(pthread_create(&worker,NULL,wrong_thread,&key)==0);CHECK(pthread_join(worker,NULL)==0);CHECK(pcc_gui_appearance_release(key)==0);CHECK(NSApp.appearance==previous);CHECK(pcc_gui_appearance_release(key)==2);
 CHECK(pcc_gui_appearance_open(&key)==0);CHECK(pcc_gui_appearance_set_source(key,2)==0);NSAppearance *foreign=[NSAppearance appearanceNamed:NSAppearanceNameAqua];NSApp.appearance=foreign;CHECK(pcc_gui_appearance_set_source(key,0)==5);CHECK(pcc_gui_appearance_release(key)==0&&NSApp.appearance==foreign);NSApp.appearance=previous;
 CHECK(pcc_gui_appearance_live_count(&out)==0&&out==0);CHECK(pcc_gui_metal_window_close(handle)==0);pump();
 puts("PCC_NATIVE_APPEARANCE_OK registration=2 preflight_reentry=1 worker=1 snapshots=1 late=1 sampler_retirement=1 overflow=1 light_dark=1 colors=1 window_override=1 restore=1 foreign=1 thread=1 leases=0");
}return 0;}
