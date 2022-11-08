# C6T Grammar

The C6T Grammar is specified here using EBNF.

## External Definitions

A C6T program is a series of external definitions.

### C6T Program

    program = {extdef};

    extdef = [typeclass] (datadef|funcdef);

An external definition defines data or functions in external (global) scope.

### Data definition

    datadef = dataelem {',' dataelem} [','] ';';

A data definition announces that a piece of data exists, optionally initializing its value.

    dataelem = funcdecl | (datadecl initializer);

Function type data cannot be initialized -- use function definitions for that.

### Initializers

    initializer = noinit | init;

    noinit = ['{' '}'];

Defined data without an initializer are assumed to refer to a block of data the size indicated by the type of the declaration, in a read/write memory segment, whose value is all set to 0 bytes at program start. This is done by marking the data as a **common** label to the linker.

If the linker brings in *any* C file that initializes the data so that it is not **common**, that is used as the final location of the file. Otherwise, the linker tacks all **common** data to the end of the **bss* segment at the maximum of all sizes it was declared to have across all files.

    init = initexpr | '{' initlist '}' ;

C6T initializers do not contain the leading '=' operator seen in modern C. Do *not* think of them as an assignment. They can only exist in extern scope.

Initializers are output directly inline to the assembler: `int foo 2, *bar &foo;` assembles something to the effect of

    _foo: .dw 2
    _bar: .ds _foo

It is assumed the linker can properly handle expressions consisting of a constant, a label, or a label +/- an integer constant. These are the only guarentees for what the linker can handle.

Accordingly, the only valid expressions which may be used in an initializer are a constant, an address, or a constant +/- an address (the laster useful in indexing into arrays).

There is special handling in the case floating point values. Due to how initializers work, based on the declared type, a single output format is found: char, int (assumed synonymous with pointer), float, or double. If outputting a float, double type constants are converted accordingly BUT INTEGER FORMAT ARE NOT. So, `float foo[] { 1.0, 2.0, 3 };` outputs as:

    _foo: .df 1.0, 2.0
    .dw 3

Similarly, a floating constant in a non-floating type initializer gets output accordingly. `int foo[] { 1, 2, 3.0 };` becomes

    _foo: .dw 1,2
    .dd 3.0

There are no multi-depth level initializer lists. A multidimension array must be handled flatly:

    int foobar[4][2] {
        1,2
        3,4
        5,6
        7,8
    };

Since struct members do not attach to any particular struct, it is not possible (nor in our case desired) for struct initializers to work properly. Parsing a struct initializer is, in fact, one of the most difficult parts of parsing modern C code. Accordingly, a struct initializer simply outputs a series of ints (or doubles if a floating constant is used).

    struct foobar { struct foobar *foo; double bar; } list[] {
        0, 1.0,
        list, 2.0,
        &list[1], 3.0
    };

translates to:

    _list: .dw 0
    .dd 1.0
    .dw _list
    .dd 2.0
    .dw _list+10
    .dd 3.0

### Function Definitions

    funcdef = funcdecl paramtypes '{' locals {statement} '}';

It might help to think of function definitions as a special case of data initializer for function types.

    paramtypes = typedecls ;

 The function declaration contains the names of any parameters; this series of declarations specifies their types.

    locals = typedecls ;

There is only one level of scope. It is illegal for any locals declared here to overwrite the name of a declared extern; externs not declared but added by the linker, or else declared later in the same C6T source file, may legally have the same name (C6T is a linear language).

When the parser exits the function definition, any local declarations or struct/members specified, will be removed from the parser's symbol table, as though they do not exist.

## Declarations

## Statements

## Expressions
