# C6TIR

This is the intermediate representation used by the C6T frontend to talk to the C6T backend.

It can also be used to easily provide new frontends to the backend.

## Elements of the IR

There are three primary elements:

* *LABELS*, consisting of a *NAME* followed by a ':' character. These are output to the assembly backend directly at the point they're encounted.
* *COMMANDS*, which produce output assembly or pseudo-ops. They consist of a command name, followed by any arguments as comma seperated expressions. *COMMAND*s can also operate on...
* *NODES*, which consruct an expression tree. Each node consists of the name of the node, followed by any arguments required by it as comma seperated expresisons. The nodes are specified postfix, and are placed by the IR onto a stack as encountered. Any arguments required by them will be popped off this stack.

Command and node names are recognized in upper or lower case.

## COMMANDS

* `byte [ARG,...]`/`word [ARG,...]`: place literal bytes/words in the assembly output. The values placed are the comma-seperated arguments.
* `storage ARG` places ARG count 0 bytes at the current location in the output.
* `autos ARG` specifies how many local variables the current function uses on the stack.
* `usedregs ARG` specifies how many register variables are used by the current function.
* `ret` *consumes the expression tree*, evaluates it, and returns its value from the current function.
* `retnull`  returns from the current function without returning any value.
* `func ARG` starts a new function with the name ARG.
* `export [ARG, ...]` marks the argument names as exported to the linker.
* `endfunc` marks the end of the current function.
* `jmp ARG` assembles a jump to the address ARG.
* `brz ARG` *consumes the expression tree*, evaluating it, and jumping to the address ARG if the result equals zero.
* `eval` *consumes the expression tree*, evaluating it, and then performing no further action.
* `switch ARG1,ARG2,ARG3` *consumes the expression tree*, evaluating it. ARG1 contains the address of a table of the format `word VALUE, LABEL` repeating ARG3 times. Code is generated to compare the evaluated value to each entry in the table. If the VALUE matches the expression, the LABEL is jumped to. If no entries matched, ARG2 is jumped to.
* `end` ends the IR file; this is optional.
* `code`/`data`/`string`/`bss` enters the accompanying assembler segment. (The `string` segment is placed on the end of the `data` segment by the assembler).
* `stkjmp` *consumes the expression tree*, evaluating it, treating its value as an address, and jumping to it.
* `common ARG1,ARG2` defines name ARG1 to be a `common` (see as80 in readme.md) with the size ARG2.
* `sweasy ARG1,ARG2,ARG3,ARG4` *consumes the expression tree*, evaluating it. Code is then generated to subtract ARG3 from this value; if it is >= ARG4, ARG2 is jumped to. Otherwise, the value is multiplied by two, and added to ARG1. ARG1 is a table of addresses; the resulting table entry is loaded and jumped to.

`sweasy` is produced by a C6T `switch` statement whose total range of case values is not too great compared to the number of cases; a table is produced with no values, only case label addresses. Any cases not present in the table have the default label address. That way, the table may be jumped into directly.

## NODES

Below, `log`ing an operator consists of converting the value to 1 if it is nonzero, 0 otherwise. `lognot`ing is the reverse; 0 if nonzero, 1 if zero. This step, as well as the `log` and `lognot` nodes can be skipped if the value is used as the target of a branch - just be sure `lognot`ed nodes have their branch reversed.

* `null`: No children. Pushes a null pointer onto the expression stack. Used by `call` and `arg`.
* `con ARG`: No children. An integer constant with ARG value.
* `load`: One child. Treats the child as an address, loading the integer value at that address.
* `cload`: One child. Treats the child as an address, loading the signed byte value at that address.
* `assign`: Two children. Treats the left child as an address. Stores the right child at that integer address.
* `cassign`: Two children. Treats the left child as an address. Stores the right child at that byte address.
* `quest`: Two children. The left part of the C6T `... ? ... : ...` operator. The right child must be a `colon` node. The left child is evaluated; if it is non-zero, the left child of `colon` is evaluated; otherwise, the right child of `colon` is used.
* `colon`: Two children. See `quest` above.
* `logor`: Two children. The left child is evaluated. The right child is only evaluated if the left child is zero. The result is `log`ed.
* `logand`: Two children. The left child is evaluated. The right child is evaluated only if the left child is nonzero. The result is `log`ed.
* `or`: Two children. They are bitwise or'd.
* `eor`: Two children. They are bitwise exclusive-or'd.
* `and`: Two children. They are bitwise and'd.
* `equ`: Two children. The result is a `log` flag for if they are equal.
* `nequ`: Two children. The result is a `log` flag for if they are not equal.
* `less`: Two children. The result is a `log` flag for if the left is less than the right.
* `great`: Two children. As less but left greater than right.
* `lequ`: Two children. As less but left less than or equal to right.
* `gequ`: Two children. As less but left greater than or equal to right.
* `rshift`: Two children. The left child is shifted the number of bits in the right child, with the left child sign extended in the high bits.
* `lshift`: Two children. The left child is shifted the number of bits left in the right child, with the left child zero-filled in the low bits.
* `add`: Two children. They are summed.
* `sub`: Two children. The result is the left minus the right.
* `mult`: Two children. They are multiplied, signed.
* `div`: Two children. The result is the left divided by the right, signed.
* `mod`: Two children. The result is the unsigned modulo of the left by the right.
* `neg`: One child. The result is the two's complement of the child.
* `lognot`: One child. The result is 0 if the child is nonzero, 1 otherwise.
* `log`: One child. The result is 0 if the child is zero, 1 otherwise.
* `compl`: One child. The result is its one's complement.
* `reg ARG`: No children. The result is the register with the number ARG, from one to three May be loaded, inc/dec'd, or assigned; in general, its address may not be used.
* `pre ARG`/`post ARG`/`cpre ARG`/`cpost ARG`: One child. Pre/post increment/decrement the child by ARG. These implement the C6T `++`/`--` operators; their child is an address or `reg`. Decrementing by using a negative ARG. `cpre`/`cpost` expect a char address, `pre`/`post` work on integer addresses. ARG is added to the value inside the address; `pre`/`cpre`'s resulting value is after the addition, `post`/`cpost` result in the value inside the address beforehand.
* `call`: Two children. The left child is a chain of `arg` nodes or else `null`. They are pushed onto the stack if non-null. The right child is the address of a function to be called. The function is then called, and the arguments are removed from the stack. Any return value from the function is then available as the resulting value.
* `arg`: Two children. A child may be `null`. Any non-null children are pushed onto the stack, the left node going first.
* `uless`/`ugreat`/`ulequ`/`ugequ`: Two children. As `less`/etc, but unsigned.
* `auto ARG`: No children. Result is the current frame pointer offset by ARG. Since the 16bit address space is the same size as integers, ARG is treated as signed.
* `asnadd`/`asnsub`/`asnmult`/`asndiv`/`asnmod`/`asnrshift`/`asnlshift`/`asnand`/`asneor`/`asnor`/`casnadd`/`casnsub`/`casnmult`/`casndiv`/`casnmod`/`casnrshift`/`casnlshift`/`casnand`/`casneor`/`casnor`: Two children. The left child is an address; those starting with `c` are byte addresses, the rest integers. The left child is evalutated *once*. The operator indicated after the `asn`/`casn` is performed on the value at the left child's address, and the right child. The result is then stored back in the left child address, and the final value is that of the operation's result.
* `comma`: Two children. The left child is performed, then the right child.
