# C6T

C6T ("See Sixty") - short for C version 6 by Troy - is a reimplementation of
the version of the C programming language included in the 1975 Unix
distribution referred to as "Research Unix Sixth Edition".

Compared to modern C, it is missing many features which are hard to parse or
codegen for, and is much closer to assembly.

To account for differing platforms, this C6T specific version defines an
int as a 16bit little-endian 2's complement number with no alignment.
Platforms with individual requirements outside of these are expected to
virtualize their environment, if not simulate it entirely.

See doc/grammar.md for details.
