# C6Tir

This is the intermediate representation used by the C6T frontend to talk to the C6T backend.

It can also be used to easily provide new frontends to the backend.

- [C6Tir](#c6tir)
  - [Environmental Guarantee](#environmental-guarantee)
    - [Addresses and Binary Data](#addresses-and-binary-data)
    - [Register Variables](#register-variables)
    - [The Stack and Calling Convention](#the-stack-and-calling-convention)
  - [Elements of the IR](#elements-of-the-ir)
  - [COMMANDS](#commands)
  - [NODES](#nodes)

## Environmental Guarantee

The order of evaluation of expression trees is *not* guaranteed *except* for function call arguments, the `COMMA` node, and the `LOGAND`/`LOGOR` nodes.

### Addresses and Binary Data

C6Tir guarantees several aspects of the operating environment. These may decrease speed of execution on certain platforms, but greatly simplify the issue of writing portable software compared to modern C solutions.

We assume a 16-bit address space, with each address unit specifying an 8-bit byte. Signed values are stored in two's complement. 16-bit *word* values are stored in a little-endian format.

The C6Tir `cload` routine assumes signed bytes - they are sign extended based on their high bit, according to two's complement.

*Word* values are not required to be aligned. If your platform requires alignment, you must synthesize unaligned loads and stores.

Executable code addresses are also not required to be aligned; if your system does require this, you may have some difficulties. An initial suggestion would be to make sure the end of every code routine pads itself to the alignment, as well as at *LABEL* definitions (in case we *goto* the *LABEL*). That way, the linker *should* (famous last words) link together all such code with proper alignment.

Since addresses are 16-bits, they are treated synonymously with integer *word*s. Access outside the 16-bit space should be handled with special calls to functions not written in C6Tir.

All integral operations are assumed to be performed in word size -- if your platform has registers greater than 16 bits in size, you may need to be careful that signed/unsigned and address operations are performed correctly.

### Register Variables

C6Tir guarantees the existence of three (no more, no less) *word* sized "register" variables. These *must not* be implemented on the stack as `auto`s. If not enough actual registers are available, `extern` variables are permitted. The recommendation is to name them "reg0", "reg1," and "reg2;" portable C6Tir code should avoid explicitly creating other labels with those names.

### The Stack and Calling Convention

There is the assumption of a large-size down-growing stack somewhere in memory.

C6Tir only pushes and pops *word* or `double` sized values onto the stack, so it could be 16-bit aligned if your CPU's stack requires such alignment. In the case of further alignment restrictions, you're on your own.

When a C6Tir function is called, any arguments to it are evaluated in reverse order and pushed onto the stack. So, `foobar(foo, bar)` would evaluate and push bar, then foo. The intention being the first argument has the lowest address.

When a C6Tir function is entered, the first thing it does is set up its stack frame.

The stack frame consists of several 16-bit values:

1. The return address.
2. The frame pointer value (see below).
3. The value of `REG` 0.
4. The value of `REG` 1.
5. The value of `REG` 2.

This has a total of 10 bytes. If any further information must be saved, it should be placed on the stack *above* the function call arguments. (This is one reason why `ARG` nodes are implemented the way they are).

After the stack frame is created, the frame pointer is given a new value, pointing to the lowest byte in the stack frame. Hence, the frame pointer + 10 points to the first byte of the first argument. Arguments and the stack frame can be accessed by using such an offset from the frame pointer, which is provided by the `AUTO` node.

The `usedregs` command indicates to the backend how many register variables are used by the current function, starting from `REG` 0. This information might be used, for instance, to let unused register variables be used for normal calculations. However, any such usage is solely for the backend's benefit, and that command can just as easily be ignored. `usedregs` may only be called at the start of a function, and only once.

The `autos` command, if given, must be given only once at the head of a function. It then lowers the stack by its given number of bytes, to provide for `auto` variables. The contents of `auto`s can be accessed by using a negative offset from the frame.

When a C6Tir function returns, either with an expression value or not, the stack is returned to a position above the frame pointer (where the stack pointed to when the function was entered), the contents of the register variables are restored from the stack frame, as is the frame pointer, and the return address is jumped to.

It is the responsibility of the caller to remove any arguments pushed onto the stack, and to remove any additional backend-dependent information placed above the arguments.

Since arguments are always passed on the stack, functions with a variable number of arguments are supported. You get the address of a known argument, then increment it to get from one argument to another. Below is an example in C6T code.

        average(count, elems)
        {
                register total;
                register i;
                register *argpnt;

                argpnt = elems;
                total = 0;
                for (i = 0; i < count; i++) {
                        total =+ *argpnt++;
                }
                return (total / count);
        }

        main()
        {
                printf("average %d\n", average(3, 4, 5, 6));
        }

## Elements of the IR

There are three primary elements:

- *LABELS*, consisting of a *NAME* followed by a ':' character. These are output to the assembly backend directly at the point they're encountered.
- *COMMANDS*, which produce output assembly or pseudo-ops. They consist of a command name, followed by any arguments as comma separated expressions. *COMMAND*s can also operate on...
- *NODES*, which construct an expression tree. Each node consists of the name of the node, followed by any arguments required by it as comma separated expressions. The nodes are specified postfix, and are placed by the IR onto a stack as encountered. Any arguments required by them will be popped off this stack.

Command and node names are recognized in upper, lower, or mixed case.

Many of these elements allow or require an inline argument. These arguments are of the form of a decimal integer constant, an unreserved name (reserved names include all nodes and commands), or a name '+'/'-' a constant. For instance, `WORD _foo+2`.

## COMMANDS

- `byte [ARG,...]`/`word [ARG,...]`: place literal bytes/words in the assembly output. The values placed are the comma-separated arguments.
- `storage ARG` places ARG count bytes with the value of 0 at the current location in the output.
- `autos ARG` specifies how many local variables the current function uses on the stack. May only be called once per function, before any commands which generate code.
- `usedregs ARG` specifies how many register variables are used by the current function. May only be called once per function, before any commands which generate code.
- `ret` *consumes the expression tree*, evaluates it, and returns its value from the current function.
- `retnull` returns from the current function without returning any value. On platforms where a value is required, a default of 0 will do. (The intention is platforms which return a value in a register may leave whatever is currently in there, while platforms which return a value on the stack can place a default).
- `func ARG` starts a new function with the name ARG.
- `export [ARG, ...]` marks the argument names as exported to the linker.
- `endfunc` marks the end of the current function. No code should be generated until another `func` is called, though other types of commands may be.
- `jmp ARG` assembles a jump to the address ARG.
- `brz ARG` *consumes the expression tree*, evaluating it, and jumps to the address ARG *only* if the result equals zero; if the result is nonzero, execution continues at the next instruction.
- `eval` *consumes the expression tree*, evaluating it, and then performing no further action. Any value generated is ignored except for side effects.
- `switch ARG1,ARG2,ARG3` *consumes the expression tree*, evaluating it. ARG1 contains the address of a table of the format `word VALUE, LABEL` repeating ARG3 times. Code is generated to compare the evaluated value to each entry in the table. If the VALUE matches the expression, the LABEL is jumped to. If no entries matched, ARG2 is jumped to.
- `end` ends the IR file; this is optional.
- `code`/`data`/`string`/`bss` enters the accompanying assembler segment. (The `string` segment is placed on the end of the `data` segment by the assembler).
- `stkjmp` *consumes the expression tree*, evaluating it, treats its value as an address, and jumps to it.
- `common ARG1,ARG2` defines name ARG1 to be a `common` (see below) with the size ARG2.
- `sweasy ARG1,ARG2,ARG3,ARG4` *consumes the expression tree*, evaluating it. Code is then generated to subtract ARG3 from this value; if it is >= ARG4, ARG2 is jumped to. Otherwise, the value is multiplied by two, and added to ARG1. ARG1 is a table of addresses; the resulting table entry is loaded and jumped to.

`sweasy` is produced by a C6T `switch` statement whose total range of case values is not too great compared to the number of cases; a table is produced with no values, only case label addresses. Any cases not present in the table have the default label address. That way, the table may be jumped into directly.

`common` labels are a major reason why a backend might require writing a new assembler (helpfully, C6T provides the `as80` assembler which is easy to modify for other CPUs). `common`s have an associated size; it is the unsigned maximum of all `common` sizes given for that label. If the label is defined as a non-`common` *anywhere*, in any linked object file, then all `common` references are assumed to be references to the non-`common`. However, if no such reference is found, the linker places the `common` at the end of the BSS segment, with its given size. This behavior is *required* by C6Tir, and allows C code to not worry about `extern` flagging data (which C6T does not even support). Multiple initializations of C6T data will still give an error, however.

## NODES

Below, `log`ing an operator consists of converting the value to 1 if it is nonzero, 0 otherwise. `lognot`ing is the reverse; 0 if nonzero, 1 if zero. This step, as well as the `log` and `lognot` nodes can be skipped if the value is used as the target of a conditional branch - just be sure `lognot`ed nodes have their branch condition reversed.

- `null`: No children. Pushes a null pointer onto the expression stack. Used by `call` and `arg`.
- `con ARG`: No children. An integer constant with ARG value.
- `load`: One child. Treats the child as an address, loading the integer value at that address.
- `cload`: One child. Treats the child as an address, loading the signed byte value at that address.
- `assign`: Two children. Treats the left child as an address. Stores the right child at that integer address.
- `cassign`: Two children. Treats the left child as an address. Stores the right child at that byte address.
- `quest`: Two children. The left part of the C6T `... ? ... : ...` operator. The right child must be a `colon` node. The left child is evaluated; if it is non-zero, the left child of `colon` is evaluated; otherwise, the right child of `colon` is used.
- `colon`: Two children. See `quest` above.
- `logor`: Two children. The left child is evaluated. The right child is only evaluated if the left child is zero. The result is `log`ed.
- `logand`: Two children. The left child is evaluated. The right child is evaluated only if the left child is nonzero. The result is `log`ed.
- `or`: Two children. They are bitwise or'd.
- `eor`: Two children. They are bitwise exclusive-or'd.
- `and`: Two children. They are bitwise and'd.
- `equ`: Two children. The result is a `log` flag for if they are equal.
- `nequ`: Two children. The result is a `log` flag for if they are not equal.
- `less`: Two children. The result is a `log` flag for if the left is less than the right.
- `great`: Two children. As less but left greater than right.
- `lequ`: Two children. As less but left less than or equal to right.
- `gequ`: Two children. As less but left greater than or equal to right.
- `rshift`: Two children. The left child is shifted the number of bits in the right child, with the result sign extended in the high bits.
- `lshift`: Two children. The left child is shifted the number of bits left in the right child, with the result zero-filled in the low bits.
- `add`: Two children. They are summed.
- `sub`: Two children. The result is the left minus the right.
- `mult`: Two children. They are multiplied, signed.
- `div`: Two children. The result is the left divided by the right, signed.
- `mod`: Two children. The result is the unsigned modulo of the left by the right. The assumption is `%` will be used more often for C6T address arithmetic and indexing than for proper mathematics.
- `neg`: One child. The result is the two's complement of the child.
- `lognot`: One child. The result is 0 if the child is nonzero, 1 otherwise.
- `log`: One child. The result is 0 if the child is zero, 1 otherwise.
- `compl`: One child. The result is its one's complement.
- `reg ARG`: No children. The result is the register with the number ARG; this ARG must range from 0 through 2. It requires special usage: it is not possible to treat a `reg` raw like a con, because you cannot get the address of a register. Accordingly, you may `load` it, `assign` it (or use one of the `asn...` operators), and `post`/`pre` it. These are the only legal operations.
- `pre ARG`/`post ARG`/`cpre ARG`/`cpost ARG`: One child. Pre- / post-increment/decrement the child by ARG. These implement the C6T `++`/`--` operators; their child is an address or `reg`. Decrementing by using a negative ARG. `cpre`/`cpost` expect a char address, `pre`/`post` work on integer addresses. ARG is added to the value inside the address; `pre`/`cpre`'s resulting value is after the addition, `post`/`cpost` result in the value inside the address beforehand.
- `call`: Two children. The left child is a chain of `arg` nodes or else `null`. They are pushed onto the stack if non-null. The right child is the address of a function to be called. The function is then called, after which the arguments are removed from the stack. Any return value from the function is then available as the resulting value.
- `arg`: Two children. A child may be `null`. Any non-null children are pushed onto the stack, the left node going first.
- `uless`/`ugreat`/`ulequ`/`ugequ`: Two children. As `less`/etc., but unsigned.
- `auto ARG`: No children. Result is the current frame pointer offset by ARG. Since the 16bit address space is the same size as integers, ARG is treated as signed.
- `asnadd`/`asnsub`/`asnmult`/`asndiv`/`asnmod`/`asnrshift`/`asnlshift`/`asnand`/`asneor`/`asnor`/`casnadd`/`casnsub`/`casnmult`/`casndiv`/`casnmod`/`casnrshift`/`casnlshift`/`casnand`/`casneor`/`casnor`: Two children. The left child is an address; those starting with `c` are byte addresses, the rest integers. The left child is evaluated *once*. The operator indicated after the `asn`/`casn` is performed on the value at the left child's address, and the right child. The result is then stored back in the left child address, and the final value is that of the operation's result.
- `comma`: Two children. The left child is evaluated, then the right child. The result is the value of the right child.
