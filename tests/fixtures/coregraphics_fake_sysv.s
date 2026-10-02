.intel_syntax noprefix
.data
.p2align 3
.globl pcc_gui_cg_probe_state
pcc_gui_cg_probe_state:
.zero 512
_fake_framework:
.quad 0
_fake_color:
.quad 0
_fake_context:
.quad 0
_fake_framework_path:
.byte 47, 83, 121, 115, 116, 101, 109, 47, 76, 105, 98, 114, 97, 114, 121, 47, 70, 114, 97, 109, 101, 119, 111, 114, 107, 115, 47, 67, 111, 114, 101, 71, 114, 97, 112, 104, 105, 99, 115, 46, 102, 114, 97, 109, 101, 119, 111, 114, 107, 47, 67, 111, 114, 101, 71, 114, 97, 112, 104, 105, 99, 115, 0
_fake_name1:
.byte 67, 71, 67, 111, 110, 116, 101, 120, 116, 83, 101, 116, 82, 71, 66, 70, 105, 108, 108, 67, 111, 108, 111, 114, 0
_fake_name2:
.byte 67, 71, 67, 111, 110, 116, 101, 120, 116, 70, 105, 108, 108, 82, 101, 99, 116, 0
_fake_name3:
.byte 67, 71, 66, 105, 116, 109, 97, 112, 67, 111, 110, 116, 101, 120, 116, 67, 114, 101, 97, 116, 101, 0
_fake_name4:
.byte 67, 71, 67, 111, 108, 111, 114, 83, 112, 97, 99, 101, 67, 114, 101, 97, 116, 101, 68, 101, 118, 105, 99, 101, 82, 71, 66, 0
_fake_name5:
.byte 67, 71, 67, 111, 108, 111, 114, 83, 112, 97, 99, 101, 82, 101, 108, 101, 97, 115, 101, 0
_fake_name6:
.byte 67, 71, 67, 111, 110, 116, 101, 120, 116, 82, 101, 108, 101, 97, 115, 101, 0
_fake_name7:
.byte 67, 71, 67, 111, 110, 116, 101, 120, 116, 83, 116, 114, 111, 107, 101, 76, 105, 110, 101, 83, 101, 103, 109, 101, 110, 116, 115, 0
.text
_fake_name_equal:
 xor ecx, ecx
.L_name_loop:
 mov al, BYTE PTR [rdi + rcx]
 mov dl, BYTE PTR [rsi + rcx]
 cmp al, dl
 jne .L_name_false
 test al, al
 je .L_name_true
 add rcx, 1
 jmp .L_name_loop
.L_name_false:
 xor eax, eax
 ret
.L_name_true:
 mov eax, 1
 ret
.globl dlopen
dlopen:
 lea r10, pcc_gui_cg_probe_state[rip]
 mov rax, QWORD PTR [r10 + 32]
 add rax, 1
 mov QWORD PTR [r10 + 32], rax
 mov QWORD PTR [r10 + 312], rsi
 sub rsp, 8
 lea rsi, _fake_framework_path[rip]
 call _fake_name_equal
 add rsp, 8
 mov QWORD PTR [r10 + 320], rax
 mov rax, QWORD PTR [r10]
 cmp rax, 0
 jne .L_open_failed
 lea rax, _fake_framework[rip]
 ret
.L_open_failed:
 xor eax, eax
 ret
.globl dlsym
dlsym:
 lea r10, pcc_gui_cg_probe_state[rip]
 mov rax, QWORD PTR [r10 + 40]
 add rax, 1
 mov QWORD PTR [r10 + 40], rax
 lea rax, _fake_framework[rip]
 cmp rdi, rax
 je .L_symbol_handle_ok
 mov rax, QWORD PTR [r10 + 104]
 add rax, 1
 mov QWORD PTR [r10 + 104], rax
.L_symbol_handle_ok:
 push rbx
 mov rbx, rsi
 mov rdi, rbx
 lea rsi, _fake_name1[rip]
 call _fake_name_equal
 test eax, eax
 jne .L_symbol_1
 mov rdi, rbx
 lea rsi, _fake_name2[rip]
 call _fake_name_equal
 test eax, eax
 jne .L_symbol_2
 mov rdi, rbx
 lea rsi, _fake_name3[rip]
 call _fake_name_equal
 test eax, eax
 jne .L_symbol_3
 mov rdi, rbx
 lea rsi, _fake_name4[rip]
 call _fake_name_equal
 test eax, eax
 jne .L_symbol_4
 mov rdi, rbx
 lea rsi, _fake_name5[rip]
 call _fake_name_equal
 test eax, eax
 jne .L_symbol_5
 mov rdi, rbx
 lea rsi, _fake_name6[rip]
 call _fake_name_equal
 test eax, eax
 jne .L_symbol_6
 mov rdi, rbx
 lea rsi, _fake_name7[rip]
 call _fake_name_equal
 test eax, eax
 jne .L_symbol_7
 xor eax, eax
 pop rbx
 ret
.L_symbol_1:
 mov rax, QWORD PTR [r10 + 8]
 cmp rax, 1
 je .L_symbol_missing
 lea rax, CGContextSetRGBFillColor[rip]
 pop rbx
 ret
.L_symbol_2:
 mov rax, QWORD PTR [r10 + 8]
 cmp rax, 2
 je .L_symbol_missing
 lea rax, CGContextFillRect[rip]
 pop rbx
 ret
.L_symbol_3:
 mov rax, QWORD PTR [r10 + 8]
 cmp rax, 3
 je .L_symbol_missing
 lea rax, CGBitmapContextCreate[rip]
 pop rbx
 ret
