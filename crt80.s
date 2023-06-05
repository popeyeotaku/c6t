; partial C RunTime for C6T under CP/M

; This should be enough to run the frontend under CP/M, with some minor
; modifications to the frontend (fake flush(), main only supporting
; standard input).

bdos		= 5
C_WRITE		= 2
C_READSTR	= 10

		.text
start:		.export start	; boot here! should be at hex 100
		lhld 6		; setup stack to under BDOS
		sphl

		lxi h,0		; setup fake argc/argv
		push h
		push h

		call _main	; run the program!

_exit:		.export _exit
_abort:		.export _abort
		jmp 0		; reboot CP/M!

csave:		.export csave	; setup frame pointer and save regs
		pop h		; return addr from csave to HL
		xchg		; ... to DE
		push b		; save frame pointer
		lhld reg0	; save registers
		push h
		lhld reg1
		push h
		lhld reg2
		push h

		lxi h,0	; setup frame pointer in BC
		dad sp
		mov b,h
		mov c,l

		xchg		; return from csave
		pchl

cret:		.export cret	; return from a function entered w/ csave
		xchg		; save return value in DE

		mov h,b	; restore stack pointer to frame pointer
		mov l,c
		sphl

		pop h		; restore registers
		shld reg2
		pop h
		shld reg1
		pop h
		shld reg0

		pop b		; restore frame pointer

		xchg		; return value back to HL

		ret		; return via actual return addr on stack

		; output a character in CP/M
_putchar:	.export _putchar
		push b		; save frame pointer
		lxi h,4		; get character from stack
		dad sp
		mov a,m
		cpi 012		; convert newlines

		jnz nonl
		push psw	; save A
		lxi h,015	; output CR before newline
		push h
		call _putchar
		pop h
		pop psw		; restore A, output nl
nonl:		mov e,a
		mvi c,C_WRITE
		call bdos

		pop b		; restore frame pointer
		ret

		; get a character from CP/M
_getchar:	.export _getchar
		.data		; we have to do this buffered
getsize		= 72		; max chars in the buffer
		.export getbuf
getbuf:		.db getsize	; indicator of size to CP/M
		.ds 1		; chars CP/M placed into buffer
		.ds getsize	; buffer contents
		.bss
geti:		.ds 1		; our current position in the buffer
		.data
getflag:	.db 1		; flag for if we need to refill the buffer
		.export getinit,geti,getflag
		.text
		lda getflag
		ora a
		jnz getrefill
getagain:	lda geti	; compare current index to len
		mov e,a
		lda getbuf+1
		cmp e
		jnz skipfill	; skip refill if we have character
		mvi a,1		; set refill flag
		sta getflag
		lxi h,012	; return newline
		push h
		call _putchar	; output one too
		pop h
		ret
getrefill:	xra a		; clear refill flag
		sta getflag
		push b
		lxi d,getbuf	; refill buffer
		mvi c,C_READSTR
		call bdos
		pop b
		xra a		; clear geti
		sta geti
		jmp getagain
		ret
skipfill:	mvi d,0		; set HL to buffer+geti
		lxi h,getbuf+2
		dad d

		inr e		; update geti
		mov a,e
		sta geti

		mov a,m		; get the character
		cpi 032		; ^Z, CP/M EOF
		jnz noeof
		xra a		; return 0 instead
noeof:		mov l,a
		mvi h,0
		ret

		.bss
reg0:		.ds 2		; virtual C registers
reg1:		.ds 2
reg2:		.ds 2
		.export reg0,reg1,reg2

		.text
_open:		.export _open	; fake open
		lxi h,-1
		ret

ccall:		.export ccall	; call (hl) fake
		pchl

crshift:	.export crshift		; shift hl right by de chars,
					; sign extending.
rloop:		mov a,e
		ora d
		rz			; return if no more chars
		dcx d
		mov a,h			; get sign into carry
		ral
		mov a,h
		rar			; shift w/ sign
		mov h,a
		mov a,l
		rar
		mov l,a
		jmp rloop

casnadd:	.export casnadd
		mov a,m
		add e
		mov e,a
		mov m,a
		inx h
		mov a,m
		adc d
		mov d,a
		mov m,a
		xchg
		ret
ccasnadd:	.export ccasnadd
		mov a,m
		add e
		mov m,a
		mov l,a
extend:		mvi h,0
		mov a,l
		ora a
		rp
		dcr h
		ret
casnsub:	.export casnsub
		mov a,m
		sub e
		mov e,a
		mov m,a
		inx h
		mov a,m
		adc d
		mov d,a
		mov m,a
		xchg
		ret
ccasnand:	.export ccasnand
		mov a,m
		ana e
		mov m,a
		mov l,a
		jmp extend
ccasnor:	.export ccasnor
		mov a,m
		ora e
		mov m,a
		mov l,a
		jmp extend

signed:		mov a,h		; carry=1 if hl<de
		xra d
		jp signed1
		xra h
		rm
		stc
		ret
signed1:	mov a,l
		sub e
		mov a,h
		sbb d
		ret

cless:		.export cless
		call signed
		lxi h,0
		rnc
		inx h
		ret
cgequ:		.export cgequ
		call signed
		lxi h,0
		rc
		inx h
		ret
clequ:		.export clequ
		mov a,l
		cmp e
		jnz cless
		mov a,h
		cmp d
		jnz cless
		lxi h,1
		ret
