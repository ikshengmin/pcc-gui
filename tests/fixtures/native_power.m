// Private centers and owned subscriptions only: no OS power transition.
#include "../../pcc_gui/native/pcc_gui_metal_render_bridge.m"
#include <pthread.h>
static void verify(BOOL ok,const char *expression,int line){if(!ok){fprintf(stderr,"power assertion %d: %s\n",line,expression);exit(90);}}
#define CHECK(x) verify((x),#x,__LINE__)
static int64_t open_center(NSNotificationCenter *center,int64_t mask){int64_t key=-1;CHECK(pcc_power_open_center(mask,center,&key)==0&&key>0);return key;}
static int64_t peek(int64_t key,int64_t expected){int64_t ready=-1,sequence=-2,kind=-3;CHECK(pcc_gui_power_peek(key,&ready,&sequence,&kind)==0&&ready==1&&kind==expected);return sequence;}
@interface FailingPowerCenter : NSNotificationCenter
@property(nonatomic) int additions,removals;
@property(nonatomic) BOOL throws;
@end
@implementation FailingPowerCenter
- (id)addObserverForName:(NSNotificationName)name object:(id)object queue:(NSOperationQueue *)queue usingBlock:(void(^)(NSNotification *))block {
 if(++self.additions==2){if(self.throws)@throw [NSException exceptionWithName:@"OwnedPowerFailure" reason:@"registration" userInfo:nil];return nil;}
 return [super addObserverForName:name object:object queue:queue usingBlock:block];
}
- (void)removeObserver:(id)observer {self.removals++;[super removeObserver:observer];}
@end
static void *post_worker(void *raw){@autoreleasepool{NSNotificationCenter *center=CFBridgingRelease(raw);[center postNotificationName:NSWorkspaceDidWakeNotification object:nil];[center postNotificationName:NSWorkspaceWillPowerOffNotification object:nil];}return NULL;}
static void *wrong_thread(void *raw){int64_t out=71,key=*(int64_t *)raw;CHECK(pcc_gui_power_open(3,&out)==2&&out==71);CHECK(pcc_gui_power_live_count(&out)==2&&out==71);CHECK(pcc_gui_power_release(key)==2);CHECK(pcc_gui_power_ack(key,1)==2);return NULL;}
static void *publish_race(void *raw){@autoreleasepool{PccGuiPower *held=CFBridgingRelease(raw);for(int i=0;i<20000;i++)pcc_power_publish(held,1);}return NULL;}
int main(void){@autoreleasepool{
 NSNotificationCenter *center=[NSNotificationCenter new];int64_t key=open_center(center,3),other=open_center(center,1),out=71;
 CHECK(pcc_gui_power_open(0,&out)==2&&out==71);CHECK(pcc_gui_power_open(4,&out)==2&&out==71);CHECK(pcc_gui_power_open(1,NULL)==2);CHECK(pcc_gui_power_peek(key,&out,&out,&out)==2&&out==71);
 int64_t ready=-1,sequence=-2,kind=-3;CHECK(pcc_gui_power_peek(key,&ready,&sequence,&kind)==0&&ready==0&&sequence==-2&&kind==-3);
 pthread_t worker;CHECK(pthread_create(&worker,NULL,post_worker,(void *)CFBridgingRetain(center))==0);CHECK(pthread_join(worker,NULL)==0);
 int64_t first=peek(key,1);CHECK(peek(key,1)==first);CHECK(pcc_gui_power_ack(key,first+99)==2);CHECK(pcc_gui_power_ack(key,first)==0);CHECK(pcc_gui_power_ack(key,first)==2);CHECK(peek(key,2)==first+1);CHECK(pcc_gui_power_ack(key,first+1)==0);CHECK(pcc_gui_power_ack(other,peek(other,1))==0);
 CHECK(pcc_gui_power_peek(other,&ready,&sequence,&kind)==0&&ready==0);
 CHECK(pthread_create(&worker,NULL,wrong_thread,&key)==0);CHECK(pthread_join(worker,NULL)==0);
 PccGuiPower *held=pcc_power_get(key);CHECK(pcc_gui_power_release(key)==0);CHECK(pcc_gui_power_release(key)==2);pcc_power_publish(held,1);CHECK(held->active==NO&&held->count==0);CHECK(pcc_gui_power_peek(key,&out,&sequence,&kind)==2&&out==71);
 [center postNotificationName:NSWorkspaceDidWakeNotification object:nil];CHECK(pcc_gui_power_ack(other,peek(other,1))==0);CHECK(pcc_gui_power_release(other)==0);
 for(int mode=0;mode<2;mode++){FailingPowerCenter *fail=[FailingPowerCenter new];fail.throws=mode;out=71;CHECK(pcc_power_open_center(3,fail,&out)==4&&out==71&&fail.additions==2&&fail.removals==1);}
 int64_t full=open_center(center,1);for(int i=0;i<257;i++)[center postNotificationName:NSWorkspaceDidWakeNotification object:nil];out=71;CHECK(pcc_gui_power_peek(full,&out,&sequence,&kind)==6&&out==71);CHECK(pcc_gui_power_release(full)==0);
 int64_t exhausted=open_center(center,1);PccGuiPower *slot=pcc_power_get(exhausted);slot->sequence=INT64_MAX;[center postNotificationName:NSWorkspaceDidWakeNotification object:nil];CHECK(pcc_gui_power_peek(exhausted,&out,&sequence,&kind)==6&&out==71);CHECK(pcc_gui_power_release(exhausted)==0);
 for(int i=0;i<64;i++){@autoreleasepool{int64_t racing=open_center(center,3);PccGuiPower *r=pcc_power_get(racing);CHECK(pthread_create(&worker,NULL,publish_race,(void *)CFBridgingRetain(r))==0);CHECK(pcc_gui_power_release(racing)==0);CHECK(pthread_join(worker,NULL)==0);CHECK(r->active==NO&&r->count==0);}}
 int64_t keys[256];for(int i=0;i<256;i++)keys[i]=open_center(center,1);out=71;CHECK(pcc_power_open_center(1,center,&out)==6&&out==71);for(int i=0;i<256;i++)CHECK(pcc_gui_power_release(keys[i])==0);
 // Production registration is exercised without posting a system notification.
 int64_t native=0;CHECK(pcc_gui_power_open(3,&native)==0);CHECK(pcc_gui_power_release(native)==0);CHECK(pcc_gui_power_live_count(&out)==0&&out==0);
 puts("PCC_NATIVE_POWER_OK worker=1 order=1 failure=2 races=64 overflow=1 sequence=1 capacity=1 stale=1 counts=0");
}return 0;}
