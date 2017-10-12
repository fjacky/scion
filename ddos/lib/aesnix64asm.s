[bits 64]
[CPU intelnop]

%macro linux_setup 0
%ifdef __linux__
 	mov r9, rcx
 	mov r8, rdx
	mov rcx, rdi
	mov rdx, rsi
%endif
%endmacro

%macro inversekey 1
	movdqu  xmm1,%1
	aesimc	xmm0,xmm1
	movdqu	%1,xmm0
%endmacro

%macro aesenc1_u 1
	movdqu	xmm4,%1
	aesenc	xmm0,xmm4
%endmacro

%macro aesenclast1_u 1
	movdqu	xmm4,%1
	aesenclast	xmm0,xmm4
%endmacro

%macro aesenc2_u 1
	movdqu	xmm4,%1
	aesenc	xmm0,xmm4
	aesenc	xmm1,xmm4
%endmacro

%macro aesenclast2_u 1
	movdqu	xmm4,%1
	aesenclast	xmm0,xmm4
	aesenclast	xmm1,xmm4
%endmacro

%macro aesenc4_u 1
	movdqa	xmm4,%1
	
	aesenc	xmm0,xmm4
	aesenc	xmm1,xmm4
	aesenc	xmm2,xmm4
	aesenc	xmm3,xmm4
%endmacro

%macro aesenclast4_u 1
	movdqa	xmm4,%1

	aesenclast	xmm0,xmm4
	aesenclast	xmm1,xmm4
	aesenclast	xmm2,xmm4
	aesenclast	xmm3,xmm4
%endmacro

%macro load_and_inc4 1
	movdqa	xmm4,%1
	movdqa	xmm0,xmm5
	pshufb	xmm0, xmm6 ; byte swap counter back
	movdqa  xmm1,xmm5
	paddd	xmm1,[counter_add_one wrt rip]
	pshufb	xmm1, xmm6 ; byte swap counter back
	movdqa  xmm2,xmm5
	paddd	xmm2,[counter_add_two wrt rip]
	pshufb	xmm2, xmm6 ; byte swap counter back
	movdqa  xmm3,xmm5
	paddd	xmm3,[counter_add_three wrt rip]
	pshufb	xmm3, xmm6 ; byte swap counter back
	pxor	xmm0,xmm4
	paddd	xmm5,[counter_add_four wrt rip]
	pxor	xmm1,xmm4
	pxor	xmm2,xmm4
	pxor	xmm3,xmm4
%endmacro

%macro xor_with_input4 1
	movdqu xmm4,[%1]
	pxor xmm0,xmm4
	movdqu xmm4,[%1+16]
	pxor xmm1,xmm4
	movdqu xmm4,[%1+32]
	pxor xmm2,xmm4
	movdqu xmm4,[%1+48]
	pxor xmm3,xmm4
%endmacro

%macro load_and_xor4 2
	movdqa	xmm4,%2
	movdqu	xmm0,[%1 + 0*16]
	pxor	xmm0,xmm4
	movdqu	xmm1,[%1 + 1*16]
	pxor	xmm1,xmm4
	movdqu	xmm2,[%1 + 2*16]
	pxor	xmm2,xmm4
	movdqu	xmm3,[%1 + 3*16]
	pxor	xmm3,xmm4
%endmacro

%macro store4 1
	movdqu [%1 + 0*16],xmm0
	movdqu [%1 + 1*16],xmm1
	movdqu [%1 + 2*16],xmm2
	movdqu [%1 + 3*16],xmm3
%endmacro

%macro copy_round_keys 3
	movdqu xmm4,[%2 + ((%3)*16)]
	movdqa [%1 + ((%3)*16)],xmm4
%endmacro


%macro key_expansion_1_192 1
	;; Assumes the xmm3 includes all zeros at this point. 
    pshufd xmm2, xmm2, 11111111b        
    shufps xmm3, xmm1, 00010000b        
    pxor xmm1, xmm3        
    shufps xmm3, xmm1, 10001100b
    pxor xmm1, xmm3        
	pxor xmm1, xmm2		
	movdqu [rdx+%1], xmm1			
