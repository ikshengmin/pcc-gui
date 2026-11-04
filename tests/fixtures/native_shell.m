// The generated-program fixture holds external effects inside this process.
#include "../../pcc_gui/native/pcc_gui_metal_render_bridge.m"
#import <objc/runtime.h>
#include <dispatch/dispatch.h>
#include <stdio.h>
#include <unistd.h>

static pthread_mutex_t fixture_lock = PTHREAD_MUTEX_INITIALIZER;
static NSMutableDictionary<NSNumber *, PccShellCompletion> *fixture_callbacks;
static NSString *fixture_url, *fixture_path;
static int64_t fixture_activates = -1;

int64_t pcc_gui_test_shell_open_external(int64_t owner, const void *url, int64_t len,
        int64_t activate, int64_t has_application, int64_t *out) {
    if (![NSThread isMainThread] || !pcc_protocol_outputs(&out, 1) ||
        (has_application != 0 && has_application != 1)) return 2;
    __block PccShellCompletion saved;
    int64_t key = 0;
    int64_t status = pcc_shell_open_with(owner, url, len, activate, &key, ^BOOL(NSURL *value) {
        fixture_url = [value.absoluteString copy];
        return has_application != 0;
    }, ^(NSURL *value, BOOL activates, PccShellCompletion complete) {
        fixture_activates = activates;
        saved = [complete copy];
    });
    if (status) return status;
    if (saved) {
        pthread_mutex_lock(&fixture_lock);
        if (!fixture_callbacks) fixture_callbacks = [NSMutableDictionary dictionary];
        BOOL space = fixture_callbacks.count < 256;
        if (space) fixture_callbacks[@(key)] = saved;
        pthread_mutex_unlock(&fixture_lock);
        if (!space) pcc_gui_protocol_fail(owner, key, 6);
    }
    *out = key;
    return 0;
}
int64_t pcc_gui_test_shell_finish(int64_t key, int64_t successful) {
    if (successful != 0 && successful != 1) return 2;
    pthread_mutex_lock(&fixture_lock);
    PccShellCompletion callback = fixture_callbacks[@(key)];
    [fixture_callbacks removeObjectForKey:@(key)];
    pthread_mutex_unlock(&fixture_lock);
    if (!callback) return 2;
    callback(successful != 0);
    return 0;
}
int64_t pcc_gui_test_shell_pending(void) {
    pthread_mutex_lock(&fixture_lock);
    int64_t count = (int64_t)fixture_callbacks.count;
    pthread_mutex_unlock(&fixture_lock);
    return count;
}
int64_t pcc_gui_test_shell_show_item_in_folder(int64_t owner, const void *path, int64_t len) {
    return pcc_shell_reveal_with(owner, path, len, ^(NSString *value) {
        fixture_path = [value copy];
    });
}
int64_t pcc_gui_test_shell_observation(int64_t field, void *buffer, int64_t capacity, int64_t *len) {
    if (![NSThread isMainThread] || !pcc_protocol_outputs(&len, 1) ||
        (field != 0 && field != 1) || capacity < 0 || (!buffer && capacity)) return 2;
    NSString *value = field ? fixture_path : fixture_url;
    if (!value) return 1;
    NSData *data = [value dataUsingEncoding:NSUTF8StringEncoding];
    if (!data) return 4;
    if (buffer && capacity < (int64_t)data.length) return 5;
    if (buffer && pcc_protocol_overlap(buffer, data.length, len, sizeof(*len))) return 2;
    if (buffer && data.length) memcpy(buffer, data.bytes, data.length);
    *len = (int64_t)data.length;
    return 0;
}
int64_t pcc_gui_test_shell_last_activate(int64_t *out) {
    if (![NSThread isMainThread] || !pcc_protocol_outputs(&out, 1)) return 2;
    if (fixture_activates < 0) return 1;
    *out = fixture_activates;
    return 0;
}

