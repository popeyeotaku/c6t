# C6T Grammar

The C6T Grammar is specified here using EBNF.

## Lexical Conventions

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

A special case of initializer is a constant **STRING** for an declarator of type *array of char* (**not** *pointer to char*). Ordinarily, strings are stored in the data segment, with expressions evaluating to a pointer to them -- `char *foo "0";` evalutates something like:

    _foo: .dw L1
    L1 .dc 48,0

An array of char initialized in this way instead stores the string inline -- `char foo[] "0";` translates as:

    _foo: .dc 48,0

The difference in operation is that a char* data def may be re-assigned to a different pointer, while in this form it may not, but there is a saving in storage. Be intentional about which you employ.

A declarator whose outermost type modifier is an array, automatically adjusts the size that dimension by the size of the initialized elements.

### Function Definitions

    funcdef = funcdecl paramtypes '{' locals {statement} '}';

It might help to think of function definitions as a special case of data initializer for function types.

    paramtypes = typedecls ;

 The function declaration contains the names of any parameters; this series of declarations specifies their types.

    locals = typedecls ;

There is only one level of scope (excluding struct/member tags, which have their own). It is illegal for any locals declared here to overwrite the name of a declared extern; externs not declared but added by the linker, or else declared later in the same C6T source file, may legally have the same name (C6T is a linear language).

When the parser exits the function definition, any local declarations or struct/members specified, will be removed from the parser's symbol table, as though they do not exist.

## Declarations

Declarations are used to specify the type and name of an object.

    typedecls = {typedecl};

A type declaration list is used in a variety of places, usually with some special logic as to what it wants to do with the declaration.

    typedecl = typeclass [decl {',' decl} [',']] ';';

A type declaration line constists of a base type and storage class, followed by an optional line of declarators, and a final semicolon.

    typeclass = type class | class type | type | class ;

A typeclass specifies a base type and/or a storage class for the current declaration line. Whereas in modern C, any number of tagged are incorporated into this section, the C6T language only has these two.

    type = 'int' | 'char' | 'float' | 'double' | 'struct' structdef ;

A base type specification.

- **int**: a signed 16-bit, two's complement, little endian integer. Most of the system is geared around the int being a fundamental system type.
- **char**: a signed 8-bit, two's complement integer. The high bit is used as a sign bit, with the value in the lower 7 bits.
- **float**: an 4-byte floating point value. A later version of the C6T language may specifically define the format of floats, not necessarily the same as IEEE, since it is not expected C6T will be used for serious number-crunching.
- **double**: an 8-byte floating point value. At the point in development of C which C6T is based upon, floating point values have been awkwardly kludged into the existing language, and are not as widely supported as in even K&R C.
- **struct**: Structs are not quite a real data type, and are not well integrated into the surrounding system. A struct is treated as a block of data with a arbirtrary size in bytes. The only legal operations on a struct are to get its address, or perform a member operator (**.** or **->**).

These base types are tacked onto the end of following declarators. If no base type is specified in a type class, **int** is assumed.

    structdef = NAME members | NAME | members;

Struct and member tag **names** exist in their own scope seperate from other **NAME**s. It is illegal to have a struct tag share the same name as a member tag or vice versa.

In the first form, the members are processed, and their total size is assigned to a struct tag with the given **NAME**. It is illegal to assign a struct tag NAME more than once. The returned base struct size is the size of the members.

In the second form, the **NAME** must be an already existing struct tag, and that tag's size is returned as the size of the base type struct.

In the third form, the size of the members are returned, and no struct tag name is set.

    members = '{' typedecls '}';

Each type declaration specifies a single member tag. Each of these tags is assigned its corresponding type, and an offset in bytes from the start of the member list. The first member has an offset of 0, the next member is offset to start at the first byte after the size of the previous member, and so on.

`struct { int foo; char bar; float foobar; }`

evaluates to member *foo* with offset *0*, member *bar* with offset *2*, member *foobar* with offset *3*, and a total size of seven bytes.

It is legal to redefine a member as long as it has the same type and offset. This is useful since C6T does not have members.

    struct foobar { int foo; double bar; };
    struct { int foo; char cbar[8]; };