%endmacro

; Calculate w10 and w11 using calculated w9 and known w4-w5
%macro key_expansion_2_192 1				
	movdqa xmm5, xmm4
	pslldq xmm5, 4
	shufps xmm6, xmm1, 11110000b
	pxor xmm6, xmm5
	pxor xmm4, xmm6
	pshufd xmm7, xmm4, 00001110b 
	movdqu [rdx+%1], xmm7
%endmacro


section .data
align 16
shuffle_mask:
DD 0FFFFFFFFh
DD 03020100h
DD 07060504h
DD 0B0A0908h

byte_swap_16:
DDQ 0x000102030405060708090A0B0C0D0E0F


align 16
counter_add_one:
DD 1
DD 0
DD 0
DD 0

counter_add_two:
DD 2
DD 0
DD 0
DD 0

counter_add_three:
DD 3
DD 0
DD 0
DD 0

counter_add_four:
DD 4
DD 0
DD 0
DD 0



section .text

align 16
key_expansion128: 
    pshufd xmm2, xmm2, 0xFF;
    movdqa xmm3, xmm1
    pshufb xmm3, xmm5
    pxor xmm1, xmm3
    pshufb xmm3, xmm5
    pxor xmm1, xmm3
    pshufb xmm3, xmm5
    pxor xmm1, xmm3
    pxor xmm1, xmm2

    ; storing the result in the key schedule array
    movdqu [rdx], xmm1
    add rdx, 0x10                    
    ret
    

align 16
global ExpandKey128
ExpandKey128:

	linux_setup

    

    movdqu xmm1, [rcx]    ; loading the key

    movdqu [rdx], xmm1

    movdqa xmm5, [shuffle_mask wrt rip]

    add rdx,16

    aeskeygenassist xmm2, xmm1, 0x1     ; Generating round key 1
    call key_expansion128
    aeskeygenassist xmm2, xmm1, 0x2     ; Generating round key 2
    call key_expansion128
    aeskeygenassist xmm2, xmm1, 0x4     ; Generating round key 3
    call key_expansion128
    aeskeygenassist xmm2, xmm1, 0x8     ; Generating round key 4
    call key_expansion128
    aeskeygenassist xmm2, xmm1, 0x10    ; Generating round key 5
    call key_expansion128
    aeskeygenassist xmm2, xmm1, 0x20    ; Generating round key 6
    call key_expansion128
    aeskeygenassist xmm2, xmm1, 0x40    ; Generating round key 7
    call key_expansion128
    aeskeygenassist xmm2, xmm1, 0x80    ; Generating round key 8
    call key_expansion128
    aeskeygenassist xmm2, xmm1, 0x1b    ; Generating round key 9
    call key_expansion128
    aeskeygenassist xmm2, xmm1, 0x36    ; Generating round key 10
    call key_expansion128

	ret



align 16
global _do_rdtsc
_do_rdtsc:

	rdtsc
	ret

align 16
global sample_rate
sample_rate:

	ret

align 16
global PMAC
PMAC:
	
	linux_setup
	
testcount:
	
	cmp edx, 5						; if blk > 5
	jl endblk
	
para4blk:						; encrypt for four block
	
	movdqu xmm0, [r8+0*16]		; loading the input
	movdqu xmm1, [r8+1*16]		; loading the input
	movdqu xmm2, [r8+2*16]		; loading the input
	movdqu xmm3, [r8+3*16]		; loading the input
	
	movdqu xmm4, [rcx+0*16]		; loading the round keys
	
	pxor xmm0, xmm4
	pxor xmm1, xmm4
	pxor xmm2, xmm4
	pxor xmm3, xmm4
	aesenc4_u [rcx+1*16]
	aesenc4_u [rcx+2*16]
	aesenc4_u [rcx+3*16]
	aesenc4_u [rcx+4*16]     
	aesenc4_u [rcx+5*16]
	aesenc4_u [rcx+6*16]
	aesenc4_u [rcx+7*16]
	aesenc4_u [rcx+8*16]
	aesenc4_u [rcx+9*16]
	aesenclast4_u [rcx+10*16]
	
	sub edx, 4					; blk = blk-4
	add r8, 64					; input address + 16
	pxor xmm0, xmm1
	pxor xmm2, xmm3
	pxor xmm0, xmm2
	movdqu xmm5, xmm0
	jmp testcount				; goto loop test
	
