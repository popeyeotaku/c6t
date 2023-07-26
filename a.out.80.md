# PopLink A.OUT Format

## Overview

A Poplink a.out file consists of a header, followed by the text and data
segments, followed by the relocation blocks, and finally
the symbol table.

## Header

        struct header {
                int magic;
                int flags;
                char *textsize, *datasize, *bsssize;
                char *textreloc, *datareloc;
                char *symsize, *startaddr;
        };

The magic value should be 0417(8).

### Flags

* 01(8):        This file is executable.

## Text and Data Segments

This contains the raw binary bytes; all references to text, data, or bss
segment address are already offset from their supposed start
(startaddr for text, startaddr+textsize for data, startaddr+textsize+datasize
for bss)
so the segments can be loaded in without modification
if executable.

## Symbol Table

struct symbol {
        char name[9];
        char class;
        int value;
};

### Symbol Classes

* 0:    undefined
* 1:    Text Segment
* 2:    Data Segment
* 3:    BSS Segment
* 4:    Absolute
* 5:    COMMON (value is the size)

Bit7 of the class is a flag for if the symbol is exported.

## Relocation Info

There are the two relocation info blocks: one for text, one for data.

Each block consists of one or more chunks.
Each chunk relocates by adding an 8 or 16bit value in the corresponding
segment to the new offset for the start of that segment.

        struct chunk {
                char *offset;
                char hilo;
                char class;
        };      /* if class > 0 */
        struct chunk {
                char *offset;
                char hilo;
                char class;
                char name[9];
        };      /* if class == 0 */
        struct chunk {
                char *offset;
                char hilo, lobyte;
                char class;
                /* char name[9] if class == 0 */
        };      /* if hilo == 1 */

* offset: number of bytes from the previous relocchunk (starting
        at the start of the segment (text/data)).
        An offset of -1/all bits set indicates the end of the relocation block.
* hilo: Indicates 0 for 26bit relocation, 1 for 8bit relocation of the low
        byte, and 1 for 8bit relocation of the high byte.
        If =1/the hibyte is indicated, it is followed by the low byte
        of the full 16bit offset in the segment data, of which only the high
        8 bits are present.
* class: Same value as in the symbol table. If =0=undefined, the name
        will follow.
