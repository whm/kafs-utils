#!/usr/bin/python3
#
# Emit C synchronous functions
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

class decode_phase:
    def __init__(self, form="flat", size=0, xdr_size=0, name=None):
        self.form = form
        self.size = size
        self.params = list()
        self.xdr_size = xdr_size
        self.elem_count = 0
        self.name = name

bulk_get_helpers = dict();
bulk_set_helpers = dict();

c_to_py_type_map = dict([("char",     "T_CHAR"),
                         ("int8_t",   "T_BYTE"),
                         ("int16_t",  "T_SHORT"),
                         ("int32_t",  "T_INT"),
                         ("int64_t",  "T_LONGLONG"),
                         ("uint8_t",  "T_UBYTE"),
                         ("uint16_t", "T_USHORT"),
                         ("uint32_t", "T_UINT"),
                         ("uint64_t", "T_ULONGLONG")
                     ])

###############################################################################
#
# Emit python objects to represent received parameter sets and received
# response sets for RPC calls.
#
###############################################################################
def emit_py_func_param_object(o, func, way):
    struct_req = "py_" + func.name + "_" + way;
    basic_params = list()
    complex_params = list()
    params = list()
    division = ""

    global c_to_py_type_map

    t = py_type_def(func.name + "_" + way, struct_req + "Type")
    o.xdr.py_type_defs.append(t)

    if way == "request":
        params = func.request
        division = "calls"
    else:
        params = func.response
        division = "responses"

    # Define a C structure to hold the python object header and the data.
    o.pyhdr("\n")
    o.pyhdr("struct ", struct_req, " {\n")
    o.pyhdr("\tstruct py_rx_", way, " common;\n")
    if params:
        have_opaque = False
        o.pyhdr("\tstruct {\n")
        for p in params:
            o.where(func.name + ":" + p.name)
            ty = p.typespec
            if ty.is_single_int():
                basic_params.append(p)
                o.pyhdr("\t\t", ty.name, "\t", p.name, ";\n")
            else:
                complex_params.append(p)
                o.pyhdr("\t\tPyObject\t*", p.name, ";\n")

            if ty.is_single_opaque():
                have_opaque = True

        o.pyhdr("\t} x;\n")
        if have_opaque:
            o.pyhdr("\tPy_buffer dec_buf;\n")

    o.pyhdr("};\n")

    # We need to have a new function if the object is to be allocatable by the
    # Python interpreter
    o.pysrc("\n")
    o.pysrc("static PyObject *\n")
    o.pysrc(struct_req, "_new(PyTypeObject *subtype, PyObject *args, PyObject *kwds)\n")
    o.pysrc("{\n")
    o.pysrc("\tPyObject *obj;\n")
    o.pysrc("\n")
    o.pysrc("\tobj = subtype->tp_alloc(subtype, 1);\n")
    if params:
        o.pysrc("\tif (obj) {\n")
        o.pysrc("\t\tstruct ", struct_req, " *self = (struct ", struct_req, " *)obj;\n")
        o.pysrc("\t\tmemset(&self->x, 0, sizeof(self->x));\n")
        o.pysrc("\t}\n")
    o.pysrc("\treturn obj;\n")
    o.pysrc("}\n")

    # We have to have a deallocation function
    o.pysrc("\n")
    o.pysrc("static void ", struct_req, "_dealloc(struct ", struct_req, " *self)\n")
    o.pysrc("{\n")
    for p in complex_params:
        o.pysrc("\tPy_XDECREF(self->x.", p.name, ");\n")
    o.pysrc("\tPy_TYPE(self)->tp_free((PyObject *)self);\n")
    o.pysrc("}\n")

    # All elements are made directly accessible to the Python interpreter,
    # either as integer types or as object types.
    if params:
        o.pysrc("\n")
        o.pysrc("static PyMemberDef ", struct_req, "_members[] = {\n")
        for p in params:
            o.where(func.name + ":" + p.name)
            ty = p.typespec
            o.pysrc("\t{ \"", p.name, "\", ")
            if ty.is_single_blob():    o.pysrc("T_OBJECT_EX")
            elif ty.is_bulk():         o.pysrc("T_OBJECT_EX")
            elif ty.is_single_int():   o.pysrc(c_to_py_type_map[ty.name])
            else:
                o.pysrc("T_OBJECT_EX")
            o.pysrc(", offsetof(struct ", struct_req, ", x.", p.name, "), 0, \"\"},\n")

        o.pysrc("\t{}\n")
        o.pysrc("};\n")

    # Emit the Python type definition
    o.pysrc("\n")
    o.pysrc("static PyTypeObject ", struct_req, "Type = {\n")
    o.pysrc("\tPyVarObject_HEAD_INIT(NULL, 0)\n")
    o.pysrc("\t\"kafs.", func.name, "_", way, "\",\t\t/*tp_name*/\n")
    o.pysrc("\tsizeof(struct ", struct_req, "),\t/*tp_basicsize*/\n")
    o.pysrc("\t0,\t\t\t\t/*tp_itemsize*/\n")
    o.pysrc("\t(destructor)", struct_req, "_dealloc, /*tp_dealloc*/\n")
    o.pysrc("\t0,\t\t\t\t/*tp_print*/\n")
    o.pysrc("\t0,\t\t\t\t/*tp_getattr*/\n")
    o.pysrc("\t0,\t\t\t\t/*tp_setattr*/\n")
    o.pysrc("\t0,\t\t\t\t/*tp_compare*/\n")
    o.pysrc("\t0,\t\t\t\t/*tp_repr*/\n")
    o.pysrc("\t0,\t\t\t\t/*tp_as_number*/\n")
    o.pysrc("\t0,\t\t\t\t/*tp_as_sequence*/\n")
    o.pysrc("\t0,\t\t\t\t/*tp_as_mapping*/\n")
    o.pysrc("\t0,\t\t\t\t/*tp_hash */\n")
    o.pysrc("\t0,\t\t\t\t/*tp_call */\n")
    o.pysrc("\t0,\t\t\t\t/*tp_str*/\n")
    o.pysrc("\t0,\t\t\t\t/*tp_getattro*/\n")
    o.pysrc("\t0,\t\t\t\t/*tp_setattro*/\n")
    o.pysrc("\t0,\t\t\t\t/*tp_as_buffer*/\n")
    o.pysrc("\tPy_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE, /*tp_flags*/\n")
    o.pysrc("\t\"\",\t\t\t\t/* tp_doc */\n")
    o.pysrc("\t0,\t\t\t\t/* tp_traverse */\n")
    o.pysrc("\t0,\t\t\t\t/* tp_clear */\n")
    o.pysrc("\t0,\t\t\t\t/* tp_richcompare */\n")
    o.pysrc("\t0,\t\t\t\t/* tp_weaklistoffset */\n")
    o.pysrc("\t0,\t\t\t\t/* tp_iter */\n")
    o.pysrc("\t0,\t\t\t\t/* tp_iternext */\n")
    o.pysrc("\t0,\t\t\t\t/* tp_methods */\n")
    if params:
        o.pysrc("\t", struct_req, "_members,\n")
    else:
        o.pysrc("\t0,\t\t\t\t/* tp_members */\n")

    o.pysrc("\t0,\t\t\t\t/* tp_getset */\n")
    o.pysrc("\t0,\t\t\t\t/* tp_base */\n")
    o.pysrc("\t0,\t\t\t\t/* tp_dict */\n")
    o.pysrc("\t0,\t\t\t\t/* tp_descr_get */\n")
    o.pysrc("\t0,\t\t\t\t/* tp_descr_set */\n")
    o.pysrc("\t0,\t\t\t\t/* tp_dictoffset */\n")
    o.pysrc("\t0,\t\t\t\t/* tp_init */\n")
    o.pysrc("\t0,\t\t\t\t/* tp_alloc */\n")
    o.pysrc("\t", struct_req, "_new,\n")
    o.pysrc("};\n")


