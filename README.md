# C6T - C version 6 by Troy

C6T (pronounced "See Sixty") is an implementation of the version of the C programming language included with the 1975 version of Unix referred to as "Research Unix Sixth Edition" or "Unix V6." This version of C predates K&R C, and is missing most of the difficult to parse or codegen elements.

C6T is largely complete, requireing additional testing and support for more backends.

## Differences from Modern C

* Preprocessor only supports one-level includes (no system headers), and non-recursive non-parameterized defines.
* Initializers are only permitted in extern scope. Initializers do *not* have an equal sign; they are *not* assignments; they require expresions the linker can output (a constant, a *Name*, or a *Name* +/- a constant), are are output directly to backend as such. Function definitions can be thought of as a special case of initializer.
* Only two scopes - local and extern. Local scope is entered when starting a function definition; there is *not* block scoping at each compound statement. The only legal place to introduce locals is just after the left brace starting the function body. Declared/specified locals and externs also *share namespace*; locals are cleared out of the symbol table on exit of local scope. It is therefore illegal to declare/specify a local with the same name as a declared/specified extern. (Parsing modern C is made much trickier by the scoping system, which has weird interactions with typedefs/structs, and does not apply to goto labels).
* No typedefs.
* No shorts or longs.
* No bitfields.
* No qualifiers.
* Structs cannot be passed as arguments nor returned as values; only pointers to them may be.
* No one-line *//* comments.
* No unions.
* Tag scope (member and struct names) is shared. Struct tags cannot have the same name as member tags, and member tags are shared by all structs. The only identifying information structs contain is their size in bytes. It is legal to redeclare members as long as their type and offset from the start of the struct are the same.
* Member operations (`.` and `->`) can be applied to any expression, not just struct types. Therefore, unions may be easily synthesized. Additionally, memory-mapped I/O is supported by `#define`ing the address as an integer constant, and defining a struct for its register set. Then, `ADDR->member` will evalutate to the address of the register *member*.
* More specifically, the `.` operator requires the thing on its left to be an lvalue (an address or register), will add the offset of the member to it. The `->` operator works on any expression, and will 'rvalue' (load an address) whatever's on its left if it's an lvalue as usual.
* Register variables may not have their address taken, or have member operations applied to them.
* Static declared functions are not allowed; all externs are exported to the linker.
* Assignment operators are reversed (`=+` instead of `+=`).
* The only operators which support floating point are the comparisons `<`, `>`, `<=`, `>=`, `==`, `!=`; the assignment operator '=' (not other assignment operators like `=+`); the negation operator unary `-`; and the ordinary mathematical operators `+`,`-`,`*`,`/`.
* The null pointer is defined as 0.

## C6T Specific Alterations

* C6T's implementation guarentees integers as 16-little endian in an unaligned, 8-bit byte addressing system. It also guarentees signed 8-bit chars, and as-yet unspecified 4-byte floats and 8-byte doubles. C6T does not pad structs for alignment.
* C6T refers to declarations as "specifiers" and identifiers as "names".
* C6T *requires* exactly three integer-size register variables. If physical registers are not available, static/extern variables are to be used. It is not allowed to place them onto the auto stack.
* On most C6T backends, it's expected that extern/static access is at least as fast as autos (probably faster), and register access is at least as fast as extern/statics. It is recommended that locals be placed in registers as much as possible, and non-recursive functions place remaining locals into statics.
* C6T guarentees multiplications and divisions by constant powers of 2 will be converted to shift operations.
* Right shifts are always sign-extending.
* C6T defines modulo (`%`) as an unsigned operation, so that it can guarntee `%` something by a constant power of 2 will be transformed to `&` bitwise and'ing it by the power of 2 minus 1 (`% 4` becomes `& 3`).
* C6T guarentees the layout of the stack frame: from the frame pointer position up: register var 2, register var 1, register var 0, the previous frame pointer, and the previous program counter. Any further platform-specific information must be placed above the arguments to a function call.
* All C6T functions pass arguments on the stack. The stack is down-growing, and the first argument is at the lowest address, with further arguments above it. Because of this, you can implement varargs by getting the address of an argument. Arguments start above the stack frame (in other words, 10 bytes above the frame pointer).
* C6T does not check the number or type of arguments; because of this, arguments not used by a function don't have to be passed even if specified.

## Included Programs

Each program is written in C6T itself. There is a `run` shell script designed for Unix V6 in each directory for producing their executable(s).

It is recommended these be compiled on an actual PDP-11 or emulator running Unix V6, for the time being.

### CPP

The C6T preprocessor.