endblk:
	movdqu xmm0, [r8]			; loading the last block
	pxor xmm0, xmm5
	
	movdqu xmm4, [rcx+0*16]		; loading the round keys

	pxor xmm0, xmm4
	aesenc1_u [rcx+1*16]
	aesenc1_u [rcx+2*16]
	aesenc1_u [rcx+3*16]
	aesenc1_u [rcx+4*16]     
	aesenc1_u [rcx+5*16]
	aesenc1_u [rcx+6*16]
	aesenc1_u [rcx+7*16]
	aesenc1_u [rcx+8*16]
	aesenc1_u [rcx+9*16]
	aesenclast1_u [rcx+10*16]
	
	movdqu  [r9], xmm0
	ret


align 16
global CBCMAC
CBCMAC:
	
	linux_setup
	pxor xmm1, xmm1				;
	movdqu [rcx], xmm1			;

	
testloop:
	
	test edx,edx				; if blk = 0
	jz endloop

enc1block:						; encrypt for one block
	
	movdqu xmm0, [r8]			; loading the input
	movdqu xmm1, [rcx]			; loading iv
	movdqu xmm4, [rcx+0*16]		; loading the round keys
	
	pxor xmm0, xmm1				; xor iv
	aesenc1_u [rcx+1*16]
	aesenc1_u [rcx+2*16]
	aesenc1_u [rcx+3*16]
	aesenc1_u [rcx+4*16]     
	aesenc1_u [rcx+5*16]
	aesenc1_u [rcx+6*16]
	aesenc1_u [rcx+7*16]
	aesenc1_u [rcx+8*16]
	aesenc1_u [rcx+9*16]
	aesenclast1_u [rcx+10*16]
	
	dec edx					; blk --
	add r8, 16				; input address + 16
	movdqu [rcx], xmm0		; copy cipher as iv for next round encryption
	jmp testloop			; goto loop test
	
endloop:
	
	movdqu  [r9], xmm0
	ret



align 16
global PRF
PRF:
	
	linux_setup
	
	; compute L = E_k(x)
	movdqu xmm0, [r8]			; loading the seed (x)
	movdqu xmm2, xmm0			; store original seed (x)
	movdqu xmm4, [rcx+0*16]		; loading the round keys
	mov rax, 0
	
	pxor xmm0, xmm4
	aesenc1_u [rcx+1*16]
	aesenc1_u [rcx+2*16]
	aesenc1_u [rcx+3*16]
	aesenc1_u [rcx+4*16]     
	aesenc1_u [rcx+5*16]
	aesenc1_u [rcx+6*16]
	aesenc1_u [rcx+7*16]
	aesenc1_u [rcx+8*16]
	aesenc1_u [rcx+9*16]
	aesenclast1_u [rcx+10*16]
	movdqu xmm1, xmm0			; stroe L

tloop:
	
	test edx,edx				; if blk = 0
	jz eloop

prf1block:						; encrypt for one block
	
	; inc(x)
	paddd xmm2,[counter_add_one wrt rip]
	movdqu xmm0, xmm2
	
	pxor xmm0, xmm4
	aesenc1_u [rcx+1*16]
	aesenc1_u [rcx+2*16]
	aesenc1_u [rcx+3*16]
	aesenc1_u [rcx+4*16]     
	aesenc1_u [rcx+5*16]
	aesenc1_u [rcx+6*16]
	aesenc1_u [rcx+7*16]
	aesenc1_u [rcx+8*16]
	aesenc1_u [rcx+9*16]
	aesenclast1_u [rcx+10*16]
	
	pxor xmm0, xmm1				; store L xor E_k(inc(x))
	dec edx						; blk --
	movdqu [r9], xmm0			; copy random to output
	add r9, 16					; shift to next block
	jmp tloop					; goto loop test
	
eloop:
	ret

