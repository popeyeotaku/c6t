"""C6T - C version 6 by Troy - Shared Utility Routines."""


def word(i: int) -> int:
    """Wrap i as if it was a 2byte 2's complement integer."""
    if i < 0:
        i = ((-i) ^ 0xFFFF) + 1
    return i & 0xFFFF
