"""C6T - C version 6 by Troy - Type System Unit Tests"""

import unittest
from type6 import TypeString, TypeElem, Type


class TypeTest(unittest.TestCase):
    """Tests for the C6T type system."""

    def test_size(self):
        """Test the sizes of different type strings."""
        typestr = TypeString(Type.POINT, Type.INT)
        self.assertEqual(typestr.size, 2)
        self.assertEqual(typestr.sizenext(), 2)
        typestr = TypeString(
            TypeElem(Type.ARRAY, 10),
            TypeElem(Type.ARRAY, 10),
            Type.POINT,
            Type.FUNC,
            Type.INT,
        )
        self.assertEqual(typestr.size, 10 * 10 * 2)
        self.assertEqual(typestr.pop().size, 10 * 2)
        self.assertEqual(typestr.pop().pop().size, 2)
        self.assertEqual(typestr.pop().pop().pop().size, 0)
        self.assertEqual(typestr.pop().pop().pop().pop().size, 2)

    def test_type(self):
        """Test the type info on different type strings."""
        typestr = TypeString(Type.FUNC, Type.POINT, TypeElem(Type.ARRAY, 10), Type.INT)
        self.assertFalse(typestr.floating)
        self.assertFalse(typestr.integral)
        self.assertFalse(typestr.pointer)
        typestr = typestr.pop()
        self.assertTrue(typestr.pointer)
        self.assertFalse(typestr.integral)
        self.assertFalse(typestr.floating)
        typestr = typestr.pop()
        self.assertTrue(typestr.pointer)
        self.assertFalse(typestr.integral)
        self.assertFalse(typestr.floating)
        typestr = typestr.pop()
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

    def test_eq(self):
        """Test type string compare and hashes."""
        typestrs = (
            TypeString(Type.POINT, Type.INT),
            TypeString(Type.POINT, Type.INT),
            TypeString(TypeElem(Type.ARRAY, 10), Type.POINT, Type.FUNC, Type.INT),
            TypeString(TypeElem(Type.ARRAY, 5), Type.POINT, Type.FUNC, Type.INT),
        )
        self.assertEqual(typestrs[0], typestrs[1])
        self.assertNotEqual(typestrs[0], typestrs[2])
        self.assertNotEqual(typestrs[1], typestrs[3])
        self.assertNotEqual(typestrs[2], typestrs[3])
        self.assertEqual(hash(typestrs[0]), hash(typestrs[1]))
        self.assertNotEqual(hash(typestrs[0]), hash(typestrs[3]))
        self.assertNotEqual(hash(typestrs[1]), hash(typestrs[2]))
        self.assertNotEqual(hash(typestrs[2]), hash(typestrs[3]))