###############################################################################
#
# Emit functions to help deal with bulk lists
#
###############################################################################
def emit_py_func_bulk_helper(o, func):
    for p in func.params:
        o.where(func.name + ":" + p.name)
        ty = p.typespec
        if not ty.is_bulk():
            continue

        # Data encoding
        if ty.name not in bulk_get_helpers:
            bulk_get_helpers[ty.name] = True

            o.pysrc("\n")
            o.pysrc("static __attribute__((unused))\n")
            o.pysrc("int py_encode_bulk_", ty.name, "(struct rx_call *call, PyObject *list)\n")
            o.pysrc("{\n")
            o.pysrc("\tPyObject *item;\n")
            o.pysrc("\tunsigned count, i;\n")
            o.pysrc("\n")
            o.pysrc("\tcount = PyList_Size(list);\n")
            o.pysrc("\trxrpc_enc(call, count);\n")
            o.pysrc("\n")
            o.pysrc("\tfor (i = 0; i < count; i++) {\n")
            o.pysrc("\t\titem = PyList_GetItem(list, i);\n")
            o.pysrc("\t\tif (!item)\n")
            o.pysrc("\t\t\treturn -1;\n")

            o.pysrc("\n")
            if ty.is_bulk_int():
                o.pysrc("\t\tif (!PyLong_Check(item)) {\n")
                o.pysrc("\t\t\tPyErr_SetString(PyExc_TypeError, \"Expected list of ", ty.name, "\");\n")
                o.pysrc("\t\t\treturn -1;\n")
                o.pysrc("\t\t}\n")
            else:
                o.pysrc("\t\tif (py_premarshal_", ty.name, "(item))\n")
                o.pysrc("\t\t\treturn -1;\n")

            if ty.is_bulk_int():
                if ty.name == "int64_t":
                    o.pysrc("\t\tuint64_t x = PyLong_AsLongLong(item);\n")
                    o.pysrc("\t\trxrpc_enc(call, x >> 32);\n")
                    o.pysrc("\t\trxrpc_enc(call, x);\n")
                elif ty.name == "uint64_t":
                    o.pysrc("\t\tuint64_t x = PyLong_AsUnsignedLongLong(item);\n")
                    o.pysrc("\t\trxrpc_enc(call, x >> 32);\n")
                    o.pysrc("\t\trxrpc_enc(call, x);\n")
                elif ty.name.startswith("int"):
                    o.pysrc("\t\trxrpc_enc(call, PyLong_AsLong(item));\n")
                elif ty.name.startswith("uint") or ty.name.startswith("char"):
                    o.pysrc("\t\trxrpc_enc(call, PyLong_AsUnsignedLong(item));\n")
                else:
                    raise RuntimeError
            else:
                o.pysrc("\t\trxgen_encode_", ty.name, "(call, &((struct py_", ty.name, " *)item)->x);\n")

            o.pysrc("\t}\n")
            o.pysrc("\treturn 0;\n")
            o.pysrc("}\n")

