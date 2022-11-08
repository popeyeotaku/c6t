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

 The function declaration contains the names of any parameters; this series of declarations specifies their types. It is illegal to set a struct type for a parameter; array types are converted to pointers to the corresponding element, bare floats are converted to doubles, and bare chars are converted to ints.

    locals = typedecls ;

There is only one level of scope (excluding struct/member tags, which have their own). It is illegal for any locals declared here to overwrite the name of a declared extern; externs not declared but added by the linker, or else declared later in the same C6T source file, may legally have the same name (C6T is a linear language).

When the parser exits the function definition, any local declarations or struct/members specified, will be removed from the parser's symbol table, as though they do not exist.

## Declarations

Declarations are used to specify the type and name of an object.

### Type Declarators

    typedecls = {typedecl};

A type declaration list is used in a variety of places, usually with some special logic as to what it wants to do with the declaration.

    typedecl = typeclass [decl {',' decl} [',']] ';';

A type declaration line constists of a base type and storage class, followed by an optional line of declarators, and a final semicolon.

### Type Class

    typeclass = type class | class type | type | class ;

A typeclass specifies a base type and/or a storage class for the current declaration line. Whereas in modern C, any number of tagged are incorporated into this section, the C6T language only has these two.

### Base Type

    type = 'int' | 'char' | 'float' | 'double' | 'struct' structdef ;

A base type specification.

- **int**: a signed 16-bit, two's complement, little endian integer. Most of the system is geared around the int being a fundamental system type.
- **char**: a signed 8-bit, two's complement integer. The high bit is used as a sign bit, with the value in the lower 7 bits.
- **float**: an 4-byte floating point value. A later version of the C6T language may specifically define the format of floats, not necessarily the same as IEEE, since it is not expected C6T will be used for serious number-crunching.
- **double**: an 8-byte floating point value. At the point in development of C which C6T is based upon, floating point values have been awkwardly kludged into the existing language, and are not as widely supported as in even K&R C.
- **struct**: Structs are not quite a real data type, and are not well integrated into the surrounding system. A struct is treated as a block of data with a arbirtrary size in bytes. The only legal operations on a struct are to get its address, or perform a member operator (**.** or **->**).

These base types are tacked onto the end of following declarators. If no base type is specified in a type class, **int** is assumed.

### Structs

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

It may be useful to specify struct sizes as a power of 2, since that will aid in pointer arithmetic when indexing arrays.

### Storage Class

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

### Declarators

    decl = datadecl | funcdecl;

A data or function declarator.

### Data Declarators

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

A **\*** binds right to left, has lower priority than **NAME**, and prepends a *POINTER TO ...* onto the current type string. ***POINTERS ARE GUARENTEED TO BE EQUIVALENT TO PHYSICALLY INTS***.

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

### Function declarators

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

    statement = 
        NAME ':' statement
        | IF '(' expr ')' statement [ELSE statement]
        | WHILE '(' expr ')' statement
        | DO statement WHILE '(' expr ')' ';'
        | FOR '(' [expr] ';' [expr] ';' [expr] ')' statement
        | SWITCH '(' expr ')' statement
        | CASE conexpr ':' statement
        | DEFAULT ':' statement
        | BREAK ';'
        | CONTINUE ';'
        | RETURN ';'
        | RETURN '(' expr ')' ';'
        | GOTO expr ';'
        | ';'
        | '{' {statement} '}'
        | expr ';'
    ;

A statement assembles executable code for the current function.

## Labels

    NAME ':' statement

This places a static goto label in front of a statement. Goto labels have type *array of one int*, although you should not rely on the array dimension; it is employed so that its address will not be loaded in a **GOTO** statement.

## If Statement

    IF '(' expr ')' statement [ELSE statement]

The **IF** statement evaluates the leading expression; if it is equal to 0, the first statement will be skipped. In the event of an ELSE, the second statement is evaluated only if the expression is equal to 0.

Something to the effect of:

    /* expr */
    brz L1
    /* true-statement */
    jmp L2
    L1: /* false-statement */
    L2:

if else is employed,

    /* expr */
    brz L1
    /* true-statement */
    L1:

if else is not employed.

### While Statement

    WHILE '(' expr ')' statement

As long as the expression evalutes as non-zero, the statement is executed.

Something to the effect of:

    continue_label:
    /* expr */
    brz break_label
    /* statement */
    jmp continue_label
    break_label:

where continue_label and break_label specify the targets of continues and breaks.

### Do Statement

    DO statement WHILE '(' expr ')' ';'

The statement is executed, and then re-executed as long as the expression is non-zero. In other words, an equivalent to while with the test at the end, and which always executes at least once.

Something to the effect of:

    L1:
    /* statement */
    continue_label:
    /* expr */
    brz break_label
    jmp L1
    break_label

where continue_label and break_label specify the targets of continues and breaks.

### For Statement

    FOR '(' [expr] ';' [expr] ';' [expr] ')' statement