.L_symbol_4:
 mov rax, QWORD PTR [r10 + 8]
 cmp rax, 4
 je .L_symbol_missing
 lea rax, CGColorSpaceCreateDeviceRGB[rip]
 pop rbx
 ret
.L_symbol_5:
 mov rax, QWORD PTR [r10 + 8]
 cmp rax, 5
 je .L_symbol_missing
 lea rax, CGColorSpaceRelease[rip]
 pop rbx
 ret
.L_symbol_6:
 mov rax, QWORD PTR [r10 + 8]
 cmp rax, 6
 je .L_symbol_missing
 lea rax, CGContextRelease[rip]
 pop rbx
 ret
.L_symbol_7:
 mov rax, QWORD PTR [r10 + 8]
 cmp rax, 7
 je .L_symbol_missing
 lea rax, CGContextStrokeLineSegments[rip]
 pop rbx
 ret
.L_symbol_missing:
 xor eax, eax
 pop rbx
 ret
.globl CGColorSpaceCreateDeviceRGB
CGColorSpaceCreateDeviceRGB:
 lea r10, pcc_gui_cg_probe_state[rip]
 mov rax, QWORD PTR [r10 + 48]
 add rax, 1
 mov QWORD PTR [r10 + 48], rax
 mov rax, QWORD PTR [r10 + 16]
 cmp rax, 0
 jne .L_color_failed
 lea rax, _fake_color[rip]
 ret
.L_color_failed:
 xor eax, eax
 ret
.globl CGColorSpaceRelease
CGColorSpaceRelease:
 lea r10, pcc_gui_cg_probe_state[rip]
 mov rax, QWORD PTR [r10 + 56]
 add rax, 1
 mov QWORD PTR [r10 + 56], rax
 mov QWORD PTR [r10 + 352], rdi
 ret
.globl CGBitmapContextCreate
CGBitmapContextCreate:
 lea r10, pcc_gui_cg_probe_state[rip]
 mov rax, QWORD PTR [r10 + 64]
 add rax, 1
 mov QWORD PTR [r10 + 64], rax
 mov QWORD PTR [r10 + 112], rdi
 mov QWORD PTR [r10 + 120], rsi
 mov QWORD PTR [r10 + 128], rdx
 mov QWORD PTR [r10 + 136], rcx
 mov QWORD PTR [r10 + 144], r8
 mov QWORD PTR [r10 + 152], r9
 mov eax, DWORD PTR [rsp + 8]
 mov QWORD PTR [r10 + 160], rax
 mov rax, QWORD PTR [r10 + 24]
 cmp rax, 0
 jne .L_bitmap_failed
 lea rax, _fake_context[rip]
 ret
.L_bitmap_failed:
 xor eax, eax
 ret
.globl CGContextRelease
CGContextRelease:
 lea r10, pcc_gui_cg_probe_state[rip]
 mov rax, QWORD PTR [r10 + 72]
 add rax, 1
 mov QWORD PTR [r10 + 72], rax
 mov QWORD PTR [r10 + 168], rdi
 ret
.globl CGContextSetRGBFillColor
CGContextSetRGBFillColor:
 lea r10, pcc_gui_cg_probe_state[rip]
 mov rax, QWORD PTR [r10 + 80]
 add rax, 1
 mov QWORD PTR [r10 + 80], rax
 mov QWORD PTR [r10 + 176], rdi
 movq rax, xmm0
 mov QWORD PTR [r10 + 184], rax
 movq rax, xmm1
 mov QWORD PTR [r10 + 192], rax
 movq rax, xmm2
 mov QWORD PTR [r10 + 200], rax
 movq rax, xmm3
 mov QWORD PTR [r10 + 208], rax
 ret
.globl CGContextFillRect
CGContextFillRect:
 lea r10, pcc_gui_cg_probe_state[rip]
 mov rax, QWORD PTR [r10 + 88]
 add rax, 1
 mov QWORD PTR [r10 + 88], rax
 mov QWORD PTR [r10 + 216], rdi
 mov rax, QWORD PTR [rsp + 8]
 mov QWORD PTR [r10 + 224], rax
 mov rax, QWORD PTR [rsp + 16]
 mov QWORD PTR [r10 + 232], rax
 mov rax, QWORD PTR [rsp + 24]
 mov QWORD PTR [r10 + 240], rax
 mov rax, QWORD PTR [rsp + 32]
 mov QWORD PTR [r10 + 248], rax
 ret
.globl CGContextStrokeLineSegments
CGContextStrokeLineSegments:
 lea r10, pcc_gui_cg_probe_state[rip]
 mov rax, QWORD PTR [r10 + 96]
 add rax, 1
 mov QWORD PTR [r10 + 96], rax
 mov QWORD PTR [r10 + 256], rdi
 mov QWORD PTR [r10 + 264], rdx
 mov rax, rsi
 and rax, 7
 mov QWORD PTR [r10 + 272], rax
 mov rax, QWORD PTR [rsi]
 mov QWORD PTR [r10 + 280], rax
 mov rax, QWORD PTR [rsi + 8]
 mov QWORD PTR [r10 + 288], rax
 mov rax, QWORD PTR [rsi + 16]
 mov QWORD PTR [r10 + 296], rax
 mov rax, QWORD PTR [rsi + 24]
 mov QWORD PTR [r10 + 304], rax
 ret
.globl pcc_gui_cg_probe_setup
pcc_gui_cg_probe_setup:
 lea r10, pcc_gui_cg_probe_state[rip]
 lea rax, _fake_color[rip]
 mov QWORD PTR [r10 + 328], rax
 lea rax, _fake_context[rip]
 mov QWORD PTR [r10 + 336], rax
 lea rax, _fake_framework[rip]
 mov QWORD PTR [r10 + 344], rax
 ret