###############################################################################
#
# Emit a python wrapper function to make a simple synchronous call
#
###############################################################################
def emit_py_func_simple_sync_call(o, func):

    o.xdr.py_func_defs.append(py_func_def(func.name, "kafs_" + func.name))

    o.pysrc("\n")
    o.pysrc("PyObject *\n")
    o.pysrc("kafs_", func.name, "(PyObject *_self, PyObject *args)\n")
    o.pysrc("{\n")

    # Local variable declarations representing parameters to send
    o.pysrc("\tstruct rx_call *call;\n")
    o.pysrc("\tstruct py_rx_connection *z_conn;\n")
    o.pysrc("\tstruct py_", func.name, "_response *response;\n")
    for p in func.request:
        o.where(func.name + ":" + p.name)
        ty = p.typespec
        if ty.is_single_blob():
            o.pysrc("\tPy_buffer param_", p.name, ";\n")
        elif ty.is_single_int():
            o.pysrc("\t", ty.name, " param_", p.name, ";\n")
        elif ty.is_single_struct():
            o.pysrc("\tstruct py_", ty.name, " *param_", p.name, ";\n")
        elif ty.is_bulk():
            if p.direction != "OUT":
                o.pysrc("\tPyObject *param_", p.name, ";\n")
        else:
            raise RuntimeError("Unsupported type \"" + str(ty) + "\"")

    if func.split:
        o.pysrc("\tPyObject *split_callback, *split_info;\n")
    o.pysrc("\tPyObject *res = NULL;\n")
    o.pysrc("\tint ret;\n")

    # Make use of the tuple parser to extract the arguments and check their
    # types for us.
    o.pysrc("\n")
    o.pysrc("\tif (!PyArg_ParseTuple(args, \"O!")

    for p in func.request:
        o.where(func.name + ":" + p.name)
        ty = p.typespec
        if ty.is_bulk():               o.pysrc("O!")
        elif ty.is_array():            raise RuntimeError
        elif ty.name == "int8_t":      o.pysrc("B")
        elif ty.name == "int16_t":     o.pysrc("h")
        elif ty.name == "int32_t":     o.pysrc("i")
        elif ty.name == "int64_t":     o.pysrc("L")
        elif ty.name == "uint8_t":     o.pysrc("b")
        elif ty.name == "uint16_t":    o.pysrc("H")
        elif ty.name == "uint32_t":    o.pysrc("I")
        elif ty.name == "uint64_t":    o.pysrc("K")
        elif ty.is_single_struct():    o.pysrc("O!")
        elif ty.is_single_string():    o.pysrc("s*")
        elif ty.is_single_opaque():    o.pysrc("z*")
        else:
            raise RuntimeError("No py parse for param")

    if func.split:
        o.pysrc("O")
    o.pysrc("\",\n")
    o.pysrc("\t\t\t      &py_rx_connectionType, &z_conn")

    for p in func.request:
        o.where(func.name + ":" + p.name)
        ty = p.typespec
        o.pysrc(",\n")
        o.pysrc("\t\t\t      ")
        if ty.is_single_int():
            o.pysrc("&param_", p.name)
        elif ty.is_single_struct():
            o.pysrc("&py_", ty.name, "Type, &param_", p.name)
        elif ty.is_single_blob():
            o.pysrc("&param_", p.name)
        elif ty.is_bulk():
            o.pysrc("&PyList_Type, &param_", p.name)
        else:
            raise RuntimeError(": Unsupported type \"" + str(ty) + "\"")

    if func.split:
        o.pysrc(",\n\t\t\t      &split_callback")
    o.pysrc("))\n")
    o.pysrc("\t\treturn NULL;\n")

    if func.split:
        o.pysrc("\n")
        o.pysrc("\tsplit_info = py_rxgen_split_client_prepare();\n")
        o.pysrc("\tif (!split_info)\n")
        o.pysrc("\t\treturn NULL;\n")

    o.pysrc("\n")
    o.pysrc("\tcall = rxrpc_alloc_call(z_conn->x, 0);\n")
    o.pysrc("\tif (!call) {\n")
    if func.split:
        o.pysrc("\t\tPy_XDECREF(split_info);\n");
    o.pysrc("\t\treturn PyErr_NoMemory();\n")
    o.pysrc("\t}\n")
    o.pysrc("\tcall->decoder_cleanup = py_rxgen_decoder_cleanup;\n")
    if func.split:
        o.pysrc("\tpy_rxgen_split_client_set(call, split_callback, split_info);\n")

    # Marshal the arguments
    o.pysrc("\n")
    o.pysrc("\trxrpc_enc(call, ", func.opcode.name, ");\n")
    for p in func.request:
        o.where(func.name + ":" + p.name)
        ty = p.typespec
        if ty.is_blob():
            dim = -1
            if ty.max_size:
                dim = ty.max_size.name
            o.pysrc("\tif (py_enc_buffer(call, &param_", p.name, ", ", dim, ") < 0) {\n")
            o.pysrc("\t\trxrpc_terminate_call(call, EINVAL);\n")
            o.pysrc("\t\treturn NULL;\n")
            o.pysrc("\t}\n")
        elif ty.is_bulk():
            o.pysrc("\tif (py_encode_bulk_", ty.name, "(call, param_", p.name, ") < 0)\n")
            o.pysrc("\t\tgoto error;\n")
        elif ty.is_single_int32():
            o.pysrc("\trxrpc_enc(call, param_", p.name, ");\n")
        elif ty.is_single_int64():
            o.pysrc("\trxrpc_enc(call, param_", p.name, " >> 32);\n")
            o.pysrc("\trxrpc_enc(call, param_", p.name, ");\n")
        elif ty.is_single_struct():
            o.pysrc("\tif (py_premarshal_", ty.name, "((PyObject *)param_", p.name, ")) {\n")
            o.pysrc("\t\trxrpc_terminate_call(call, EINVAL);\n")
            o.pysrc("\t\treturn NULL;\n")
            o.pysrc("\t}\n")
            o.pysrc("\trxgen_encode_", ty.name, "(call, &param_", p.name, "->x);\n")
        else:
            raise RuntimeError("Unsupported type in decode " + str(ty))

    o.pysrc("\tif (rxrpc_post_enc(call) < 0)\n")
    o.pysrc("\t\tgoto error_no_res;\n")

    # Allocate a reply object
    o.pysrc("\n")
    o.pysrc("\tres = _PyObject_New(&py_", func.name, "_responseType);\n")
    o.pysrc("\tresponse = (struct py_", func.name, "_response *)res;\n")
    o.pysrc("\tif (!response)\n")
    o.pysrc("\t\tgoto enomem;\n")
    if func.response:
        o.pysrc("\tmemset(&response->x, 0, sizeof(response->x));\n")
    o.pysrc("\tcall->decoder = py_", func.name, "_decode_response;\n")
    o.pysrc("\tcall->decoder_private = response;\n")

    # Transmit the split data
    if func.split:
        o.pysrc("\tif (py_rxgen_split_transmit(call) < 0)\n")
        o.pysrc("\t\tgoto error_no_res;\n")
    else:
        o.pysrc("\tcall->more_send = 0;\n")

        # Make the call
        o.pysrc("\n")
        o.pysrc("\tret = rxrpc_send_data(call);\n")
        o.pysrc("\tif (ret == -1)\n")
        o.pysrc("\t\tgoto error;\n")

    # Wait for the reply
    #
    # If we're dealing with a split function or are in asynchronous mode, we
    # need to return the call here.
    #
    o.pysrc("\n")
    o.pysrc("\tret = rxrpc_run_sync_call(call);\n")
    o.pysrc("\tif (ret == -1)\n")
    o.pysrc("\t\tgoto error;\n")

    # Successful return
    o.pysrc("\n")
    o.pysrc("\trxrpc_terminate_call(call, 0);\n")
    o.pysrc("\treturn res;\n")

    # Error cleanups
    o.pysrc("\n")
    o.pysrc("error:\n")
    o.pysrc("\tPy_XDECREF(res);\n")
    o.pysrc("error_no_res:\n")
    o.pysrc("\tif (errno == ENOMEM)\n")
    o.pysrc("enomem:\n")
    o.pysrc("\t\tres = PyErr_NoMemory();\n")
    o.pysrc("\telse if (errno == ECONNABORTED)\n")
    o.pysrc("\t\tres = py_rxgen_received_abort(call);\n")
    o.pysrc("\telse\n")
    o.pysrc("\t\tres = PyErr_SetFromErrno(PyExc_IOError);\n")
    o.pysrc("\trxrpc_terminate_call(call, ENOMEM);\n")
    o.pysrc("\treturn res;\n")

    # End the function
    o.pysrc("}\n")

