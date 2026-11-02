#import <AppKit/AppKit.h>
#include "../../pcc_gui/native/pcc_gui_clipboard.h"
#include <pthread.h>
#include <stdio.h>
#include <string.h>

typedef struct { int64_t key, snapshot; int ok; } Worker;
static void *off_main(void *raw) {
  Worker *w=raw;int64_t a=-7,b=-9;char byte='!';
  w->ok=pcc_gui_clipboard_open_general(&a)==2 && a==-7 &&
    pcc_gui_clipboard_open_named("private",7,&a)==2 && a==-7 &&
    pcc_gui_clipboard_write_utf8(w->key,"x",1)==2 &&
    pcc_gui_clipboard_clear(w->key)==2 &&
    pcc_gui_clipboard_snapshot(w->key,&a,&b)==2 && a==-7 && b==-9 &&
    pcc_gui_clipboard_snapshot_copy(w->snapshot,&byte,1)==2 && byte=='!' &&
    pcc_gui_clipboard_snapshot_release(w->snapshot)==2 &&
    pcc_gui_clipboard_close(w->key)==2 &&
    pcc_gui_clipboard_live_counts(&a,&b)==2 && a==-7 && b==-9;
  return NULL;
}
static int same(NSPasteboard *board,const void *bytes,NSUInteger size) {
  NSData *actual=[[board stringForType:NSPasteboardTypeString] dataUsingEncoding:NSUTF8StringEncoding];
  return actual!=nil && actual.length==size && (!size||memcmp(actual.bytes,bytes,size)==0);
}
int main(void) {
 @autoreleasepool {
  const unsigned char text[]={'A',0,'B',0xc3,0xa9,0xf0,0x9f,0x98,0x80};
  const unsigned char bad[]={0xc0,0xaf};
  int64_t out=-7,length=-9,boards=-7,snapshots=-9;
  if(pcc_gui_clipboard_open_named(NULL,1,&out)!=2||out!=-7) return 1;
  if(pcc_gui_clipboard_open_named(bad,2,&out)!=3||out!=-7) return 2;
  NSData *general=[NSPasteboardNameGeneral dataUsingEncoding:NSUTF8StringEncoding];
  if(pcc_gui_clipboard_open_named(general.bytes,(int64_t)general.length,&out)!=2||out!=-7) return 3;
  for(int cycle=0;cycle<32;cycle++){
   @autoreleasepool {
    NSString *name=[@"org.pcc.clipboard.test." stringByAppendingString:NSUUID.UUID.UUIDString];
    NSData *nameBytes=[name dataUsingEncoding:NSUTF8StringEncoding];
    NSPasteboard *board=[NSPasteboard pasteboardWithName:name];
    int64_t key=0,copy=0;
    if(pcc_gui_clipboard_open_named(nameBytes.bytes,(int64_t)nameBytes.length,&key)||key<=0) return 4;
    if(pcc_gui_clipboard_write_utf8(key,text,sizeof(text))||!same(board,text,sizeof(text))) return 5;
    if(pcc_gui_clipboard_snapshot(key,&copy,&length)||length!=sizeof(text)||copy<=0) return 6;
    if(pcc_gui_clipboard_snapshot(key,&out,&out)!=2||out!=-7) return 7;
    Worker worker={key,copy,0};pthread_t thread;
    if(pthread_create(&thread,NULL,off_main,&worker)||pthread_join(thread,NULL)||!worker.ok) return 8;
    if(pcc_gui_clipboard_write_utf8(key,bad,sizeof(bad))!=3||!same(board,text,sizeof(text))) return 9;
    if(pcc_gui_clipboard_write_utf8(key,"later",5)||!same(board,"later",5)) return 10;
    unsigned char bytes[sizeof(text)+2];memset(bytes,0xa5,sizeof(bytes));
    if(pcc_gui_clipboard_snapshot_copy(copy,bytes+1,sizeof(text)-1)!=5) return 11;
    for(NSUInteger i=0;i<sizeof(bytes);i++)if(bytes[i]!=0xa5)return 12;
    if(pcc_gui_clipboard_close(key)||pcc_gui_clipboard_close(key)!=2) return 13;
    if(pcc_gui_clipboard_snapshot_copy(copy,bytes+1,sizeof(text))||memcmp(bytes+1,text,sizeof(text))||bytes[0]!=0xa5||bytes[sizeof(bytes)-1]!=0xa5) return 14;
    if(pcc_gui_clipboard_snapshot_release(copy)||pcc_gui_clipboard_snapshot_release(copy)!=2) return 15;
    if(pcc_gui_clipboard_write_utf8(key,"bad",3)!=2||!same(board,"later",5)) return 16;
    if(pcc_gui_clipboard_open_named(nameBytes.bytes,(int64_t)nameBytes.length,&key)) return 17;
    if(pcc_gui_clipboard_clear(key)||pcc_gui_clipboard_snapshot(key,&copy,&length)||length!=0) return 18;
    if(pcc_gui_clipboard_snapshot_copy(copy,NULL,0)||pcc_gui_clipboard_snapshot_release(copy)) return 19;
    if(pcc_gui_clipboard_write_utf8(key,NULL,0)||!same(board,"",0)) return 20;
    if(pcc_gui_clipboard_close(key)||pcc_gui_clipboard_live_counts(&boards,&snapshots)||boards!=0||snapshots!=0) return 21;
    [board releaseGlobally];
   }
  }
  puts("PCC_NATIVE_CLIPBOARD_OK cycles=32 snapshots=64 private_only=1 worker_rejected=1 stale_rejected=1");
 }
 return 0;
}