In other words, it is useful to have structs with the same initial part but varying equivalent later parts (for instance, to store nodes with different value types). Ordinarily a union would reserve the maximum of the space required by all the given types; since C6T has no alignment and clearly defines the size of all data elements, this may be done -- albeit awkwardly -- by the poor programmer.

    class = 'extern' | 'auto' | 'static' | 'register';

Storage classes specify the manner in which data appears in memory.

- **extern**: specifies a normal global assembly label name, with a '_' prepended on it to avoid interference with specific assembler names.
- **auto**: Stored as an offset from the current frame pointer position (see the commentary on expression calls below). Locals are stored as an offset below the frame pointer, and function arguments as an offset above.
- **static**: The same as extern, but a temporary local label (starting with a capital 'L') is used instead. C6T also uses these for elements such as control flow.
- **register**: These refer to one of the three integer fast registers of the C6T system. If the backend implementation cannot actually store them into registers, it may store them as invisible externs. They MUST be int/char or pointer type, no other types are valid. They are assigned to the target registers in the order seen -- if there are too many, they are invisibly converted to auto registers. Registers are special cased in that *IT IS ILLEGAL TO DO ANY OPERATION WHICH WOULD GET THEIR ADDRESS*. You may only load or store their values.

In general: statics and externs are at least as fast to access as autos; statics and externs are equally fast to access; registers are at least as fast to access as statics and externs; register variables might increase in speed the earlier they are declared in the local type declaration list.

According to these rules, it is recommended to use register variables as much as possible, and to use statics where ever you know a function will not employ the data recursively. Using externs extensively is not necessarily a problem wrt state if your program is simple enough.

If a storage class is not listed in a typeclass, auto is assumed if inside local scope; in other cases, extern is assumed. However, extern is always assumed for functions, since you cannot compile one onto the stack or into a register.

If a storage class specifier is used in a context where the required class is known (anywhere except a local type declaration list), the storage class specified is ***ignored***, and the required one is employed instead. `auto foo(bar) static bar; { return (bar); }` will place foo as an extern class, and bar as an auto class.

    decl = datadecl | funcdecl;

A data or function declarator.

    datadecl =
        NAME |
        '*' datadecl
        | datadecl '(' ')'
        | datadecl arraydecl
        | '(' datadecl ')'
    ;

    arraydecl =
        '[' ']'
        | '[' conexpr ']'
    ;

A **NAME** specifies the name used for the declarator, and the current base type is inserted here. It has the highest priority.

A **\*** binds right to left, has lower priority than **NAME**, and prepends a *POINTER TO ...* onto the current type string.

A **()** binds left to right, is lower priority than **NAME** but higher priority than **\***, and prepends a *FUNCTION RETURNING ...* onto the current type string.

An array declarator binds left to right, is lower priority than **NAME** but higher priority than **\*** and equal priority to **()**, and prepends *ARRAY OF SIZE ... OF ... ELEMENTS* onto the current type string.

An array declarator of the form `[]` specifies an array of one element. An array declarator with a constant expression instead specifies an array of that many elements.

The size of a type is calculable as follows in bytes:

- **int**: 2
- **char**: 1
- **float**: 4
- **double**: 8
- **struct**: the specified struct size
- **pointer**: 2
- **func**: 0, function types should not be used in a context where this value would be useful
- **array**: the size of the rest of the typestring multiplied by the number of elements in this array modifier.

**int**, **char**, **float**, **double**, and **struct** can be described as a *base type*. **pointer**, **function**, and **array** can be described as modifier types.

    funcdecl =
        NAME '(' [paramnames] ')'
        | '*' funcdecl
        | funcdecl '(' ')'
        | funcdecl arraydecl
        | '(' funcdecl ')'
    ;

Function declarators start with the function spec immediately after the **NAME** -- otherwise they are identical to data declarators. This is the great parsing issue in C6T: the type of a declarator must be known to properly parse an external definition (modern C has a great many larger troubles).

The NAME '(' ... ')' form should be regarded identically to the data declarator form of NAME followed by '(' ')'.

    paramnames = NAME {',' NAME} [','];

Paremeter names are assigned positions on the stack such that the first name is at the lowest memory position, with furst names increasing in address.

## Statements

## Expressions