###############################################################################
#
# Emit a function to decode a block into a python object in a way that can be
# used from asynchronous code.  The opcode is expected to have been removed
# from the incoming call on the server side.
#
###############################################################################
def emit_py_func_decode(o, func, side, subname, params):
    ptr = "obj->"

    # We fetch the data in a number of phases.  Each phase receives a chunk of
    # data of a certain size.  A phase's size might be dependent on a variable
    # in the previous phase.  Variable-sized bulk arrays are split across
    # multiple phases, with the length being at the end of the first phase and
    # the data in the second.
    #
    # We also need to interpolate a phase to deal with decoding split-op
    # auxiliary data.  This comes last when decoding the request and first when
    # decoding the response.
    #
    phases = list()
    phase = None
    have_bulk = False
    want_item = False

    if func.split and subname == "response":
        phase = decode_phase(form="split",
                             size="py_rxgen_split_receive(call)")
        phases.append(phase)
        phase = None
        have_bulk = True

    for p in params:
        o.where(func.name + ":" + p.name)
        ty = p.typespec

        if not phase:
            phase = decode_phase(form="flat")
            phases.append(phase)

        if ty.is_single_int() or ty.is_single_struct():
            phase.size += ty.xdr_size
            phase.params.append(p)
        elif ty.is_single_blob():
            have_bulk = True

            # Bulk objects begin with an element count
            phase.elem_count = phase.size
            phase.size += 4

            count_type = xdr_type(o.xdr, base=o.xdr.get_type("uint32_t"))
            pseudoparam = xdr_member("nr__" + p.name, count_type, o.xdr)
            pseudoparam.special = "blob_size"
            phase.params.append(pseudoparam)

            # Create a new phase
            phase = decode_phase(form="blob", name=p.name, size=4, xdr_size=ty.xdr_size)
            phase.params.append(p)
            phases.append(phase)

            # We don't want to be asking recvmsg() for one object at a time if
            # they're really small.
            phase.size = ty.xdr_size
            phase = None
        elif ty.is_bulk():
            have_bulk = True

            # Bulk objects begin with an element count
            phase.elem_count = phase.size
            phase.size += 4

            count_type = xdr_type(o.xdr, base=o.xdr.get_type("uint32_t"))
            pseudoparam = xdr_member("nr__" + p.name, count_type, o.xdr)
            pseudoparam.special = "bulk_size"
            phase.params.append(pseudoparam)

            # Create a new phase
            phase = decode_phase(form="bulk", name=p.name, size=4, xdr_size=ty.xdr_size)
            phase.params.append(p)
            phases.append(phase)

            want_item = True

            # We don't want to be asking recvmsg() for one object at a time if
            # they're really small.
            phase.size = ty.xdr_size
            phase = None
        else:
            raise RuntimeError("Reply array not supported")

    if func.split and subname == "request":
        phase = decode_phase(form="split",
                             size="py_rxgen_split_receive(call)")
        phases.append(phase)
        phase = None
        have_bulk = True

    # Function definition and arguments
    o.pysrc("\n")
    o.pysrc("int py_", func.name, "_decode_", subname, "(struct rx_call *call)\n")
    o.pysrc("{\n")

    if not params and not func.split:
        o.pysrc("\treturn 0;\n")
        o.pysrc("}\n")
        return

    # Local variables
    if params:
        o.pysrc("\tstruct py_", func.name, "_", subname, " *obj = call->decoder_private;\n")
    if want_item:
        o.pysrc("\tPyObject *item;\n")
    o.pysrc("\tunsigned phase = call->phase;\n")
    o.pysrc("\tunsigned count;\n")

    # Deal with each phase
    o.pysrc("\n")
    if have_bulk:
        o.pysrc("select_phase:\n")
    o.pysrc("\tcount = call->data_count;\n")
    #o.pysrc("\tprintf(\"-- Phase %u (%u) --\\n\", phase, count);\n")
    o.pysrc("\tswitch (phase) {\n")

    o.pysrc("\tcase 0:\n")

    next_phase_id = 1
    for phase in phases:
        phase.phase_id = next_phase_id
        next_phase_id += 1

    phase_goto_label = None
    for phase in phases:
        phase_id = phase.phase_id
        o.pysrc("\n")
        o.pysrc("\t\t/* --- Phase ", phase_id, " --- */\n")

        if phase_goto_label == phase_id:
            o.pysrc("\tphase_", phase_id, ":\n")
            phase_goto_label = None

        # Determine how big bulk objects are
        if phase.form == "blob":
            p = phase.params[0]
            ty = p.typespec
            if ty.is_single_string():
                o.pysrc("\t\tswitch (py_dec_init_string(call, &obj->x.", p.name, ")) {\n")
            elif ty.is_single_opaque():
                o.pysrc("\t\tobj->x.", p.name, " = PyByteArray_FromStringAndSize(\"\", 0);\n")
                o.pysrc("\t\tif (!obj->x.", p.name, ")\n")
                o.pysrc("\t\t\treturn -1;\n")
                o.pysrc("\t\tif (PyByteArray_Resize(obj->x.", p.name, ", call->blob_size) == -1)\n")
                o.pysrc("\t\t\treturn -1;\n")

                o.pysrc("\t\tswitch (py_dec_init_opaque(call, obj->x.", p.name, ")) {\n")
            else:
                raise RuntimeError("Unsupported blob type " + str(ty))

            o.pysrc("\t\tcase -1: return -1;\n")
            o.pysrc("\t\tcase  0: goto phase_", phase_id + 1, ";\n")
            o.pysrc("\t\tcase  1: break;\n")
            o.pysrc("\t\t}\n")
            phase_goto_label = phase_id + 1

        elif phase.form == "bulk":
            p = phase.params[0]
            ty = p.typespec
            if ty.is_bulk_int() or ty.is_bulk_struct():
                o.pysrc("\t\tobj->x.", p.name, " = PyList_New(call->bulk_count);\n")
                o.pysrc("\t\tif (!obj->x.", p.name, ")\n")
                o.pysrc("\t\t\treturn -1;\n")
            else:
                raise RuntimeError

            o.pysrc("\t\tif (call->bulk_count == 0)\n")
            o.pysrc("\t\t\tgoto phase_", phase_id + 1, ";\n")
            phase_goto_label = phase_id + 1
            o.pysrc("\t\tcall->bulk_index = 0;\n")

        # Entry point for a phase
        elif phase.form == "split":
            o.pysrc("\t\tif (py_rxgen_split_receive(call, 1) < 0)\n")
            o.pysrc("\t\t\treturn -1;\n")
            o.pysrc("\t\tif (call->need_size == 0)\n")
            o.pysrc("\t\t\tgoto phase_", phase_id + 1, ";\n")
            phase_goto_label = phase_id + 1

        o.pysrc("\t\tcall->phase = ", phase_id, ";\n")
        o.pysrc("\tcase ", phase_id, ":\n")

        if phase.form != "split":
            o.pysrc("\t\tcall->need_size = ", phase.size, ";\n")
            o.pysrc("\t\tif (count < call->need_size)\n")
            o.pysrc("\t\t\treturn 1;\n")
        else:
            o.pysrc("\t\tif (call->need_size == UINT_MAX ? count == 0 : count < call->need_size) {\n")
            #o.pysrc("\t\t\tprintf(\"NEED %u (phase %u)\\n\", call->need_size, phase);\n")
            o.pysrc("\t\t\treturn 1;\n")
            o.pysrc("\t\t}\n")

        # Unmarshal the data
        o.pysrc("\n")
        for p in phase.params:
            o.where(func.name + ":" + p.name)
            ty = p.typespec
            if p.special == None:
                pass
            elif p.special == "blob_size":
                o.pysrc("\t\tcall->blob_size = rxrpc_dec(call);\n")
                continue
            elif p.special == "bulk_size":
                o.pysrc("\t\tcall->bulk_count = rxrpc_dec(call);\n")
                continue
            else:
                raise RuntimeError

            if ty.is_bulk():
                if ty.is_bulk_struct():
                    o.pysrc("\t\titem = py_decode_", ty.name, "(call);\n")
                elif ty.is_bulk_int32() and ty.name.startswith("u"):
                    o.pysrc("\t\titem = PyLong_FromUnsignedLong((", ty.name, ")rxrpc_dec(call));\n")
                elif ty.is_bulk_int32():
                    o.pysrc("\t\titem = PyLong_FromLong((", ty.name, ")rxrpc_dec(call));\n")
                elif ty.is_bulk_int64() and ty.name.startswith("u"):
                    o.pysrc("\t\tcall->bulk_u64  = (uint64_t)rxrpc_dec(call) << 32;\n")
                    o.pysrc("\t\tcall->bulk_u64 |= (uint64_t)rxrpc_dec(call);\n")
                    o.pysrc("\t\titem = PyLong_FromUnsignedLongLong(call->bulk_u64);\n")
                elif ty.is_bulk_int64():
                    o.pysrc("\t\tcall->bulk_s64  = (int64_t)rxrpc_dec(call) << 32;\n")
                    o.pysrc("\t\tcall->bulk_s64 |= (int64_t)rxrpc_dec(call);\n")
                    o.pysrc("\t\titem = PyLong_FromLongLong(call->bulk_s64);\n")
                else:
                    raise RuntimeError

                o.pysrc("\t\tif (!item)\n")
                o.pysrc("\t\t\treturn -1;\n")
                o.pysrc("\t\tif (PyList_SetItem(obj->x.", p.name, ", call->bulk_index, item) < 0)\n")
                o.pysrc("\t\t\treturn -1;\n")
                o.pysrc("\t\tcall->bulk_index++;\n")

            elif ty.is_single_blob():
                if ty.is_single_string():
                    o.pysrc("\t\tswitch (py_dec_into_string(call)) {\n")
                else:
                    o.pysrc("\t\tswitch (py_dec_into_buffer(call)) {\n")
                o.pysrc("\t\tcase -1: return -1;\n")
                o.pysrc("\t\tcase  0: break;\n")
                o.pysrc("\t\tcase  1: phase = ", phase_id, "; goto select_phase;\n")
                o.pysrc("\t\t}\n")
            elif ty.is_single_int32():
                o.pysrc("\t\tobj->x.", p.name, " = (", ty.name, ")rxrpc_dec(call);\n")
            elif ty.is_single_int64():
                o.pysrc("\t\tobj->x.", p.name, " = (", ty.name, ")rxrpc_dec(call) << 32;\n")
                o.pysrc("\t\tobj->x.", p.name, " |= (", ty.name, ")rxrpc_dec(call) << 32;\n")
            elif ty.is_single_struct():
                o.pysrc("\t\tobj->x.", p.name, " = py_decode_", ty.name, "(call);\n")
            else:
                raise RuntimeError("Unsupported type in decode")

            if ty.is_single_string():
                o.pysrc("\t\tif (rxrpc_post_dec(call) < 0)\n")
                o.pysrc("\t\t\treturn -1;\n")
                o.pysrc("\t\tif (call->blob_offset < call->blob_size) {\n")
                o.pysrc("\t\t\tphase = ", phase_id, ";\n")
                o.pysrc("\t\t\tgoto select_phase;\n")
                o.pysrc("\t\t}\n")
            if ty.is_bulk():
                o.pysrc("\t\tif (rxrpc_post_dec(call) < 0)\n")
                o.pysrc("\t\t\treturn -1;\n")
                o.pysrc("\t\tif (call->bulk_index < call->bulk_count) {\n")
                o.pysrc("\t\t\tphase = ", phase_id, ";\n")
                o.pysrc("\t\t\tgoto select_phase;\n")
                o.pysrc("\t\t}\n")

        if phase.form == "split":
            o.pysrc("\t\tswitch (py_rxgen_split_receive(call, 0)) {\n")
            o.pysrc("\t\tcase -1: return -1;\n")
            o.pysrc("\t\tcase  0: break;\n")
            o.pysrc("\t\tcase  1: phase = ", phase_id, "; goto select_phase;\n")
            o.pysrc("\t\t}\n")
            #o.pysrc("\t\tif (rxrpc_post_dec(call) < 0)\n")
            #o.pysrc("\t\t\treturn -1;\n")
            #o.pysrc("\t\tif (call->need_size != 0) {\n")
            #o.pysrc("\t\t\tphase = ", phase_id, ";\n")
            #o.pysrc("\t\t\tgoto select_phase;\n")
            #o.pysrc("\t\t}\n")

        if phase.form != "bulk" and phase.form != "blob":
            o.pysrc("\t\tif (rxrpc_post_dec(call) < 0)\n")
            o.pysrc("\t\t\treturn -1;\n")

    o.pysrc("\n")
    o.pysrc("\t\t/* --- Phase ", next_phase_id, " --- */\n")
    if phase_goto_label:
        o.pysrc("\tphase_", next_phase_id, ":\n")
    o.pysrc("\t\tcall->phase = ", next_phase_id, ";\n")
    o.pysrc("\t\tcall->need_size = 0;\n")
    o.pysrc("\tdefault:\n")
    o.pysrc("\t\treturn 0;\n")
    o.pysrc("\t}\n")

    o.pysrc("}\n")
