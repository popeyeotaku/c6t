start:_start:jmp _reset
.dw _savearea
.dw _clock
.bss
_savearea:.export _savearea
.ds 2+2+2+6
.text
_reset:
name _secs
load
con 2
gequ
brz _reset
name _start
name _secs
load
assign
jmp 65535
_clock:
name _temp
preinc 1
con 60
gequ
brz nosec
name _secs
preinc 1
drop
name _temp
con 0
assign
drop
nosec:
irqret
.data
_temp:.dw 0
_secs:.dw 0