#ifndef PCC_GUI_SHELL_TEST_LIBRARY
#define CHECK(x) do { if (!(x)) { fprintf(stderr, "line %d failed: %s\n", __LINE__, #x); exit(1); } } while (0)
static int64_t new_owner(void) {
    int64_t owner = 0;
    CHECK(pcc_gui_protocol_open(&owner) == 0 && owner > 0);
    return owner;
}
static void take(int64_t owner, int64_t key, int64_t wanted_kind, int64_t wanted_code) {
    int64_t ready = -1, kind = -1, error = -1, metadata = -1, body = -1;
    CHECK(pcc_gui_protocol_response_peek(owner, key, &ready, &kind, &error, &metadata, &body)==0);
    CHECK(ready==1 && kind==wanted_kind && error==wanted_code && metadata==0 && body==0);
    CHECK(pcc_gui_protocol_response_take(owner, key, NULL, 0, NULL, 0, &kind, &error)==0);
    CHECK(kind==wanted_kind && error==wanted_code);
    CHECK(pcc_gui_protocol_response_take(owner, key, NULL, 0, NULL, 0, &kind, &error)==2);
}
static void worker(void (^action)(void)) {
    dispatch_group_t group=dispatch_group_create();
    dispatch_group_async(group,dispatch_get_global_queue(QOS_CLASS_DEFAULT,0),^{
        CHECK(![NSThread isMainThread]); action();
    });
    CHECK(dispatch_group_wait(group,dispatch_time(DISPATCH_TIME_NOW,5*NSEC_PER_SEC))==0);
}
static void owned_completion_cases(void) {
    int64_t owner = new_owner(), key;
    char url[] = "https://example.invalid/safe?q=%23";
    CHECK(pcc_gui_test_shell_open_external(owner,url,strlen(url),0,1,&key)==0);
    memset(url,'x',strlen(url));
    CHECK([fixture_url isEqualToString:@"https://example.invalid/safe?q=%23"] && fixture_activates==0);
    int64_t ready, kind=91, code=92, a=93,b=94;
    CHECK(pcc_gui_protocol_response_peek(owner,key,&ready,&kind,&code,&a,&b)==0);
    CHECK(ready==0 && kind==91 && code==92 && a==93 && b==94);
    int64_t success = key;
    worker(^{CHECK(pcc_gui_test_shell_finish(success,1)==0);});
    CHECK(pcc_gui_test_shell_finish(success,0)==2); take(owner,key,1,0);
    const char external[] = "pcc-private:opaque";
    CHECK(pcc_gui_test_shell_open_external(owner,external,sizeof(external)-1,1,1,&key)==0);
    CHECK(fixture_activates==1); int64_t failed=key;
    worker(^{CHECK(pcc_gui_test_shell_finish(failed,0)==0);}); take(owner,key,2,12);
    CHECK(pcc_gui_test_shell_open_external(owner,external,sizeof(external)-1,1,0,&key)==0);
    take(owner,key,2,11);
    CHECK(pcc_gui_test_shell_open_external(owner,external,sizeof(external)-1,1,1,&key)==0);
    CHECK(pcc_gui_protocol_cancel(owner,key)==0); take(owner,key,3,0);
    CHECK(pcc_gui_test_shell_finish(key,1)==0);
    CHECK(pcc_gui_test_shell_open_external(owner,external,sizeof(external)-1,1,1,&key)==0);
    CHECK(pcc_gui_protocol_retire(owner)==0);
    int64_t retired=key;
    worker(^{CHECK(pcc_gui_test_shell_finish(retired,1)==0);});
    CHECK(pcc_gui_test_shell_pending()==0);
}
static void argument_cases(void) {
    int64_t owner=new_owner(), key=93;
    CHECK(pcc_gui_shell_open_external(owner,NULL,0,0,&key)==0); take(owner,key,2,10);
    key=93;
    CHECK(pcc_gui_shell_open_external(owner,NULL,1,1,&key)==2 && key==93);
    CHECK(pcc_gui_shell_open_external(owner,"x",65537,1,&key)==6 && key==93);
    CHECK(pcc_gui_shell_open_external(owner,"a\0b",3,1,&key)==2 && key==93);
    CHECK(pcc_gui_shell_open_external(owner,"\xff",1,1,&key)==2 && key==93);
    CHECK(pcc_gui_shell_open_external(owner,NULL,0,2,&key)==2 && key==93);
    CHECK(pcc_gui_shell_open_external(owner,NULL,0,1,NULL)==2);
    worker(^{int64_t out=55;CHECK(pcc_gui_shell_open_external(owner,NULL,0,1,&out)==2 && out==55);
        CHECK(pcc_gui_shell_show_item_in_folder(owner,NULL,0)==2);});
    CHECK(pcc_gui_test_shell_show_item_in_folder(owner,"/tmp//x",7)==0 && [fixture_path isEqualToString:@"/tmp//x"]);
    CHECK(pcc_gui_test_shell_show_item_in_folder(owner,".",1)==0);
    char *cwd=realpath(".",NULL);CHECK(cwd && [fixture_path isEqualToString:[NSString stringWithUTF8String:cwd]]);free(cwd);
    CHECK(pcc_gui_test_shell_show_item_in_folder(owner,"not-existing-pcc-shell-356427",29)==0 && [fixture_path isEqualToString:@""]);
    int64_t first=0;
    CHECK(pcc_gui_protocol_submit(owner,"x",1,NULL,0,&first)==0);
    CHECK(pcc_gui_shell_open_external(owner,NULL,0,1,&key)==5 && key==93);
    CHECK(pcc_gui_protocol_cancel(owner,first)==0);take(owner,first,3,0);
    CHECK(pcc_gui_protocol_retire(owner)==0);
    CHECK(pcc_gui_test_shell_show_item_in_folder(owner,NULL,0)==2);
}
static void reentry_cases(void) {
    int64_t owner=new_owner(),out=98; __block int launched=0;
    CHECK(pcc_shell_open_with(owner,"https://example.invalid/",24,1,&out,^BOOL(NSURL *v) {
        CHECK(pcc_gui_protocol_retire(owner)==0);return YES;
    },^(NSURL *v,BOOL active,PccShellCompletion done){launched++;})==2 && out==98 && launched==0);
    owner=new_owner();
    CHECK(pcc_shell_open_with(owner,"pcc-test:a",10,0,&out,^BOOL(NSURL *v){return YES;},
        ^(NSURL *v,BOOL active,PccShellCompletion done){
            done(YES);done(NO);@throw [NSException exceptionWithName:@"after-completion" reason:nil userInfo:nil];
        })==0);
    take(owner,out,1,0);
    CHECK(pcc_shell_open_with(owner,"pcc-test:a",10,0,&out,^BOOL(NSURL *v){
        @throw [NSException exceptionWithName:@"lookup" reason:nil userInfo:nil];
    },^(NSURL *v,BOOL active,PccShellCompletion done){CHECK(0);})==0);
    take(owner,out,2,4);
    CHECK(pcc_gui_protocol_retire(owner)==0);
}