The first optional expression is executed. The second (if present) is used as a test; the statement is executed as long as the test expression evaluates to non-zero. If the test expression is not present, the statement always executes. Finally, the third expression is used as an update.

Something to the efect of:

    /* first expr */
    L1: /* second expr */
    brz break_label
    /* statement */
    continue_label:
    /* third expr */
    jmp L1
    break_label

where continue_label and break_label specify the targets of continues and breaks.

### Switch Statement

    SWITCH '(' expr ')' statement

The statement contains any number of **CASE** labels, and one optional **DEFAULT** label. If the default label is not specified, the switch's break label is used.

The expression is evaluated, and the **CASE** whose constant expression equals the expression's value is jumped to. If none match, the default/break label is jumped to.

***THIS IS ALWAYS DONE VIA TABLE LOOKUP***. There may be optimizations as to which kind of table, which may at a later time be clearly defined, but -- unlike an *if-else if* chain, this is always a table lookup. Use accordingly as you would such a table in assembly.

A break label is produced after execution of the switch statement.

### Case Statement

    CASE conexpr ':' statement

Introduces a case label for the statement to the innermost enclosing switch statement. The value of the constant expression is used for the value the switch statement uses to jump into the appropriate statement.

It is illegal to use a case statement outside of any switch.

### Default Statement

    DEFAULT ':' statement

Introduces a default label for the statement ot the innermost enclosing switch statement. It is illegal to have more than one in a switch. If no cases match, the switch statement will jump to here.

It is illegal to use a default statement outside of any switch.

### Break and Continue Statements

    BREAK ';'

or

    CONTINUE ';'

will jump to the innermost enclosing break or continue label introduced by statement structres as described above.

It is illegal to use when there is no such label introduced.

### Return Statements

    RETURN ';'

or

    RETURN '(' expr ')' ';'

will return from the current function. The first implements a so-called 'null return' with no value, while the second will return with the given expression value.

Sadly the behavior of using the value of a null-return function is undefined.

It is not guarenteed the type of the returned value will be matched up to that of the function -- a non-floating function may return a double if the expression is floating type, or vice versa.

### Goto Statement

    GOTO expr ';'

Evaluates the expression and jumps to it. You may load any number or variable here, not only case labels -- ***BUT UNLESS YOU KNOW WHAT YOU ARE DOING ON YOUR BACKEND AND DON'T DESIRE PORTABILITY***:

- **goto** a local goto label within the function.
- *Or*, **goto** a variable of type pointer to int, whose value is either an address inside this function (it's been set to a local label) *OR* whose code resets the stack in some way (equivalent to modern C's longjmp()).

***BE VERY VERY WARY OF USING THIS SECOND FORM AT ALL***

Despite these deadly warnings, goto's are not the worst thing in the world. Avoiding refactoring nested loops to get from point A to point B where breaks/continues may not help, or else having a standard error handler within a function, may be more clearly implemented with gotos. Having a weird flag variable may be more confusing than simply saying 'goto loop;'

### Null Statements

    ';'

Does nothing and outputs no code.

### Compound Statements

    '{' {statement} '}'

Executes those statements in sequence; it is equivalent to placing multiple statements where one is required.

Note that, unlike later C, there is no proper block structure, and compound statements do not have their own scope.

### Expression Statements

    expr ';'

The statement is evalutated and its value discarded.

## Expressions

Expressions are described from the highest priority at level 1, to the lowest at level 15.

### Standard Type Conversions

In binary operators, the rule usually is:

    - either side floating type, the non-float gets converted to double and the resulting type is double
    - either side pointer, an integral side if any gets multiplied by the size of what the pointer points to, and the resulting type is that of the pointer. If both sides are different pointers, the resulting type is indeterminate, but *probably* the type of the one on the left.
    - otherwise, the type is int.

A function type not used in a call operation gets a unary '&' prepended to it, so that it is a pointer to the function.

An array type used outside of a unary '&' operation gets a unary '&' prepended, whose type is a pointer to what the array is of. In other words, the array is converted to the address of its contents.

As an example, `int foo[5][10], *bar &foo[1][1];` will evaulate the initializer for bar as follows:

1. foo is array of 5 arrays of 10 ints, so is converted to unary & (address of) pointer to array of 10 ints.
2. this is added to 1 multiplied the 1 by 20 (the size of 10 ints) according to pointer arithmetic, and the result dereferenced
3. the resulting type is dereference 20 + pointer to array of 10 ints; since that's an array type, it is converted to unary '&' of pointer to int, and the '&' and '*' cancel out, so the resulting type is pointer to int
4. this is added to 1 multiplied by 2 according to pointer arithmetic, and the result is dereferenced.
5. 5he resulting type is int, since we dereference the pointer type. However, the specified unary '&' in the expression makes this an address, suitable for an initializer.

And the resulting assembly would be:

    _bar: .dw _foo+22

Expressions are internally evaluated as either int-sized or double-sized; pointers are done inside ints. Char and Float are only used to store in memory with less precision.

### Lvalues and Rvalues

