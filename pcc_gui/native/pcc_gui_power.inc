// Native event tap. It owns no source value, callback or application delegate.
#include "pcc_gui_power.h"
#include <pthread.h>
#include <limits.h>
typedef struct {int64_t sequence,kind;} PccGuiPowerEvent;
@interface PccGuiPower : NSObject {
 @public pthread_mutex_t lock;
 @public PccGuiPowerEvent events[256];
 @public NSUInteger head,count;
 @public BOOL active,lockReady;
 @public int64_t sequence,failure;
}
@property(nonatomic,strong) NSNotificationCenter *center;
@property(nonatomic,strong) id resumeToken,shutdownToken;
@property(nonatomic) int64_t key;
@end
@implementation PccGuiPower
- (instancetype)init {self=[super init];if(self){if(pthread_mutex_init(&lock,NULL)!=0)return nil;lockReady=YES;active=YES;sequence=1;}return self;}
- (void)dealloc {if(lockReady)pthread_mutex_destroy(&lock);}
@end
static NSMutableDictionary<NSNumber *,PccGuiPower *> *pcc_power_sessions;
static int64_t pcc_power_next=1;
static BOOL pcc_power_output(int64_t *out){return out&&((uintptr_t)out%_Alignof(int64_t))==0;}
static PccGuiPower *pcc_power_get(int64_t key){return key>0?pcc_power_sessions[@(key)]:nil;}
static void pcc_power_publish(PccGuiPower *session,int64_t kind){
 if(!session)return;pthread_mutex_lock(&session->lock);
 if(session->active&&!session->failure){
  if(session->count==256||session->sequence==INT64_MAX)session->failure=6;
  else{NSUInteger at=(session->head+session->count)%256;session->events[at]=(PccGuiPowerEvent){session->sequence++,kind};session->count++;}
 }
 pthread_mutex_unlock(&session->lock);
}
static void pcc_power_retire(PccGuiPower *session){
 pthread_mutex_lock(&session->lock);session->active=NO;session->count=0;pthread_mutex_unlock(&session->lock);
 if(session.resumeToken){[session.center removeObserver:session.resumeToken];session.resumeToken=nil;}
 if(session.shutdownToken){[session.center removeObserver:session.shutdownToken];session.shutdownToken=nil;}
 session.center=nil;
}
// One implementation; the native fixture supplies a private center to prove
// ownership/races without sending a computer sleep or shutdown notification.
static int64_t pcc_power_open_center(int64_t mask,NSNotificationCenter *center,int64_t *out){
 if(![NSThread isMainThread]||!pcc_power_output(out)||mask<=0||mask>3)return 2;if(!center)return 4;
 if(pcc_power_next==INT64_MAX||pcc_power_sessions.count>=256)return 6;
 @autoreleasepool{
  PccGuiPower *session=[PccGuiPower new];if(!session)return 4;session.center=center;
  __weak PccGuiPower *weakSession=session;
  @try{
   if(mask&1){session.resumeToken=[center addObserverForName:NSWorkspaceDidWakeNotification object:nil queue:nil usingBlock:^(NSNotification *notification){PccGuiPower *held=weakSession;pcc_power_publish(held,1);}];if(!session.resumeToken){pcc_power_retire(session);return 4;}}
   if(mask&2){session.shutdownToken=[center addObserverForName:NSWorkspaceWillPowerOffNotification object:nil queue:nil usingBlock:^(NSNotification *notification){PccGuiPower *held=weakSession;pcc_power_publish(held,2);}];if(!session.shutdownToken){pcc_power_retire(session);return 4;}}
   if(!pcc_power_sessions)pcc_power_sessions=[NSMutableDictionary new];if(!pcc_power_sessions){pcc_power_retire(session);return 4;}
   session.key=pcc_power_next++;pcc_power_sessions[@(session.key)]=session;*out=session.key;return 0;
  }@catch(NSException *error){pcc_power_retire(session);return 4;}
 }
}
int64_t pcc_gui_power_open(int64_t mask,int64_t *out){
 if(![NSThread isMainThread]||!pcc_power_output(out)||mask<=0||mask>3)return 2;
 @autoreleasepool{@try{return pcc_power_open_center(mask,[NSWorkspace sharedWorkspace].notificationCenter,out);}@catch(NSException *error){return 4;}}
}
int64_t pcc_gui_power_peek(int64_t key,int64_t *ready,int64_t *sequence,int64_t *kind){
 if(![NSThread isMainThread]||!pcc_power_output(ready)||!pcc_power_output(sequence)||!pcc_power_output(kind)||ready==sequence||ready==kind||sequence==kind)return 2;
 PccGuiPower *session=pcc_power_get(key);if(!session)return 2;
 int64_t status=0;BOOL available=NO;PccGuiPowerEvent event={0,0};
 pthread_mutex_lock(&session->lock);if(!session->active)status=2;else if(session->failure)status=session->failure;else if(session->count){available=YES;event=session->events[session->head];}pthread_mutex_unlock(&session->lock);
 if(status)return status;*ready=available?1:0;if(available){*sequence=event.sequence;*kind=event.kind;}return 0;
}
int64_t pcc_gui_power_ack(int64_t key,int64_t sequence){
 if(![NSThread isMainThread])return 2;PccGuiPower *session=pcc_power_get(key);if(!session)return 2;int64_t status=0;
 pthread_mutex_lock(&session->lock);if(!session->active||!session->count||session->events[session->head].sequence!=sequence)status=2;else{session->head=(session->head+1)%256;session->count--;}pthread_mutex_unlock(&session->lock);return status;
}
int64_t pcc_gui_power_release(int64_t key){if(![NSThread isMainThread])return 2;PccGuiPower *session=pcc_power_get(key);if(!session)return 2;pcc_power_retire(session);[pcc_power_sessions removeObjectForKey:@(key)];return 0;}
int64_t pcc_gui_power_live_count(int64_t *out){if(![NSThread isMainThread]||!pcc_power_output(out))return 2;*out=(int64_t)pcc_power_sessions.count;return 0;}