`cpp [FILENAME]` will place on standard output the preprocessed version of the input filename. If filename is not provided, standard input it used. If the file does not start with a `#` character, then it is not preprocessed, and the input is copied to standard output directly.

As noted above, the only directive are:

* `#include "FILENAME"` - place the filename in the current position. Only one include may be active at a time; one level deep. The C6T frontend uses the `@` character to flip a flag if it should count line numbers or not; these are inserted on either side of the include, so that line numbers are not tracked by the frontend inside one.
* `#define NAME ...`, will replace all occurences of NAME with the ... text. The text will have whitespace inside it replace with single spaces, and a space will be placed on either side of it.

Preprocessed lines must start with a `#` character, but any amount of whitespace is allowed between the `#` and the preprocessor command.

`#` lines without a recognized preprocessor command are ignored.

### C6T

The C6T frontend.

`c6t [FILENAME]` produces a C6TIR format representation of the C6T source in filename onto the standard output. If filename is not provided, standard input is used.

### C6TIR

The C6T backend.

Currently only one backend is supplied, for the Intel 8080 CPU. This will also work on the Zilog Z80, which is compatbile.

`i8080 [FILENAME]` will accept C6TIR representation from the source file, and produce assembly for the 8080 on standard output. If the filename is not provided, standard input is used.

New backends are **required** to use the *shared.c* file in the c6tir directory as their basis.

### AS80

An Intel 8080 assembler.

`as80 [-s START] [FILENAME]` will produce an output file, currently called *a.out.80*, though this may soon change to *a.out*. If filename is not provided, standard input is used.

The `-s` flag specifies a starting address in decimal for the ouput file; the default is 0.

It can easily become the basis for further assemblers, by modifying the YACC grammar and writing a new *opcode.c* file.

Labels are always followed by a colon. Multiple labels may be on the same line. Comments are started with the ';' character. Absolute symbols may be assign a value with `NAME = EXPRESSION`. The operators presently are '+', '-', '*', '/', negation, and the lo/hibyte operators '<'/'>'. '*' on its own refers to the program counter.

The pseudo-ops are:

* `.text`, `.data`, `.string`, `.bss`, to switch into the corresponding output segment (string segments get concatted onto the end of the data segm nt).
* `.common NAME,EXPRESSION` declares a 'common' symbol with the size of the expression. When the program is finally linked, if *any* linked file defines the corresponding name as non-common, all references use the non-common version. Otherwise, each common is appended to the *bss* segment with the maximum of its listed sizes.
* `.export NAME[,NAME...]` declares the given symbols as exported.
* `.db [EXPR,...]` places the given bytes at the present location.
* `.dw [EXPR,...]` places the given 16bit little-endian words at the present location.
* `.ds [EXPR]` places *expr* 0's at the present location.

### PopLink

Links together a.out.80 files into a new a.out.80 file.

`poplink [FLAGS] NAME[,NAME...]`

Supported flags are:

* `-s START` sets the start address to the given decimal offset.
* `-x` will not resolve commons, set the executable flag, or establish the "_etext"/"_edata"/"_end" symbols, allowing further output to be made on the output object file.

### Names/Psize

These programs are minor utilities working on a.out.80 files. Psize prints the size in decimal of the text,data, and bss segments, as well as the total size. Names displays the object file's symbol table.

### CC6T

This is the complete compiler manager.

`cc6t [ARG, ...]`

Each argument is examined in turn.

* If it is a flag cc6t recognizes, it is processed and then skipped.
* If it ends in '.s', it is assembled, and the a.out.80 is renamed to the base name of the filename with an '.o' extension. For instance, '../foo.s' becomes 'foo.o'. This object file is then sent to the linker in the current position at the end of argument parsing.
* If it ends in '.c', it is preprocessed, compiled thru frontend and backend, and assembled, and the a.out.80 is renamed to the basename of the file path with a '.o' extension. For instance, '../bar.c' becomes 'bar.o'. This object file is then sent to the linker in the current position at the end of argument parsing.
* All other arguments are sent to the linker in the current position at the end of argument parsing.

When all arguments have been read and handled, the `poplink` linker is called, with the arguments as indicated above, with the output on a.out.80.

The CC6T understood arguments are:

* `-P`: any '.c' files are run through the preprocessor only, resulting in a 'BASENAME.i' file. No linking is performed.
* `-S`: any '.c' files are run through the preprocessor, frontend, and backend, resulting in a 'BASENAME.s' assembly file. No linking is performed.
* `-c`: No linking is performed. C files will therefore be left as '.o' files.

When proper crt support libraries are available, cc6t will also link that in to the linker.

At the moment, a crt80.s support library providing partial support under the CP/M operating system is provided.