An lvalue is an address, with the special case that registers may also be used even though their address may not be taken. This is because lvalues are used for loads and stores.

The rule is, where an rvalue is required, if an lvalue is positioned instead, its corresponding value must be loaded from the address.

The overwhelming majority of expressions use rvalues, so the requirement for an lvalue will be stated explicitly.

### Expression Level 1

    expr1 =
        NAME
        | CON
        | FCON
        | STRING
        | '(' expr15 ')'
        | expr1 '(' exprlist ')'
        | expr1 '[' expr15 ']'
        | expr1 '.' NAME
        | expr1 '->' NAME
    ;

A primary expression. Can be split into the left side and the right side.

Left sides consist of one of the following

- **NAME**: The address of the NAME according to its storage class is produced. As such, this is an lvalue. If the NAME is undefined, the following occurs.
  - If in local scope:
    - If the next operator is a '(', indicated the start of a function call, then the NAME is set in the parser's symbol table as an **extern** of type *function returning int*. Since pointers and ints are largely synonymous, and structs/arrays may not be returned, this will work in most cases. This symbol will be marked as local so it will disappear when exiting local scope.
    - Otherwise, it is assumed to be a undefined **GOTO** label of type array-of-integers. It is marked as undefined, so that upon exiting local scope, if the corresponding label was never specified in a statement, an error will occur. It is also marked local so that it will disappear upon exiting local scope.
  - Otherwise, we're in extern scope, so assume an **extern** of type *int*.
- **CON** or **FCON**: an integer or floating constant. An integer constant has type int, a floating constant has type double.
- **STRING**: a pointer to the string is placed here, storage class **static**, of type *array of (length of string) chars*. As an array, it will have the unary '&' prepended to it according to the type conversion rules.
- **'(' expr15 ')'**: allows adjustment of precedence rules; the set expression will evaluate first.

After the left side, any number of right side operators may occur, binding left to right:

- **expr1 '(' exprlist ')'**: a function call. The expression are evaluated, right to left, each pushed onto the C6T stack. If an expression is floating type, it will take up a double-sized chunk of stack; otherwise int sized. Then the left side is called as a function. Afterwords, the argument expressions are removed from the stack. ***NO CHECKING AS TO THE TYPE OF THE ARGUMENTS IS DONE***. Accordingly, you may pass a variable length argument list (for instance, to printf) but having a function get the address of one of its declared paremeters, and treating it as a pointer to its arguments; each subsequent argument will have a higher address, since the stack is downgrowing, and they were pushed right-to-left.
- **expr1 '[' expr15 ']'**: equivalent exactly to '*((expr1)+(expr15))'.
- **expr1 '.' NAME**: expr1 must be an lvalue, and not a register. The **NAME** must be a member tag. The offset of the tag is added to the lvalue, and the result is an lvalue of the type of the member. Note that the type of expr1 is *not* checked to be a struct; this is a feature, not a bug. The '.' operator may be applied to any address.
- **expr1 '->' NAME**: expr1 is evaluated as an rvalue, with any loading that entails. The result must not be a float; it also does not have to be a struct or pointer. **NAME** must be a member tag. Its offset is added to the value of expr1, and the result is an lvalue of the type of the member. Since expr1's type is not checked, you may use it, for instance, to access a register in a memory mapped I/O structure; `100->foo` would access member foo starting at address decimal 100.

### Expression Level 2

Unary operators

    expr2 =
        expr1 {incdec}
        | unary expr2
    ;
    incdec = '++' | '--';

Right-associative. The unary operators are as follow:

- **'~'**: requires a non-float; the resulting valuehas the same type, but all bits flipped.
- **'*'**: dereference operator. Requires a pointer or array type. Result is an lvalue whose type is whatever the pointer pointed to. As a result, an additional rvalue use will have its contents loaded again. For instance, `extern *_foo, x; x = *foo;` will evaluate something like `_foo; load; load; store _x`; getting the contents of foo, and treating that as an address.
- **&**: address-of operator. Requires an lvalue, and the result is treated as an rvalue; in other words, use the lvalue as an rvalue.
- **-**: negation. May use floating or other type; the result is the negated form.
- **!**: logical not operator. If the value was 0, the result is the constant 1; else, the result is the constant 0. Resulting value is integer.
- **sizeof**: the right side exression is NOT evaluated; its type is taken and the result is an integer constant of the size of the type. *Unlike* modern C, there is no syntax to specify a general type here, so you must use an expression or variable with the type desired; `int foo; sizeof(foo)` instead of `sizeof(int)`.
- **++** or **--**: increment or decrement operators. Require an lvalue. If the operator is on the left side, it is a pre-inc/dec; on the right side, a post-inc/dec. May not work on floats, may work on pointers. A pre-inc/dec adds or subtracts 1, with pointer arithmetic, to value in lvalue, storing it, and the resulting value is the stored value. Post-inc/dec is the same, but the resulting value is the value stored in the lvalue BEFORE the increment/decrement.