cgreat:		.export cgreat
		mov a,l
		cmp e
		jnz cgequ
		mov a,h
		cmp d
		jnz cgequ
		lxi h,0
		ret

culess:		.export culess
		mov a,l
		sub e
		mov a,h
		sbb d
		lxi h,0
		rnc		; borrow=hl less than de
		inx h
		ret
cugequ:		.export cugequ
		mov a,l
		sub e
		mov a,h
		sbb d
		lxi h,0
		rc
		inx h
		ret
culequ:		.export culequ
		mov a,l
		cmp e
		jnz culess
		mov a,h
		cmp d
		jnz culess
		lxi h,1
		ret
cugreat:	.export cugreat
		mov a,l
		cmp e
		jnz cugequ
		mov a,h
		cmp d
		jnz cugequ
		lxi h,0
		ret

cswitch:	.export cswitch	; stk=val,count,default,table
		.bss
savebc:		.ds 2
ldret:
cswdef:		.ds 2
		.export savebc,cswdef
		.text
		mov a,c		; frame pointer to savebc
		sta savebc
		mov a,b
		sta savebc+1
		pop d		; val to DE
		pop b		; count to BC
		pop h
		shld cswdef	; default to cswdef
		pop h		; table to HL

cswloop:	mov a,b		; check count
		ora c
		jz cswdodef
		dcx b		; dec count
		mov a,m		; check val lo
		inx h
		cmp e
		jnz cswnope
		mov a,m
		cmp d
		jnz cswnope
		inx h		; gottem! get label into HL, restore BC
		mov e,m		; label into DE
		inx h
		mov d,m
		xchg		; label into HL
		lda savebc
		mov c,a
		lda savebc+1
		mov b,a
		pchl		; jump to label!
cswnope:	inx h		; HL=val+1 on entry,needs to be val+4
		inx h
		inx h
		jmp cswloop
cswdodef:	lda savebc	; no match found, restore BC and default
		mov c,a
		lda savebc+1
		mov b,a
		lhld cswdef
		pchl

cmult:		.export cmult
		push b
		mov b,d
		mov c,e
		xchg
		mvi a,16
cmloop:		dad h
		xchg
		dad h
		xchg
		jnc cmskip
		dad b
cmskip:		dcr a
		jnz cmloop
		pop b
		ret

		.bss
ldwork:		.ds 4
ldrem:		.ds 2
ldneg:		.ds 1
		.export ldwork,ldrem,ldneg

		.text
uldiv:		.export uldiv	; unsigned divide ldwork by BC
				; quotient in ldwork, remainder in ldrem
		lxi h,0
		shld ldrem
		mvi e,32
ulhead:		mvi d,6		; shift ldwork-ldrem left 1 bit
		lxi h,ldwork
		xra a		; clear carry
ulshift:	mov a,m
		ral
		mov m,a
		inx h
		dcr d
		jnz ulshift
		lhld ldrem
		mov a,l
		sub c
		mov d,a
		mov a,h
		sbb b
		jc ulskip
		mov h,a
		mov l,d
		shld ldrem
		lda ldwork
		inr a
		sta ldwork
ulskip:		dcr e
		jnz ulhead
		ret

ldiv:		.export ldiv	; signed divide ldwork by bc
				; quotient in HL, remainder in ldrem
		lda ldwork+3
		xra b
		ani 0200
		sta ldneg
		mov a,b
		ora a
		jp ldposb
		cma
		mov b,a
		mov a,c
		cma
		mov c,a
		inx b
ldposb:		lda ldwork+3
		ora a
		jp ldposw
		lxi d,1
		lda ldwork
		cma
		add e
		sta ldwork
		lda ldwork+1
		cma
		adc d
		sta ldwork+1
		lda ldwork+2
		cma
		adc d
		sta ldwork+2
		lda ldwork+3
		cma
		adc d
		sta ldwork+3
ldposw:		call uldiv
		lhld ldwork
		lda ldneg
		ora a
		rp
		mov a,l
		cma
		mov l,a
		mov a,h
		cma
		mov h,a
		inx h
		ret

cdiv:		.export cdiv	; HL=HL/DE, unsigned
		push b
		mov b,d
		mov c,e
		shld ldwork
		mov a,h
		ora a
		lxi h,0
		jp cdpos
		dcx h
cdpos:		shld ldwork+2
		call ldiv
		pop b
		ret

cmod:		.export cmod	; HL=HL%DE, unsigned
		push b
		mov b,d
		mov c,e
		shld ldwork
		lxi h,0
		shld ldwork+2
		call uldiv
		lhld ldrem
		pop b
		ret

		.bss
_ldivr:		.export _ldivr
		.text
_ldiv:		.export _ldiv	;stk:ret,num-hi,num-lo,dennom
		lxi h,2
ldcommon:
		dad sp
		push b
		mov e,m
		inx h
		mov d,m
		inx h
		xchg
		shld ldwork+2
		xchg
		mov e,m
		inx h
		mov d,m
		inx h
		xchg
		shld ldwork
		xchg
		mov c,m
		inx h
		mov b,m
		call ldiv
		pop b
		xchg
		lhld ldrem
		shld _ldivr
		xchg
		ret

_lrem:		.export _lrem
		lxi h,4
		call ldcommon
		xchg
		ret
