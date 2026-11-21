// Principal-box presentation of translated DOM/CSS data; no source JS executes.
#include "pcc_gui_document.h"
#import <objc/runtime.h>
static NSString *pcc_doc_trim(NSString *s) {
  return
      [s stringByTrimmingCharactersInSet:NSCharacterSet
                                             .whitespaceAndNewlineCharacterSet];
}
static NSArray<NSString *> *pcc_doc_words(NSString *s) {
  NSMutableArray *out = [NSMutableArray array];
  NSInteger depth = 0;
  unichar quote = 0;
  NSUInteger start = 0;
  for (NSUInteger i = 0; i <= s.length; i++) {
    unichar c = i < s.length ? [s characterAtIndex:i] : ' ';
    if (quote) {
      if (c == quote)
        quote = 0;
    } else if (c == '\'' || c == '"')
      quote = c;
    else if (c == '(')
      depth++;
    else if (c == ')')
      depth--;
    if (!quote && depth == 0 &&
        [[NSCharacterSet whitespaceAndNewlineCharacterSet]
            characterIsMember:c]) {
      if (i > start)
        [out addObject:[s substringWithRange:NSMakeRange(start, i - start)]];
      start = i + 1;
    }
  }
  return out;
}
static NSString *pcc_doc_resolve(NSString *s, NSDictionary *vars, int depth) {
  if (depth > 32)
    return @"";
  NSRange at = [s rangeOfString:@"var("];
  if (at.location == NSNotFound)
    return s;
  NSUInteger start = at.location + 4, end = start;
  NSInteger level = 1;
  while (end < s.length && level) {
    unichar c = [s characterAtIndex:end];
    if (c == '(')
      level++;
    if (c == ')')
      level--;
    if (level)
      end++;
  }
  if (level)
    return s;
  NSString *body = [s substringWithRange:NSMakeRange(start, end - start)];
  NSRange comma = [body rangeOfString:@","];
  NSString *name = pcc_doc_trim(comma.location == NSNotFound
                                    ? body
                                    : [body substringToIndex:comma.location]);
  NSString *value = vars[name];
  if (!value)
    value = comma.location == NSNotFound
                ? @""
                : [body substringFromIndex:comma.location + 1];
  value = pcc_doc_resolve(value, vars, depth + 1);
  return pcc_doc_resolve(
      [s stringByReplacingCharactersInRange:NSMakeRange(at.location,
                                                        end - at.location + 1)
                                 withString:value],
      vars, depth + 1);
}
static CGFloat pcc_doc_length(NSString *s, CGFloat basis, CGFloat font,
                              CGFloat fallback) {
  if (!s.length || [s isEqual:@"auto"] || [s isEqual:@"none"] ||
      [s isEqual:@"inherit"])
    return fallback;
  if ([s hasSuffix:@"% "])
    s = pcc_doc_trim(s);
  if ([s hasSuffix:@"%"])
    return s.doubleValue * basis / 100;
  if ([s hasSuffix:@"rem"])
    return s.doubleValue * 16;
  if ([s hasSuffix:@"em"])
    return s.doubleValue * font;
  if ([s hasPrefix:@"calc("]) {
    NSString *body = [s substringWithRange:NSMakeRange(5, s.length - 6)];
    NSArray *parts = pcc_doc_words(body);
    CGFloat n = 0;
    int sign = 1;
    for (NSString *part in parts) {
      if ([part isEqual:@"+"]) {
        sign = 1;
        continue;
      }
      if ([part isEqual:@"-"]) {
        sign = -1;
        continue;
      }
      n += sign * pcc_doc_length(part, basis, font, 0);
    }
    return n;
  }
  NSScanner *scan = [NSScanner scannerWithString:s];
  double v;
  if (![scan scanDouble:&v])
    return fallback;
  return v;
}
static NSColor *pcc_doc_color(NSString *s) {
  s = pcc_doc_trim(s ?: @"");
  if ([s isEqual:@"transparent"])
    return NSColor.clearColor;
  if ([s isEqual:@"white"])
    return NSColor.whiteColor;
  if ([s isEqual:@"black"])
    return NSColor.blackColor;
  if ([s hasPrefix:@"#"]) {
    NSString *h = [s substringFromIndex:1];
    unsigned long long n = 0;
    [[NSScanner scannerWithString:h] scanHexLongLong:&n];
    if (h.length == 3 || h.length == 4) {
      CGFloat r = ((n >> (h.length == 4 ? 12 : 8)) & 15) / 15.0,
              g = ((n >> (h.length == 4 ? 8 : 4)) & 15) / 15.0,
              b = ((n >> (h.length == 4 ? 4 : 0)) & 15) / 15.0,
              a = h.length == 4 ? (n & 15) / 15.0 : 1;
      return [NSColor colorWithSRGBRed:r green:g blue:b alpha:a];
    }
    if (h.length == 6 || h.length == 8) {
      if (h.length == 6)
        n = (n << 8) | 255;
      return [NSColor colorWithSRGBRed:((n >> 24) & 255) / 255.0
                                 green:((n >> 16) & 255) / 255.0
                                  blue:((n >> 8) & 255) / 255.0
                                 alpha:(n & 255) / 255.0];
    }
  }
  if ([s hasPrefix:@"color-mix("]) {
    NSRange rgb = [s rangeOfString:@"rgb("];
    if (rgb.location != NSNotFound) {
      NSRange end =
          [s rangeOfString:@")"
                   options:0
                     range:NSMakeRange(rgb.location, s.length - rgb.location)];
      if (end.location != NSNotFound) {
        NSColor *base = pcc_doc_color([s
            substringWithRange:NSMakeRange(rgb.location,
                                           end.location - rgb.location + 1)]);
        NSString *tail = pcc_doc_trim([s substringFromIndex:end.location + 1]);
        return [base colorWithAlphaComponent:tail.doubleValue / 100];
      }
    }
  }
  if ([s hasPrefix:@"rgb"]) {
    NSRange a = [s rangeOfString:@"("],
            z = [s rangeOfString:@")" options:NSBackwardsSearch];
    if (a.location != NSNotFound && z.location > a.location) {
      NSString *body =
          [s substringWithRange:NSMakeRange(a.location + 1,
                                            z.location - a.location - 1)];
      body = [[body stringByReplacingOccurrencesOfString:@"," withString:@" "]
          stringByReplacingOccurrencesOfString:@"/"
                                    withString:@" "];
      NSArray *v = pcc_doc_words(body);
      if (v.count >= 3)
        return [NSColor colorWithSRGBRed:[v[0] doubleValue] / 255
                                   green:[v[1] doubleValue] / 255
                                    blue:[v[2] doubleValue] / 255
                                   alpha:v.count > 3 ? [v[3] doubleValue] : 1];
    }
  }
  return NSColor.clearColor;
}
@interface PCCDocumentNode : NSObject
@property NSDictionary *source;
@property NSMutableDictionary *style;
@property NSMutableArray<PCCDocumentNode *> *children;
@property NSRect frame;
@property BOOL hidden;
@property CGFloat fontSize, lineHeight, opacity;
@end
@implementation PCCDocumentNode
@end
@interface PCCDocumentImage : NSObject
@property NSImage *image;
@property NSString *aspect;
@end
@implementation PCCDocumentImage
@end
@interface PCCSvgRoot : NSObject <NSXMLParserDelegate>
@property NSString *aspect;
@end
@implementation PCCSvgRoot
- (void)parser:(NSXMLParser *)parser
    didStartElement:(NSString *)name
       namespaceURI:(NSString *)uri
      qualifiedName:(NSString *)qualified
         attributes:(NSDictionary<NSString *, NSString *> *)attributes {
  if ([name isEqual:@"svg"])
    self.aspect = attributes[@"preserveAspectRatio"] ?: @"xMidYMid meet";
  [parser abortParsing];
}
@end
static NSString *pcc_doc_svg_aspect(NSData *encoded) {
  NSString *text =
      [[NSString alloc] initWithData:encoded encoding:NSUTF8StringEncoding];
  if (!text ||
      [text rangeOfString:@"<!DOCTYPE" options:NSCaseInsensitiveSearch]
              .location != NSNotFound ||
      [text rangeOfString:@"<!ENTITY" options:NSCaseInsensitiveSearch]
              .location != NSNotFound)
    return nil;
  PCCSvgRoot *root = [PCCSvgRoot new];
  NSXMLParser *parser = [[NSXMLParser alloc] initWithData:encoded];
  parser.shouldResolveExternalEntities = NO;
  parser.delegate = root;
  [parser parse];
  return root.aspect;
}
@interface PCCDocumentView : NSView
@property NSArray<PCCDocumentNode *> *nodes;
@property NSDictionary *images;
@property NSString *status;
@property NSMutableIndexSet *enabledButtons;
@property NSInteger pressedButton;
@property NSInteger pendingButton;
@property CGFloat sourceWidth, sourceHeight;
@end
static NSFont *pcc_doc_font(PCCDocumentNode *n) {
  CGFloat size = n.fontSize > 0 ? n.fontSize : 16;
  NSString *family = n.style[@"font-family"] ?: @"";
  NSString *first =
      pcc_doc_trim([[family componentsSeparatedByString:@","] firstObject]);
  first =
      [first stringByTrimmingCharactersInSet:
                 [NSCharacterSet characterSetWithCharactersInString:@"\"'"]];
  CGFloat weight = [n.style[@"font-weight"] doubleValue];
  if (!weight)
    weight = 400;
  NSFont *font = nil;
  if (first.length && ![first hasPrefix:@"-"] && ![first isEqual:@"inherit"] &&
      [[NSFontManager sharedFontManager].availableFontFamilies
          containsObject:first]) {
    NSFontDescriptor *descriptor =
        [NSFontDescriptor fontDescriptorWithFontAttributes:@{
          NSFontFamilyAttribute : first,
          NSFontTraitsAttribute : @{
            NSFontWeightTrait : @(weight <= 300   ? NSFontWeightLight
                                  : weight >= 600 ? NSFontWeightSemibold
                                  : weight >= 500 ? NSFontWeightMedium
                                                  : NSFontWeightRegular)
          }
        }];
    font = [NSFont fontWithDescriptor:descriptor size:size];
  }
  if (!font)
    font = [NSFont systemFontOfSize:size
                             weight:weight <= 300   ? NSFontWeightLight
                                    : weight >= 600 ? NSFontWeightSemibold
                                    : weight >= 500 ? NSFontWeightMedium
                                                    : NSFontWeightRegular];
  return font;
}
static BOOL pcc_doc_inline(PCCDocumentNode *n) {
  NSString *tag = n.source[@"tag"], *display = n.style[@"display"];
  return
      [n.source[@"name"] isEqual:@"#text"] || [display isEqual:@"inline"] ||
      (!display && [@[ @"span", @"em", @"strong", @"a", @"b", @"i", @"label" ]
                       containsObject:tag]);
}
static BOOL pcc_doc_fully_clipped(PCCDocumentNode *node) {
  return [node.style[@"clip-path"] isEqual:@"inset(50%)"];
}
static void pcc_doc_runs(PCCDocumentNode *n, NSMutableAttributedString *text) {
  if (n.hidden || pcc_doc_fully_clipped(n))
    return;
  NSString *value = n.source[@"text"];
  if ([n.source[@"name"] isEqual:@"#text"] && value.length) {
    value = [value
        stringByReplacingOccurrencesOfString:@"\\s+"
                                  withString:@" "
                                     options:NSRegularExpressionSearch
                                       range:NSMakeRange(0, value.length)];
    NSColor *color = pcc_doc_color(n.style[@"color"] ?: @"black");
    [text appendAttributedString:
              [[NSAttributedString alloc]
                  initWithString:value
                      attributes:@{
                        NSFontAttributeName : pcc_doc_font(n),
                        NSForegroundColorAttributeName : [color
                            colorWithAlphaComponent:color.alphaComponent *
                                                    n.opacity]
                      }]];
  }
  for (PCCDocumentNode *child in n.children)
    pcc_doc_runs(child, text);
}
static BOOL pcc_doc_textbox(PCCDocumentNode *n) {
  BOOL some = NO;
  for (PCCDocumentNode *c in n.children) {
    if (c.hidden)
      continue;
    if (!pcc_doc_inline(c))
      return NO;
    some = YES;
  }
  return some || [n.source[@"name"] isEqual:@"#text"];
}
static CGFloat pcc_doc_edge(PCCDocumentNode *n, NSString *kind, NSString *side,
                            CGFloat basis) {
  return pcc_doc_length(
      n.style[[NSString stringWithFormat:@"%@-%@", kind, side]], basis,
      n.fontSize, 0);
}
static NSSize pcc_doc_measure(PCCDocumentNode *n, CGFloat width) {
  if (n.hidden)
    return NSZeroSize;
  CGFloat pl = pcc_doc_edge(n, @"padding", @"left", width),
          pr = pcc_doc_edge(n, @"padding", @"right", width),
          pt = pcc_doc_edge(n, @"padding", @"top", width),
          pb = pcc_doc_edge(n, @"padding", @"bottom", width);
  CGFloat w = 0, h = 0;
  if ([n.source[@"tag"] isEqual:@"img"]) {
    w = [n.source[@"attributes"][@"width"] doubleValue];
    h = [n.source[@"attributes"][@"height"] doubleValue];
  } else if (pcc_doc_textbox(n)) {
    NSMutableAttributedString *text =
        [[NSMutableAttributedString alloc] initWithString:@""];
    pcc_doc_runs(n, text);
    w = text.size.width;
    h = n.lineHeight;
  } else {
    for (PCCDocumentNode *c in n.children) {
      if (c.hidden)
        continue;
      NSSize size = pcc_doc_measure(c, MAX(0, width - pl - pr));
      w = MAX(w, size.width);
      h += size.height + pcc_doc_edge(c, @"margin", @"top", width) +
           pcc_doc_edge(c, @"margin", @"bottom", width);
    }
  }
  w = pcc_doc_length(n.style[@"width"], width, n.fontSize, w + pl + pr);
  h = pcc_doc_length(n.style[@"height"], 0, n.fontSize, h + pt + pb);
  return NSMakeSize(MAX(0, w), MAX(0, h));
}
static NSRect pcc_doc_inner(PCCDocumentNode *n) {
  CGFloat pl = pcc_doc_edge(n, @"padding", @"left", n.frame.size.width),
          pr = pcc_doc_edge(n, @"padding", @"right", n.frame.size.width),
          pt = pcc_doc_edge(n, @"padding", @"top", n.frame.size.width),
          pb = pcc_doc_edge(n, @"padding", @"bottom", n.frame.size.width);
  return NSMakeRect(n.frame.origin.x + pl, n.frame.origin.y + pt,
                    MAX(0, n.frame.size.width - pl - pr),
                    MAX(0, n.frame.size.height - pt - pb));
}
static void pcc_doc_layout(PCCDocumentNode *n, NSRect frame) {
  n.frame = frame;
  if (n.hidden || pcc_doc_textbox(n) || [n.source[@"tag"] isEqual:@"img"])
    return;
  NSRect box = pcc_doc_inner(n);
  NSString *display = n.style[@"display"] ?: @"block";
  NSMutableArray *children = [NSMutableArray array];
  for (PCCDocumentNode *c in n.children)
    if (!c.hidden && (![c.source[@"name"] isEqual:@"#text"] ||
                      pcc_doc_trim(c.source[@"text"]).length))
      [children addObject:c];
  if ([display isEqual:@"grid"]) {
    NSArray *tracks = pcc_doc_words(n.style[@"grid-template-rows"] ?: @"1fr");
    NSMutableArray *sizes = [NSMutableArray array];
    CGFloat fixed = 0;
    NSInteger flexible = 0;
    for (NSString *track in tracks) {
      BOOL flex = [track containsString:@"fr"];
      CGFloat size =
          flex ? 0 : pcc_doc_length(track, box.size.height, n.fontSize, 0);
      [sizes addObject:@(size)];
      fixed += size;
      if (flex)
        flexible++;
    }
    if (!sizes.count)
      [sizes addObject:@(box.size.height)];
    for (NSUInteger i = 0; i < tracks.count; i++)
      if ([tracks[i] containsString:@"fr"])
        sizes[i] = @(MAX(0, box.size.height - fixed) / MAX(1, flexible));
    NSInteger automatic = 0;
    for (PCCDocumentNode *c in children) {
      NSInteger row = [c.style[@"grid-row"] integerValue] - 1;
      if (row < 0)
        row = automatic++;
      row = MAX(0, MIN(row, (NSInteger)sizes.count - 1));
      CGFloat y = box.origin.y;
      for (NSInteger j = 0; j < row; j++)
        y += [sizes[j] doubleValue];
      CGFloat rh = [sizes[row] doubleValue];
      NSSize natural = pcc_doc_measure(c, box.size.width);
      BOOL center = [n.style[@"justify-items"] isEqual:@"center"];
      CGFloat w = pcc_doc_length(c.style[@"width"], box.size.width, c.fontSize,
                                 center ? MIN(natural.width, box.size.width)
                                        : box.size.width);
      BOOL stretch = [c.style[@"align-self"] isEqual:@"stretch"];
      CGFloat h = pcc_doc_length(c.style[@"height"], rh, c.fontSize,
                                 stretch ? rh : natural.height);
      CGFloat x = box.origin.x + (center ? (box.size.width - w) / 2 : 0);
      if ([n.style[@"align-items"] isEqual:@"center"] && !stretch)
        y += (rh - h) / 2;
      pcc_doc_layout(c, NSMakeRect(x, y, w, h));
    }
    return;
  }
  if ([display isEqual:@"flex"] || [display isEqual:@"inline-flex"]) {
    BOOL column = [n.style[@"flex-direction"] isEqual:@"column"];
    CGFloat axis = column ? box.size.height : box.size.width,
            gap = pcc_doc_length(n.style[@"gap"], axis, n.fontSize, 0),
            fixed = gap * MAX(0, (NSInteger)children.count - 1), grow = 0;
    NSMutableArray *bases = [NSMutableArray array],
                   *grows = [NSMutableArray array];
    for (PCCDocumentNode *c in children) {
      NSSize natural = pcc_doc_measure(c, box.size.width);
      NSArray *flex = pcc_doc_words(c.style[@"flex"] ?: @"");
      CGFloat g = flex.count ? [flex[0] doubleValue] : 0;
      NSString *basis = flex.count > 2 ? flex[2] : nil;
      CGFloat size = pcc_doc_length(basis, axis, c.fontSize, NAN);
      if (isnan(size))
        size = pcc_doc_length(c.style[column ? @"height" : @"width"], axis,
                              c.fontSize,
                              g > 0    ? 0
                              : column ? natural.height
                                       : natural.width);
      [bases addObject:@(size)];
      [grows addObject:@(g)];
      fixed += size;
      grow += g;
    }
    CGFloat offset = 0;
    if (grow == 0 && [n.style[@"justify-content"] isEqual:@"center"])
      offset = MAX(0, axis - fixed) / 2;
    for (NSUInteger i = 0; i < children.count; i++) {
      PCCDocumentNode *c = children[i];
      CGFloat size =
          [bases[i] doubleValue] +
          (grow > 0 ? MAX(0, axis - fixed) * [grows[i] doubleValue] / grow : 0);
      NSSize natural = pcc_doc_measure(c, box.size.width);
      BOOL center = [n.style[@"align-items"] isEqual:@"center"];
      CGFloat cross = column ? box.size.width : box.size.height;
      CGFloat cs = pcc_doc_length(
          c.style[column ? @"width" : @"height"], cross, c.fontSize,
          center ? (column ? natural.width : natural.height) : cross);
      NSRect child =
          column ? NSMakeRect(box.origin.x + (center ? (cross - cs) / 2 : 0),
                              box.origin.y + offset, cs, size)
                 : NSMakeRect(box.origin.x + offset,
                              box.origin.y + (center ? (cross - cs) / 2 : 0),
                              size, cs);
      pcc_doc_layout(c, child);
      offset += size + gap;
    }
    return;
  }
  CGFloat y = box.origin.y;
  for (PCCDocumentNode *c in children) {
    NSSize natural = pcc_doc_measure(c, box.size.width);
    CGFloat top = pcc_doc_edge(c, @"margin", @"top", box.size.width),
            bottom = pcc_doc_edge(c, @"margin", @"bottom", box.size.width);
    CGFloat w = pcc_doc_length(c.style[@"width"], box.size.width, c.fontSize,
                               box.size.width),
            h = pcc_doc_length(c.style[@"height"], box.size.height, c.fontSize,
                               natural.height);
    if ([c.source[@"tag"] isEqual:@"html"] ||
        [c.source[@"tag"] isEqual:@"body"])
      h = box.size.height;
    pcc_doc_layout(c, NSMakeRect(box.origin.x, y + top, w, h));
    y += top + h + bottom;
  }
}
static void pcc_doc_styles(PCCDocumentNode *n, PCCDocumentNode *parent,
                           NSUInteger depth) {
  if (depth > 128) {
    n.hidden = YES;
    return;
  }
  NSMutableDictionary *style = [NSMutableDictionary dictionary];
  if (parent) {
    for (NSString *key in parent.style)
      if ([key hasPrefix:@"--"] || [@[
            @"font-size", @"font-family", @"font-weight", @"font-style",
            @"line-height", @"color", @"text-align", @"white-space",
            @"letter-spacing"
          ] containsObject:key])
        style[key] = parent.style[key];
  }
  NSArray *original = n.source[@"styles"];
  NSMutableArray<NSNumber *> *indices = [NSMutableArray array];
  for (NSUInteger i = 0; i < original.count; i++)
    [indices addObject:@(i)];
  [indices
      sortUsingComparator:^NSComparisonResult(NSNumber *left, NSNumber *right) {
        NSDictionary *a = original[left.unsignedIntegerValue],
                     *b = original[right.unsignedIntegerValue];
        for (NSString *key in @[ @"important", @"ids", @"classes", @"types" ]) {
          NSInteger x = [a[key] integerValue], y = [b[key] integerValue];
          if (x != y)
            return x < y ? NSOrderedAscending : NSOrderedDescending;
        }
        return [left compare:right];
      }];
  NSMutableArray *rows = [NSMutableArray array];
  for (NSNumber *index in indices)
    [rows addObject:original[index.unsignedIntegerValue]];
  for (NSDictionary *row in rows)
    if ([row[@"name"] hasPrefix:@"--"])
      style[row[@"name"]] = row[@"value"];
  for (NSDictionary *row in rows) {
    NSString *name = row[@"name"],
             *value = pcc_doc_resolve(row[@"value"], style, 0);
    if ([name hasPrefix:@"--"])
      continue;
    if ([value isEqual:@"inherit"]) {
      if (parent.style[name])
        style[name] = parent.style[name];
      continue;
    }
    style[name] = value;
    if ([name isEqual:@"padding"] || [name isEqual:@"margin"]) {
      NSArray *v = pcc_doc_words(value);
      if (v.count && v.count <= 4) {
        NSArray *sides = @[ @"top", @"right", @"bottom", @"left" ];
        NSUInteger indices[4] = {0, v.count > 1 ? 1 : 0, v.count > 2 ? 2 : 0,
                                 v.count > 3   ? 3
                                 : v.count > 1 ? 1
                                               : 0};
        for (int j = 0; j < 4; j++)
          style[[NSString stringWithFormat:@"%@-%@", name, sides[j]]] =
              v[indices[j]];
      }
    }
    if ([name isEqual:@"border"]) {
      NSArray *v = pcc_doc_words(value);
      if (v.count > 0)
        style[@"border-width"] = v[0];
      if (v.count > 1)
        style[@"border-style"] = v[1];
      if (v.count > 2)
        style[@"border-color"] = v[2];
    }
  }
  n.style = style;
  NSString *tag = n.source[@"tag"];
  n.hidden = parent.hidden || [style[@"display"] isEqual:@"none"] ||
             [@[ @"head", @"script", @"style", @"link", @"meta", @"title" ]
                 containsObject:tag];
  n.fontSize = pcc_doc_length(
      style[@"font-size"], parent ? parent.fontSize : 16,
      parent ? parent.fontSize : 16, parent ? parent.fontSize : 16);
  n.lineHeight = pcc_doc_length(style[@"line-height"], n.fontSize, n.fontSize,
                                parent ? parent.lineHeight : n.fontSize * 1.2);
  if (style[@"font-size"] && !style[@"line-height"])
    n.lineHeight = n.fontSize * 1.2;
  n.opacity = (parent ? parent.opacity : 1) *
              (style[@"opacity"] ? [style[@"opacity"] doubleValue] : 1);
  for (PCCDocumentNode *c in n.children)
    pcc_doc_styles(c, n, depth + 1);
}
static NSData *pcc_doc_hex(NSString *hex) {
  if (![hex isKindOfClass:NSString.class] || hex.length % 2 ||
      hex.length > 32 * 1024 * 1024)
    return nil;
  NSMutableData *data = [NSMutableData dataWithLength:hex.length / 2];
  uint8_t *out = data.mutableBytes;
  for (NSUInteger i = 0; i < data.length; i++) {
    unsigned v = 0;
    if (![[NSScanner
            scannerWithString:[hex substringWithRange:NSMakeRange(i * 2, 2)]]
            scanHexInt:&v])
      return nil;
    out[i] = (uint8_t)v;
  }
  return data;
}
static void pcc_doc_draw(PCCDocumentNode *n, NSDictionary *images) {
  if (n.hidden || pcc_doc_fully_clipped(n) || NSIsEmptyRect(n.frame))
    return;
  [NSGraphicsContext saveGraphicsState];
  CGFloat radius = pcc_doc_length(n.style[@"border-radius"], n.frame.size.width,
                                  n.fontSize, 0);
  NSBezierPath *shape = [NSBezierPath bezierPathWithRoundedRect:n.frame
                                                        xRadius:radius
                                                        yRadius:radius];
  NSColor *background =
      pcc_doc_color(n.style[@"background-color"] ?: n.style[@"background"]);
  [[background colorWithAlphaComponent:background.alphaComponent * n.opacity]
      setFill];
  [shape fill];
  CGFloat border = pcc_doc_length(n.style[@"border-width"], n.frame.size.width,
                                  n.fontSize, 0);
  if (border > 0) {
    NSColor *color = pcc_doc_color(n.style[@"border-color"] ?: @"transparent");
    [[color colorWithAlphaComponent:color.alphaComponent * n.opacity]
        setStroke];
    NSBezierPath *line = [NSBezierPath
        bezierPathWithRoundedRect:NSInsetRect(n.frame, border / 2, border / 2)
                          xRadius:MAX(0, radius - border / 2)
                          yRadius:MAX(0, radius - border / 2)];
    line.lineWidth = border;
    [line stroke];
  }
  if ([n.source[@"tag"] isEqual:@"img"]) {
    PCCDocumentImage *asset = images[n.source[@"attributes"][@"src"]];
    NSImage *image = asset.image;
    if (image) {
      NSRect rect = n.frame;
      if (asset.aspect && ![asset.aspect isEqual:@"none"]) {
        CGFloat sx = rect.size.width / image.size.width,
                sy = rect.size.height / image.size.height,
                scale = [asset.aspect containsString:@"slice"] ? MAX(sx, sy)
                                                               : MIN(sx, sy);
        NSSize size =
            NSMakeSize(image.size.width * scale, image.size.height * scale);
        CGFloat x = [asset.aspect containsString:@"xMin"] ? 0
                    : [asset.aspect containsString:@"xMax"]
                        ? rect.size.width - size.width
                        : (rect.size.width - size.width) / 2;
        CGFloat y = [asset.aspect containsString:@"YMin"] ? 0
                    : [asset.aspect containsString:@"YMax"]
                        ? rect.size.height - size.height
                        : (rect.size.height - size.height) / 2;
        NSRectClip(rect);
        rect = NSMakeRect(rect.origin.x + x, rect.origin.y + y, size.width,
                          size.height);
      }
      [image drawInRect:rect
                fromRect:NSZeroRect
               operation:NSCompositingOperationSourceOver
                fraction:n.opacity
          respectFlipped:YES
                   hints:nil];
    }
  } else if ([n.source[@"tag"] isEqual:@"input"] &&
             ![n.source[@"attributes"][@"value"] length]) {
    NSString *placeholder = n.source[@"attributes"][@"placeholder"];
    if ([placeholder isKindOfClass:NSString.class] && placeholder.length) {
      NSRect box = pcc_doc_inner(n);
      NSDictionary *attributes = @{NSFontAttributeName: pcc_doc_font(n),
                                    NSForegroundColorAttributeName: NSColor.placeholderTextColor};
      NSRectClip(box);
      CGFloat height = [placeholder sizeWithAttributes:attributes].height;
      [placeholder drawAtPoint:NSMakePoint(NSMinX(box), NSMidY(box) - height / 2)
                withAttributes:attributes];
    }
  } else if (pcc_doc_textbox(n)) {
    NSMutableAttributedString *text =
        [[NSMutableAttributedString alloc] initWithString:@""];
    pcc_doc_runs(n, text);
    if (text.length) {
      NSRect box = pcc_doc_inner(n);
      BOOL centered = [n.style[@"text-align"] isEqual:@"center"] ||
                      [n.style[@"justify-content"] isEqual:@"center"];
      CGFloat lineY = box.origin.y;
      if ([n.style[@"align-items"] isEqual:@"center"])
        lineY += (box.size.height - n.lineHeight) / 2;
      CTLineRef line = CTLineCreateWithAttributedString(
          (__bridge CFAttributedStringRef)text);
      CGFloat ascent = 0, descent = 0, leading = 0;
      double width =
          CTLineGetTypographicBounds(line, &ascent, &descent, &leading);
      CGFloat baseline = lineY + (n.lineHeight - ascent - descent) / 2 + ascent;
      CGContextRef context = NSGraphicsContext.currentContext.CGContext;
      CGContextSaveGState(context);
      CGContextSetTextMatrix(context, CGAffineTransformMakeScale(1, -1));
      CGContextSetTextPosition(
          context, box.origin.x + (centered ? (box.size.width - width) / 2 : 0),
          baseline);
      CTLineDraw(line, context);
      CGContextRestoreGState(context);
      CFRelease(line);
    }
  } else
    for (PCCDocumentNode *c in n.children)
      pcc_doc_draw(c, images);
  [NSGraphicsContext restoreGraphicsState];
}
@implementation PCCDocumentView
- (BOOL)isFlipped {
  return YES;
}
- (BOOL)isOpaque {
  return NO;
}
- (void)drawRect:(NSRect)dirty {
  [NSColor.clearColor setFill];
  NSRectFillUsingOperation(self.bounds, NSCompositingOperationCopy);
  if (self.nodes.count) {
    PCCDocumentNode *root = self.nodes[0];
    pcc_doc_layout(root, NSMakeRect(0, 0, self.bounds.size.width,
                                    self.bounds.size.height));
    pcc_doc_draw(root, self.images);
  }
  NSRect footer = NSMakeRect(0, MAX(0, self.bounds.size.height - 30),
                             self.bounds.size.width, 30);
  [[NSColor colorWithSRGBRed:.12 green:.14 blue:.18 alpha:.94] setFill];
  NSRectFill(footer);
  NSString *status =
      self.status ?: @"Read-only translated preview · backend not connected";
  [status drawInRect:NSInsetRect(footer, 12, 7)
      withAttributes:@{
        NSFontAttributeName : [NSFont systemFontOfSize:11],
        NSForegroundColorAttributeName : NSColor.whiteColor
      }];
}
- (BOOL)acceptsFirstMouse:(NSEvent *)event {
  return self.enabledButtons.count > 0 || [super acceptsFirstMouse:event];
}
- (NSInteger)buttonAtEvent:(NSEvent *)event {
  NSPoint p = [self convertPoint:event.locationInWindow fromView:nil];
  for (PCCDocumentNode *node in self.nodes.reverseObjectEnumerator) {
    if (!node.hidden && NSPointInRect(p, node.frame) &&
        [node.source[@"tag"] isEqual:@"button"] &&
        !node.source[@"attributes"][@"disabled"])
      return [node.source[@"index"] integerValue];
  }
  return -1;
}
- (void)mouseDown:(NSEvent *)event {
  NSInteger index = [self buttonAtEvent:event];
  self.pressedButton = -1;
  if (index < 0) return;
  if ([self.enabledButtons containsIndex:index]) self.pressedButton = index;
  else {
    self.status = @"This action is unavailable.";
    [self setNeedsDisplay:YES];
  }
}
- (void)mouseUp:(NSEvent *)event {
  NSInteger pressed = self.pressedButton;
  self.pressedButton = -1;
  if (pressed >= 0 && self.pendingButton < 0 && [self buttonAtEvent:event] == pressed)
    self.pendingButton = pressed;
}
@end
static char pcc_doc_key;
static BOOL pcc_doc_known(void *handle) {
  if (![NSThread isMainThread] || !handle)
    return NO;
  for (NSWindow *window in pcc_fs_windows)
    if ((__bridge void *)window == handle)
      return YES;
  return NO;
}
int32_t pcc_gui_document_present(void *handle, const uint8_t *bytes,
                                 uint64_t size) {
  @autoreleasepool {
    if (!pcc_doc_known(handle) || !bytes || size == 0 ||
        size > 16 * 1024 * 1024)
      return 2;
    NSData *data = [NSData dataWithBytes:bytes length:(NSUInteger)size];
    NSError *error = nil;
    id raw =
        [NSJSONSerialization JSONObjectWithData:data options:0 error:&error];
    if (![raw isKindOfClass:NSDictionary.class] ||
        ![raw[@"schema"] isEqual:@"t2-browser-presentation-v1"])
      return 3;
    NSArray *rows = raw[@"nodes"];
    if (![rows isKindOfClass:NSArray.class] || rows.count == 0 ||
        rows.count > 10000)
      return 3;
    double width = [raw[@"width"] doubleValue],
           height = [raw[@"height"] doubleValue];
    if (width < 1 || height < 1 || width > 8192 || height > 8192)
      return 3;
    NSMutableArray<PCCDocumentNode *> *nodes = [NSMutableArray array];
    for (NSUInteger i = 0; i < rows.count; i++) {
      NSDictionary *row = rows[i];
      if (![row isKindOfClass:NSDictionary.class] ||
          [row[@"index"] integerValue] != (NSInteger)i ||
          ![row[@"children"] isKindOfClass:NSArray.class] ||
          ![row[@"attributes"] isKindOfClass:NSDictionary.class] ||
          ![row[@"styles"] isKindOfClass:NSArray.class] ||
          ![row[@"tag"] isKindOfClass:NSString.class] ||
          ![row[@"text"] isKindOfClass:NSString.class] ||
          ![row[@"name"] isKindOfClass:NSString.class])
        return 3;
      PCCDocumentNode *node = [[PCCDocumentNode alloc] init];
      node.source = row;
      node.children = [NSMutableArray array];
      [nodes addObject:node];
    }
    NSMutableSet *seen = [NSMutableSet set];
    NSMutableArray *stack = [NSMutableArray arrayWithObject:@0];
    while (stack.count) {
      NSNumber *key = stack.lastObject;
      [stack removeLastObject];
      if ([seen containsObject:key])
        return 3;
      [seen addObject:key];
      PCCDocumentNode *n = nodes[key.unsignedIntegerValue];
      for (id child in n.source[@"children"]) {
        if (![child isKindOfClass:NSNumber.class])
          return 3;
        NSInteger index = [child integerValue];
        if (index < 0 || index >= (NSInteger)nodes.count ||
            [nodes[index] source][@"parent"] == nil ||
            [[nodes[index] source][@"parent"] integerValue] != key.integerValue)
          return 3;
        [n.children addObject:nodes[index]];
        [stack addObject:child];
      }
    }
    for (PCCDocumentNode *n in nodes) {
      for (id value in [n.source[@"attributes"] allValues])
        if (![value isKindOfClass:NSString.class])
          return 3;
      for (NSDictionary *row in n.source[@"styles"]) {
        if (![row isKindOfClass:NSDictionary.class] ||
            ![row[@"name"] isKindOfClass:NSString.class] ||
            ![row[@"value"] isKindOfClass:NSString.class])
          return 3;
        for (NSString *key in @[ @"important", @"ids", @"classes", @"types" ])
          if (![row[key] isKindOfClass:NSNumber.class] ||
              [row[key] doubleValue] < 0 || [row[key] doubleValue] > 10000)
            return 3;
      }
    }
    pcc_doc_styles(nodes[0], nil, 0);
    NSMutableDictionary *images = [NSMutableDictionary dictionary];
    id assets = raw[@"images"];
    if ([assets isKindOfClass:NSArray.class])
      for (NSDictionary *asset in assets) {
        NSInteger w = [asset[@"width"] integerValue],
                  h = [asset[@"height"] integerValue];
        NSData *pixels = pcc_doc_hex(asset[@"pixels_hex"]);
        if (w <= 0 || h <= 0 || w > 8192 || h > 8192 ||
            pixels.length != (NSUInteger)w * (NSUInteger)h * 4)
          continue;
        CGDataProviderRef provider =
            CGDataProviderCreateWithCFData((__bridge CFDataRef)pixels);
        CGColorSpaceRef space = CGColorSpaceCreateDeviceRGB();
        CGImageRef cg =
            CGImageCreate(w, h, 8, 32, w * 4, space,
                          kCGImageAlphaLast | kCGBitmapByteOrder32Big, provider,
                          NULL, false, kCGRenderingIntentDefault);
        if (cg) {
          NSImage *image =
              [[NSImage alloc] initWithCGImage:cg size:NSMakeSize(w, h)];
          PCCDocumentImage *entry = [PCCDocumentImage new];
          entry.image = image;
          if ([asset[@"mime"] isEqual:@"image/svg+xml"]) {
            NSData *encoded = pcc_doc_hex(asset[@"encoded_hex"]);
            NSString *aspect = pcc_doc_svg_aspect(encoded);
            if (!aspect)
              return 3;
            NSImage *vector = [[NSImage alloc] initWithData:encoded];
            if (!vector || vector.size.width != w || vector.size.height != h)
              return 3;
            entry.image = vector;
          }
          if ([asset[@"mime"] isEqual:@"image/svg+xml"])
            entry.aspect =
                pcc_doc_svg_aspect(pcc_doc_hex(asset[@"encoded_hex"]));
          if (asset[@"request"])
            images[asset[@"request"]] = entry;
          if (asset[@"url"])
            images[asset[@"url"]] = entry;
          CGImageRelease(cg);
        }
        CGColorSpaceRelease(space);
        CGDataProviderRelease(provider);
      }
    NSWindow *window = (__bridge NSWindow *)handle;
    PCCDocumentView *previous = objc_getAssociatedObject(window, &pcc_doc_key);
    PCCDocumentView *view =
        [[PCCDocumentView alloc] initWithFrame:window.contentView.bounds];
    view.autoresizingMask = NSViewWidthSizable | NSViewHeightSizable;
    view.nodes = nodes;
    view.images = images;
    view.sourceWidth = width;
    view.sourceHeight = height;
    view.status = previous.status;
    view.enabledButtons = [NSMutableIndexSet indexSet];
    view.pressedButton = -1;
    view.pendingButton = -1;
    [window.contentView addSubview:view];
    [previous removeFromSuperview];
    objc_setAssociatedObject(window, &pcc_doc_key, view,
                             OBJC_ASSOCIATION_RETAIN_NONATOMIC);
    if ([pcc_metal_view window] == window)
      pcc_metal_view.hidden = YES;
    [view setNeedsDisplay:YES];
    return 0;
  }
}
int32_t pcc_gui_document_enable_button(void *handle, int64_t index) {
  if (!pcc_doc_known(handle)) return 2;
  PCCDocumentView *view = objc_getAssociatedObject((__bridge NSWindow *)handle, &pcc_doc_key);
  if (!view || index < 0 || index >= (int64_t)view.nodes.count ||
      ![view.nodes[index].source[@"tag"] isEqual:@"button"]) return 3;
  [view.enabledButtons addIndex:(NSUInteger)index];
  return 0;
}
int64_t pcc_gui_document_take_click(void *handle) {
  if (!pcc_doc_known(handle)) return -1;
  PCCDocumentView *view = objc_getAssociatedObject((__bridge NSWindow *)handle, &pcc_doc_key);
  if (!view) return -1;
  NSInteger result = view.pendingButton;
  view.pendingButton = -1;
  return result;
}
int32_t pcc_gui_document_status(void *handle, const char *message) {
  if (!pcc_doc_known(handle) || !message)
    return 2;
  PCCDocumentView *view =
      objc_getAssociatedObject((__bridge NSWindow *)handle, &pcc_doc_key);
  if (!view)
    return 3;
  view.status = [NSString stringWithUTF8String:message];
  [view setNeedsDisplay:YES];
  return 0;
}
int32_t pcc_gui_document_rect(void *handle, int64_t index, double *xywh) {
  if (!pcc_doc_known(handle) || !xywh)
    return 2;
  PCCDocumentView *view =
      objc_getAssociatedObject((__bridge NSWindow *)handle, &pcc_doc_key);
  if (!view || index < 0 || index >= (int64_t)view.nodes.count)
    return 3;
  pcc_doc_layout(view.nodes[0], NSMakeRect(0, 0, view.bounds.size.width,
                                           view.bounds.size.height));
  NSRect r = view.nodes[index].frame;
  xywh[0] = r.origin.x;
  xywh[1] = r.origin.y;
  xywh[2] = r.size.width;
  xywh[3] = r.size.height;
  return 0;
}
int64_t pcc_gui_document_node_count(void *handle) {
  if (!pcc_doc_known(handle))
    return -1;
  PCCDocumentView *view =
      objc_getAssociatedObject((__bridge NSWindow *)handle, &pcc_doc_key);
  return view ? (int64_t)view.nodes.count : 0;
}