// Intercept the three system selectors in this test executable only. This
// exercises the public production functions without launching Finder or a URL.
static int found, calls;
static void (^workspace_done)(NSRunningApplication *, NSError *);
static NSURL *lookup(id self,SEL cmd,NSURL *url){
    fixture_url=[url.absoluteString copy];return found?[NSURL fileURLWithPath:@"/private/fake.app"]:nil;
}
static void launch(id self,SEL cmd,NSURL *url,NSWorkspaceOpenConfiguration *config,
                   void (^completion)(NSRunningApplication *,NSError *)){
    calls++;fixture_activates=config.activates;workspace_done=[completion copy];
}
static BOOL reveal(id self,SEL cmd,NSString *file,NSString *root){
    CHECK([root isEqualToString:@""]);fixture_path=[file copy];return NO;
}
static void production_selectors(void) {
    NSWorkspace *workspace=NSWorkspace.sharedWorkspace;
    Class cls=[workspace class];SEL a=@selector(URLForApplicationToOpenURL:),
        b=@selector(openURL:configuration:completionHandler:),c=@selector(selectFile:inFileViewerRootedAtPath:);
    Method am=class_getInstanceMethod(cls,a),bm=class_getInstanceMethod(cls,b),cm=class_getInstanceMethod(cls,c);
    CHECK(am && bm && cm);
    IMP old_a=method_setImplementation(am,(IMP)lookup),old_b=method_setImplementation(bm,(IMP)launch),
        old_c=method_setImplementation(cm,(IMP)reveal);
    @try {
        int64_t owner=new_owner(),key; const char *url="https://example.invalid/%20a";
        found=0;CHECK(pcc_gui_shell_open_external(owner,url,strlen(url),1,&key)==0);take(owner,key,2,11);CHECK(calls==0);
        found=1;CHECK(pcc_gui_shell_open_external(owner,url,strlen(url),0,&key)==0);
        CHECK(calls==1 && fixture_activates==0 && [fixture_url isEqualToString:@"https://example.invalid/%20a"]);
        worker(^{workspace_done(nil,nil);}); take(owner,key,1,0);workspace_done=nil;
        CHECK(pcc_gui_shell_open_external(owner,url,strlen(url),1,&key)==0);
        CHECK(calls==2 && fixture_activates==1);
        worker(^{workspace_done(nil,[NSError errorWithDomain:@"injected" code:37 userInfo:nil]);});
        take(owner,key,2,12);workspace_done=nil;
        CHECK(pcc_gui_shell_show_item_in_folder(owner,"/private/xyz",12)==0 && [fixture_path isEqualToString:@"/private/xyz"]);
        CHECK(pcc_gui_protocol_retire(owner)==0);
    } @finally {method_setImplementation(am,old_a);method_setImplementation(bm,old_b);method_setImplementation(cm,old_c);}
}
int main(void){
    @autoreleasepool {
        owned_completion_cases();argument_cases();reentry_cases();production_selectors();
        int64_t a,b,c;CHECK(pcc_gui_protocol_live_counts(&a,&b,&c)==0 && !a && !b && !c);
        CHECK(pcc_gui_test_shell_pending()==0);
        puts("PCC_NATIVE_SHELL_OK selectors=3 async=1 success=1 missing=1 failure=1 cancel=1 retire=1 reentry=1 counts=0 external_launches=0");
    }
    return 0;
}
#endif
