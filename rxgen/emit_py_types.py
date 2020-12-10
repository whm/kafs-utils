# Emission of Python type wrappers
# -*- coding: utf-8 -*-

__copyright__ = """
Copyright (C) 2015 Red Hat, Inc. All Rights Reserved.
Written by David Howells (dhowells@redhat.com)

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public Licence version 2 as
published by the Free Software Foundation.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public Licence for more details.

You should have received a copy of the GNU General Public Licence
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
"""

from rxgen_bits import *

###############################################################################
#
# Emit python type wrapper declarations
#
###############################################################################
def emit_py_type_wrapper_decls(o, s):
    o.pysrc("static PyTypeObject py_", s.name, "Type;\n")


###############################################################################
#
# Emit python type wrappers for C structs.
#
###############################################################################
def emit_py_type_wrapper(o, struct):
    o.xdr.py_type_defs.append(py_type_def(struct.name, "py_" + struct.name + "Type"))

    # Divide the struct members into single ints, single structs, char arrays
    # (strings) and other arrays
    single_ints = list();
    single_structs = list();
    char_arrays = list();
    arrays = list();
    for m in struct.members:
        ty = m.typespec
        o.where(struct.name + "::" + m.name)
        if ty.is_char_array():
            char_arrays.append(m)
        elif ty.is_single_basic():
            single_ints.append(m)
        elif ty.is_single_struct():
            single_structs.append(m)
        elif ty.is_array():
            arrays.append(m)
        else:
            o.error(": Unsupported struct member type")

    # Write a python wrapper struct
    #
    # We have a copy of the raw struct and we also have caches for python
    # objects for non-integer, non-array bits of the struct.  We populate the
    # caches when these bits are called for and then fold their contents back
    # into the raw struct when we're about to marshal it.
    #
    o.pyhdr("\n")
    o.pyhdr("struct py_", struct.name, " {\n")
    o.pyhdr("\tPyObject_HEAD\n")
    o.pyhdr("\tstruct ", struct.name, " x;\n")
    if single_structs or arrays:
        o.pyhdr("\tstruct {\n")
        for m in single_structs + arrays:
            o.pyhdr("\t\tPyObject *", m.name, ";\n")
        o.pyhdr("\t} c;\n")
    o.pyhdr("};\n")

    # We need to have a new function if the object is to be allocatable by the
    # Python interpreter
    o.pysrc("\n")
    o.pysrc("static PyObject *\n")
    o.pysrc("py_", struct.name, "_new(PyTypeObject *subtype, PyObject *args, PyObject *kwds)\n")
    o.pysrc("{\n")
    o.pysrc("\treturn subtype->tp_alloc(subtype, 1);\n;")
    o.pysrc("}\n")

    # We have to have a deallocation function
    o.pysrc("\n")
    o.pysrc("static void\n")
    o.pysrc("py_", struct.name, "_dealloc(struct py_", struct.name, " *self)\n")
    o.pysrc("{\n")
    for m in single_structs + arrays:
        o.pysrc("\tPy_XDECREF(self->c.", m.name, ");\n")
    o.pysrc("\tPy_TYPE(self)->tp_free((PyObject *)self);\n")
    o.pysrc("}\n")

    # Any integer non-array elements are made directly accessible to the Python
    # interpreter
    if single_ints:
        o.pysrc("\n")
        o.pysrc("static PyMemberDef py_", struct.name, "_members[] = {\n")
        for m in single_ints:
            ty = m.typespec
            o.where(struct.name + "::" + m.name)
            o.pysrc("\t{ \"", m.name, "\", ")
            if ty.name == "char":
                o.pysrc("T_CHAR")
            elif ty.name == "int8_t":
                o.pysrc("T_BYTE")
            elif ty.name == "int16_t":
                o.pysrc("T_SHORT")
            elif ty.name == "int32_t":
                o.pysrc("T_INT")
            elif ty.name == "int64_t":
                o.pysrc("T_LONGLONG")
            elif ty.name == "uint8_t":
                o.pysrc("T_UBYTE")
            elif ty.name == "uint16_t":
                o.pysrc("T_USHORT")
            elif ty.name == "uint32_t":
                o.pysrc("T_UINT")
            elif ty.name == "uint64_t":
                o.pysrc("T_ULONGLONG")
            else:
                o.error(": Unsupported type \"", ty.name, "\"")
            o.pysrc(", offsetof(struct py_", struct.name, ", x.", m.name, "), 0, \"\"},\n")
        o.pysrc("\t{}\n")
        o.pysrc("};\n")

    # Non-single integer elements need to be turned into their respective
    # Python types and returned.

    # Array elements have to be accessed through ->tp_[sg]etattro() as
    # tuples (int[]/uint[]/struct[]) or strings (char[])
    #
    attro_list = char_arrays + single_structs + arrays
    if attro_list:
        # The attribute get function
        o.pysrc("\n")
        o.pysrc("static PyObject *\n")
        o.pysrc("py_", struct.name, "_getattro(PyObject *_self, PyObject *name)\n")
        o.pysrc("{\n")
        o.pysrc("\tstruct py_", struct.name, " *self = (struct py_", struct.name, " *)_self;\n")
        o.pysrc("\n")
        o.pysrc("\tif (PyUnicode_Check(name)) {\n")

        for m in attro_list:
            ty = m.typespec
            o.where(struct.name + "::" + m.name)
            o.pysrc("\t\tif (PyUnicode_CompareWithASCIIString(name, \"", m.name, "\") == 0)\n")
            if ty.is_single_struct():
                o.pysrc("\t\t\treturn py_rxgen_get_struct(&self->x.", m.name, ",\n")
                o.pysrc("\t\t\t\t\t\t   &self->c.", m.name, ",\n")
                o.pysrc("\t\t\t\t\t\t   py_data_to_", ty.name, ");\n")
            elif not ty.is_array():
                raise RuntimeError("Unsupported basic type \"" + str(ty) + "\"")
            elif ty.is_struct_array():
                o.pysrc("\t\t\treturn py_rxgen_get_structs(&self->x.", m.name, ", ", ty.dim.name, ",\n")
                o.pysrc("\t\t\t\t\t\t    sizeof(struct ", ty.name, "),\n")
                o.pysrc("\t\t\t\t\t\t    &self->c.", m.name, ",\n")
                o.pysrc("\t\t\t\t\t\t    py_data_to_", ty.name, ");\n")
            elif not ty.is_int_array():
                o.error(": Unsupported array type class \"", ty, "\"")
            elif ty.name == "char":
                o.pysrc("\t\t\treturn py_rxgen_get_string(&self->x.", m.name, ", ", ty.dim.name, ");\n")
            elif ty.name == "uint8_t":
                o.pysrc("\t\t\treturn py_rxgen_get_uint8(&self->x.", m.name, ", ", ty.dim.name, ",\n")
                o.pysrc("\t\t\t\t\t\t  &self->c.", m.name, ");\n")
            elif ty.name == "uint16_t":
                o.pysrc("\t\t\treturn py_rxgen_get_uint16(&self->x.", m.name, ", ", ty.dim.name, ",\n")
                o.pysrc("\t\t\t\t\t\t   &self->c.", m.name, ");\n")
            elif ty.name == "uint32_t":
                o.pysrc("\t\t\treturn py_rxgen_get_uint32(&self->x.", m.name, ", ", ty.dim.name, ",\n")
                o.pysrc("\t\t\t\t\t\t   &self->c.", m.name, ");\n")
            elif ty.name == "int8_t":
                o.pysrc("\t\t\treturn py_rxgen_get_int8(&self->x.", m.name, ", ", ty.dim.name, ",\n")
                o.pysrc("\t\t\t\t\t\t  &self->c.", m.name, ");\n")
            elif ty.name == "int16_t":
                o.pysrc("\t\t\treturn py_rxgen_get_int16(&self->x.", m.name, ", ", ty.dim.name, ",\n")
                o.pysrc("\t\t\t\t\t\t   &self->c.", m.name, ");\n")
            elif ty.name == "int32_t":
                o.pysrc("\t\t\treturn py_rxgen_get_int32(&self->x.", m.name, ", ", ty.dim.name, ",\n")
                o.pysrc("\t\t\t\t\t\t   &self->c.", m.name, ");\n")
            else:
                raise RuntimeError("Unsupported array type \"" + str(ty) + "\"")

        o.pysrc("\t}\n")
        o.pysrc("\n")
        o.pysrc("\treturn PyObject_GenericGetAttr(_self, name);\n")
        o.pysrc("}\n")
        o.pysrc("\n")

        # The attribute set function
        o.pysrc("static int\n")
        o.pysrc("py_", struct.name, "_setattro(PyObject *_self, PyObject *name, PyObject *val)\n")
        o.pysrc("{\n")
        o.pysrc("\tstruct py_", struct.name, " *self = (struct py_", struct.name, " *)_self;\n")
        o.pysrc("\n")
        o.pysrc("\tif (PyUnicode_Check(name)) {\n")

        for m in attro_list:
            ty = m.typespec
            o.where(struct.name + "::" + m.name)
            o.pysrc("\t\tif (PyUnicode_CompareWithASCIIString(name, \"", m.name, "\") == 0)\n")
            if ty.is_single_struct():
                o.pysrc("\t\t\treturn py_rxgen_set_struct(&self->c.", m.name, ",\n")
                o.pysrc("\t\t\t\t\t\t   &py_", ty.name, "Type, val);\n")
            elif not ty.is_array():
                raise RuntimeError("Unsupported basic type \"" + str(ty) + "\"")
            elif ty.is_char_array():
                o.pysrc("\t\t\treturn py_rxgen_set_string(&self->x.", m.name, ", ", ty.dim.name, ", val);\n")
            elif ty.is_int_array() or ty.is_struct_array():
                o.pysrc("\t\t\treturn py_rxgen_set_array(", ty.dim.name, ", &self->c.", m.name, ", val);\n")
            else:
                raise RuntimeError("Unsupported array type \"" + str(ty) + "\"")

        o.pysrc("\t}\n")
        o.pysrc("\n")
        o.pysrc("\treturn PyObject_GenericSetAttr(_self, name, val);\n")
        o.pysrc("}\n")
        o.pysrc("\n")

    # Emit the Python type definition
    o.pysrc("static PyTypeObject py_", struct.name, "Type = {\n")
    o.pysrc("\tPyVarObject_HEAD_INIT(NULL, 0)\n")
    o.pysrc("\t\"kafs.", struct.name, "\",\t\t/*tp_name*/\n")
    o.pysrc("\tsizeof(struct py_", struct.name, "),\t/*tp_basicsize*/\n")
    o.pysrc("\t0,\t\t\t\t/*tp_itemsize*/\n")
    o.pysrc("\t(destructor)py_", struct.name, "_dealloc, /*tp_dealloc*/\n")
    o.pysrc("\t0,\t\t\t\t/*tp_print*/\n")
    o.pysrc("\t0,\t\t\t\t/*tp_getattr*/\n")
    o.pysrc("\t0,\t\t\t\t/*tp_setattr*/\n")
    o.pysrc("\t0,\t\t\t\t/*tp_compare*/\n")
    o.pysrc("\t0,\t\t\t\t/*tp_repr*/\n")
    o.pysrc("\t0,\t\t\t\t/*tp_as_number*/\n")
    o.pysrc("\t0,\t\t\t\t/*tp_as_sequence*/\n")
    o.pysrc("\t0,\t\t\t\t/*tp_as_mapping*/\n")
    o.pysrc("\t0,\t\t\t\t/*tp_hash */\n")
    o.pysrc("\t0,\t\t\t\t/*tp_call*/\n")
    o.pysrc("\t0,\t\t\t\t/*tp_str*/\n")
    if attro_list:
        o.pysrc("\tpy_", struct.name, "_getattro,\n")
        o.pysrc("\tpy_", struct.name, "_setattro,\n")
    else:
        o.pysrc("\t0,\t\t\t\t/*tp_getattro*/\n")
        o.pysrc("\t0,\t\t\t\t/*tp_setattro*/\n")
    o.pysrc("\t0,\t\t\t\t/*tp_as_buffer*/\n")
    o.pysrc("\tPy_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE, /*tp_flags*/\n")
    o.pysrc("\t\"\",\t\t\t/* tp_doc */\n")
    o.pysrc("\t0,\t\t\t\t/* tp_traverse */\n")
    o.pysrc("\t0,\t\t\t\t/* tp_clear */\n")
    o.pysrc("\t0,\t\t\t\t/* tp_richcompare */\n")
    o.pysrc("\t0,\t\t\t\t/* tp_weaklistoffset */\n")
    o.pysrc("\t0,\t\t\t\t/* tp_iter */\n")
    o.pysrc("\t0,\t\t\t\t/* tp_iternext */\n")
    o.pysrc("\t0,\t\t\t\t/* tp_methods */\n")
    if single_ints:
        o.pysrc("\tpy_", struct.name, "_members,\n")
    else:
        o.pysrc("\t0,\t\t\t/* tp_members */\n")
    o.pysrc("\t0,\t\t\t\t/* tp_getset */\n")
    o.pysrc("\t0,\t\t\t\t/* tp_base */\n")
    o.pysrc("\t0,\t\t\t\t/* tp_dict */\n")
    o.pysrc("\t0,\t\t\t\t/* tp_descr_get */\n")
    o.pysrc("\t0,\t\t\t\t/* tp_descr_set */\n")
    o.pysrc("\t0,\t\t\t\t/* tp_dictoffset */\n")
    o.pysrc("\t0,\t\t\t\t/* tp_init */\n")
    o.pysrc("\t0,\t\t\t\t/* tp_alloc */\n")
    o.pysrc("\tpy_", struct.name, "_new,\n")
    o.pysrc("};\n")

    # Emit a function to allocate such a type
    o.pyhdr("extern PyObject *kafs_new_py_", struct.name, "(PyObject *, PyObject *);\n")

    o.pysrc("\n")
    o.pysrc("PyObject *\n")
    o.pysrc("kafs_new_py_", struct.name, "(PyObject *_self, PyObject *args)\n")
    o.pysrc("{\n")
    o.pysrc("\tPyObject *obj = _PyObject_New(&py_", struct.name, "Type);\n")
    o.pysrc("\tstruct py_", struct.name, " *self = (struct py_", struct.name, " *)obj;\n")
    o.pysrc("\tif (!obj)\n")
    o.pysrc("\t\treturn PyExc_MemoryError;\n")
    o.pysrc("\tmemset(&self->x, 0, sizeof(self->x));\n")
    if single_structs or arrays:
        o.pysrc("\tmemset(&self->c, 0, sizeof(self->c));\n")
    o.pysrc("\treturn obj;\n")
    o.pysrc("}\n")

    # Emit a function to create an object of this type from raw data
    o.pyhdr("extern PyObject *py_data_to_", struct.name, "(const void *);\n")

    o.pysrc("\n")
    o.pysrc("PyObject *py_data_to_", struct.name, "(const void *data)\n")
    o.pysrc("{\n")
    o.pysrc("\tPyObject *obj = _PyObject_New(&py_", struct.name, "Type);\n")
    o.pysrc("\tstruct py_", struct.name, " *self = (struct py_", struct.name, " *)obj;\n")
    o.pysrc("\tif (!obj)\n")
    o.pysrc("\t\treturn PyExc_MemoryError;\n")
    o.pysrc("\tmemcpy(&self->x, data, sizeof(self->x));\n")
    if single_structs or arrays:
        o.pysrc("\tmemset(&self->c, 0, sizeof(self->c));\n")
    o.pysrc("\treturn obj;\n")
    o.pysrc("}\n")

    # Emit a function to unmarshal on object of this type.
    o.pysrc("\n")
    o.pysrc("PyObject *py_decode_", struct.name, "(struct rx_call *call)\n")
    o.pysrc("{\n")
    o.pysrc("\tPyObject *obj = _PyObject_New(&py_", struct.name, "Type);\n")
    o.pysrc("\tstruct py_", struct.name, " *self = (struct py_", struct.name, " *)obj;\n")
    o.pysrc("\tif (!obj)\n")
    o.pysrc("\t\treturn PyExc_MemoryError;\n")
    o.pysrc("\trxgen_decode_", struct.name, "(call, &self->x);\n")
    if single_structs or arrays:
        o.pysrc("\tmemset(&self->c, 0, sizeof(self->c));\n")
    o.pysrc("\treturn obj;\n")
    o.pysrc("}\n")

    # Emit a function to premarshal such a type.  This checks the Python object
    # type and folds the contents of the cached Python objects into their raw
    # fields.
    #
    o.pyhdr("extern int py_premarshal_", struct.name, "(PyObject *);\n")

    o.pysrc("\n")
    o.pysrc("int py_premarshal_", struct.name, "(PyObject *_self)\n")
    o.pysrc("{\n")
    o.pysrc("\tstruct py_", struct.name, " *self = (struct py_", struct.name, " *)_self;\n")

    # Check that the type we've been given is the right one
    o.pysrc("\n")
    o.pysrc("\tif (!PyObject_TypeCheck(self, &py_", struct.name, "Type)) {\n")
    o.pysrc("\t\tPyErr_Format(PyExc_TypeError, \"Expected object of type ", struct.name, "\");\n")
    o.pysrc("\t\treturn -1;\n")
    o.pysrc("\t}\n")

    if single_structs or arrays:
        o.pysrc("\n")
        first = 1
        for m in single_structs + arrays:
            ty = m.typespec
            o.where(struct.name + "::" + m.name)
            if first:
                o.pysrc("\tif (")
                first = 0
            else:
                o.pysrc(" ||\n")
                o.pysrc("\t    ")

            if ty.is_single_struct():
                o.pysrc("py_rxgen_premarshal_struct(&self->x.", m.name, ",\n")
                o.pysrc("\t\t\t\t      sizeof(struct ", ty.name, "),\n")
                o.pysrc("\t\t\t\t      offsetof(struct py_", ty.name, ", x),\n")
                o.pysrc("\t\t\t\t      self->c.", m.name, ",\n")
                o.pysrc("\t\t\t\t      py_premarshal_", ty.name, ") < 0")
            elif not ty.is_array():
                raise RuntimeError("Unsupported basic type \"" + str(ty) + "\"")
            elif ty.is_struct_array():
                o.pysrc("py_rxgen_premarshal_structs(&self->x.", m.name, ",\n")
                o.pysrc("\t\t\t\t\t", ty.dim.name, ", sizeof(struct ", ty.name, "),\n")
                o.pysrc("\t\t\t\t\toffsetof(struct py_", ty.name, ", x),\n")
                o.pysrc("\t\t\t\t\tself->c.", m.name, ",\n")
                o.pysrc("\t\t\t\t\tpy_premarshal_", ty.name, ") < 0")
            elif not ty.is_int_array():
                raise RuntimeError("Unsupported array type \"", ty, "\"")
            elif ty.name == "uint8_t":
                o.pysrc("py_rxgen_premarshal_uint8(&self->x.", m.name, ", ", ty.dim.name, ", self->c.", m.name, ") < 0")
            elif ty.name == "uint16_t":
                o.pysrc("py_rxgen_premarshal_uint16(&self->x.", m.name, ", ", ty.dim.name, ", self->c.", m.name, ") < 0")
            elif ty.name == "uint32_t":
                o.pysrc("py_rxgen_premarshal_uint32(&self->x.", m.name, ", ", ty.dim.name, ", self->c.", m.name, ") < 0")
            elif ty.name == "int8_t":
                o.pysrc("py_rxgen_premarshal_int8(&self->x.", m.name, ", ", ty.dim.name, ", self->c.", m.name, ") < 0")
            elif ty.name == "int16_t":
                o.pysrc("py_rxgen_premarshal_int16(&self->x.", m.name, ", ", ty.dim.name, ", self->c.", m.name, ") < 0")
            elif ty.name == "int32_t":
                o.pysrc("py_rxgen_premarshal_int32(&self->x.", m.name, ", ", ty.dim.name, ", self->c.", m.name, ") < 0")
            else:
                o.error(": Unsupported array type \"", ty.name, "\"")

        o.pysrc(")\n")
        o.pysrc("\t\treturn -1;\n")

    o.pysrc("\treturn 0;\n")
    o.pysrc("}\n")

