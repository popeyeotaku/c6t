"""C6T - C version 6 by Troy - Type System Unit Tests"""

import unittest
from type6 import TypeString, TypeElem, Type


class TypeTest(unittest.TestCase):
    """Tests for the C6T type system."""

    def test_size(self):
        """Test the sizes of different type strings."""
        typestr = TypeString(Type.POINT, Type.INT)
        self.assertEqual(typestr.size, 2)
        self.assertEqual(typestr.sizenext, 2)
        typestr = TypeString(
            TypeElem(Type.ARRAY, 10),
            TypeElem(Type.ARRAY, 10),
            Type.POINT,
            Type.FUNC,
            Type.INT,
        )
        self.assertEqual(typestr.size, 10 * 10 * 2)
        self.assertEqual(typestr.popped.size, 10 * 2)
        self.assertEqual(typestr.popped.popped.size, 2)
        self.assertEqual(typestr.popped.popped.popped.size, 0)
        self.assertEqual(typestr.popped.popped.popped.popped.size, 2)

    def test_type(self):
        """Test the type info on different type strings."""
        typestr = TypeString(Type.FUNC, Type.POINT, TypeElem(Type.ARRAY, 10), Type.INT)
        self.assertFalse(typestr.floating)
        self.assertFalse(typestr.integral)
        self.assertFalse(typestr.pointer)
        typestr = typestr.popped
        self.assertTrue(typestr.pointer)
        self.assertFalse(typestr.integral)
        self.assertFalse(typestr.floating)
        typestr = typestr.popped
        self.assertTrue(typestr.pointer)
        self.assertFalse(typestr.integral)
        self.assertFalse(typestr.floating)
        typestr = typestr.popped
        self.assertTrue(typestr.integral)
        self.assertFalse(typestr.floating)
        self.assertFalse(typestr.pointer)
        for label in (Type.FLOAT, Type.DOUBLE):
            typestr = TypeString(label)
            self.assertTrue(typestr.floating)
            self.assertFalse(typestr.integral)
            self.assertFalse(typestr.pointer)
        typestr = TypeString(Type.CHAR)
        self.assertTrue(typestr.integral)
        self.assertFalse(typestr.floating)
        self.assertFalse(typestr.pointer)
        typestr = TypeString(TypeElem(Type.STRUCT, 10))
        self.assertFalse(typestr.integral)
        self.assertFalse(typestr.floating)
        self.assertFalse(typestr.pointer)
