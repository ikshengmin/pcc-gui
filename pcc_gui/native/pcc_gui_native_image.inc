// Native images contain copied pixels/platform objects, never source callbacks.
#include "pcc_gui_native_image.h"
#include <limits.h>
@interface PccGuiNativeImage : NSObject
@property(nonatomic,strong) NSImage *native;
@property(nonatomic,strong) NSData *backing;
@property(nonatomic) int64_t key,width,height,scale;
@end
@implementation PccGuiNativeImage
@end
static NSMutableDictionary<NSNumber *,PccGuiNativeImage *> *pcc_native_images;
static int64_t pcc_native_image_next=1;
static BOOL pcc_native_image_output(int64_t *out){return out&&((uintptr_t)out%_Alignof(int64_t))==0;}
static PccGuiNativeImage *pcc_native_image_get(int64_t key){return key>0?pcc_native_images[@(key)]:nil;}
static int64_t pcc_native_image_publish(NSImage *image,NSData *backing,int64_t width,int64_t height,int64_t scale,int64_t *out){
 if(pcc_native_image_next==INT64_MAX||pcc_native_images.count>=4096)return 6;
 @try{PccGuiNativeImage *value=[PccGuiNativeImage new];if(!value)return 4;if(!pcc_native_images)pcc_native_images=[NSMutableDictionary new];if(!pcc_native_images)return 4;
 value.native=image;value.backing=backing;value.width=width;value.height=height;value.scale=scale;value.key=pcc_native_image_next++;pcc_native_images[@(value.key)]=value;*out=value.key;return 0;}@catch(NSException *exception){return 4;}
}
int64_t pcc_gui_native_image_empty(int64_t *out){if(![NSThread isMainThread]||!pcc_native_image_output(out))return 2;return pcc_native_image_publish(nil,nil,0,0,1,out);}
int64_t pcc_gui_native_image_rgba(const void *data,int64_t length,int64_t width,int64_t height,int64_t stride,int64_t scale,int64_t *out){
 if(![NSThread isMainThread]||!pcc_native_image_output(out)||!data||width<=0||height<=0||scale<1||scale>8||length<0||stride<0)return 2;
 if(width>4096||height>4096||stride>67108864||length>67108864)return 6;
 if(stride<width*4||height>length/stride)return 2;
 @autoreleasepool{@try{
  NSData *copy=[NSData dataWithBytes:data length:(NSUInteger)(stride*height)];if(!copy)return 4;
  CGDataProviderRef provider=CGDataProviderCreateWithCFData((__bridge CFDataRef)copy);CGColorSpaceRef color=CGColorSpaceCreateWithName(kCGColorSpaceSRGB);
  if(!provider||!color){if(provider)CGDataProviderRelease(provider);if(color)CGColorSpaceRelease(color);return 4;}
  CGImageRef cg=CGImageCreate((size_t)width,(size_t)height,8,32,(size_t)stride,color,kCGBitmapByteOrder32Big|kCGImageAlphaLast,provider,NULL,NO,kCGRenderingIntentDefault);
  CGDataProviderRelease(provider);CGColorSpaceRelease(color);if(!cg)return 4;
  NSImage *image=nil;@try{image=[[NSImage alloc]initWithCGImage:cg size:NSMakeSize((CGFloat)width/(CGFloat)scale,(CGFloat)height/(CGFloat)scale)];}@finally{CGImageRelease(cg);}if(!image)return 4;
  return pcc_native_image_publish(image,copy,width,height,scale,out);
 }@catch(NSException *exception){return 4;}}
}
int64_t pcc_gui_native_image_path(const void *bytes,int64_t length,int64_t *out){
 if(![NSThread isMainThread]||!pcc_native_image_output(out)||length<0||(length&&!bytes))return 2;if(length>1048576)return 6;if(length&&memchr(bytes,0,(size_t)length))return 2;
 @autoreleasepool{@try{NSString *path=[[NSString alloc]initWithBytes:bytes length:(NSUInteger)length encoding:NSUTF8StringEncoding];if(!path)return 3;
 NSFileHandle *file=[NSFileHandle fileHandleForReadingAtPath:path];if(!file)return pcc_gui_native_image_empty(out);NSData *data=nil;@try{data=[file readDataOfLength:67108865];}@finally{[file closeFile];}if(!data)return 4;if(data.length>67108864)return 6;
 NSBitmapImageRep *bitmap=[[NSBitmapImageRep alloc]initWithData:data];if(!bitmap)return pcc_gui_native_image_empty(out);NSInteger width=bitmap.pixelsWide,height=bitmap.pixelsHigh;if(width<=0||height<=0)return pcc_gui_native_image_empty(out);if(width>4096||height>4096)return 6;
 NSImage *image=[[NSImage alloc]initWithSize:NSMakeSize(width,height)];[image addRepresentation:bitmap];if(!image)return 4;
 return pcc_native_image_publish(image,data,width,height,1,out);
 }@catch(NSException *exception){return 4;}}
}
int64_t pcc_gui_native_image_info(int64_t key,int64_t *width,int64_t *height,int64_t *scale,int64_t *is_template){
 int64_t *outs[4]={width,height,scale,is_template};if(![NSThread isMainThread])return 2;for(int i=0;i<4;i++){if(!pcc_native_image_output(outs[i]))return 2;for(int j=0;j<i;j++)if(outs[i]==outs[j])return 2;}
 PccGuiNativeImage *value=pcc_native_image_get(key);if(!value)return 2;*width=value.width;*height=value.height;*scale=value.scale;*is_template=value.native.template?1:0;return 0;
}
int64_t pcc_gui_native_image_template(int64_t key,int64_t flag){if(![NSThread isMainThread]||(flag!=0&&flag!=1))return 2;PccGuiNativeImage *value=pcc_native_image_get(key);if(!value)return 2;value.native.template=flag!=0;return 0;}
int64_t pcc_gui_native_image_release(int64_t key){if(![NSThread isMainThread]||!pcc_native_image_get(key))return 2;[pcc_native_images removeObjectForKey:@(key)];return 0;}
int64_t pcc_gui_native_image_live_count(int64_t *out){if(![NSThread isMainThread]||!pcc_native_image_output(out))return 2;*out=(int64_t)pcc_native_images.count;return 0;}
