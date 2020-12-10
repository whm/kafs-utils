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

###############################################################################
#
# Calculate the C function prototypes
#
###############################################################################
def emit_func_prototype(o, func):
    # Function prototype lists (we add commas and the closing bracket later)
    protos = list()
    protos.append("int " + func.name + "(\n")
    send_request_protos = list()
    send_response_protos = list()
    recv_request_protos = list()
    recv_response_protos = list()

    # Arguments to pass when sending a call or processing a reply
    send_args = list()
    recv_args = list()

    for p in func.params:
        o.where(func.name + ":" + p.name)
        ty = p.typespec
        enclines = list()
        declines = list()
        args = list()

        if ty.is_array():
            raise RuntimeError("Array arg not supported")
        elif ty.is_bulk():
            # Encode
            if ty.is_bulk_struct():
                proto = "int (*get__" + p.name + ")(struct rx_call *call, void *token)"
            else:
                proto = "int (*get__" + p.name + ")(struct rx_call *call, void *token)"

            enclines.append(proto)
            enclines.append("void *token__" + p.name)
            enclines.append("size_t nr__" + p.name)
            args.append("get__" + p.name)
            args.append("token__" + p.name)
            args.append("nr__" + p.name)

            # Decode
            if ty.is_bulk_struct():
                proto = "int (*alloc__" + p.name + ")(struct rx_call *call, void **token)"
                args.append("alloc__" + p.name)
            else:
                proto = "int (*store__" + p.name + ")(struct rx_call *call, void **token)"
                args.append("store__" + p.name)

            declines.append(proto)
            declines.append("void *token__" + p.name)
            declines.append("size_t nr__" + p.name)
            args.append("token__" + p.name)
        elif ty.is_single_blob():
            # Do we want to insert a "*" in the following?
            proto = ty.c_name + " *" + p.name
            enclines.append("size_t nr__" + p.name)
            enclines.append("const " + proto)

            declines.append("size_t nr__" + p.name)
            declines.append("void *token__" + p.name)
            declines.append("int (*alloc__" + p.name + ")(struct rx_call *call, void **token)")
            args.append("nr__" + p.name)
            args.append(p.name)
            args.append("alloc__" + p.name)
        else:
            enc_const = ""
            if not ty.is_single_int():
                enc_const = "const "
            proto = ty.c_name + " "
            if not ty.is_single_int():
                proto += "*"
            proto += p.name
            enclines.append(enc_const + proto)
            declines.append(proto)
            args.append(p.name)

        if p.direction == xdr_direction.IN or p.direction == xdr_direction.INOUT:
            send_request_protos += enclines
            recv_request_protos += declines
            send_args += args
        if p.direction == xdr_direction.OUT or p.direction == xdr_direction.INOUT:
            send_response_protos += enclines
            recv_response_protos += declines
            recv_args += args

    o.rxhdr("\n")
    o.rxhdr("/*\n")
    o.rxhdr(" * ", func.name, "\n")
    o.rxhdr(" */\n")

    if recv_request_protos:
        o.rxhdr("struct ", func.name, "_request {\n")
        for p in recv_request_protos:
            o.rxhdr("\t", p, ";\n")
        o.rxhdr("};\n")

    o.rxhdr("\n")
    if recv_response_protos:
        o.rxhdr("struct ", func.name, "_response {\n")
        for p in recv_response_protos:
            o.rxhdr("\t", p, ";\n")
        o.rxhdr("};\n")

    # # Terminate each line with a comma, excepting the last, which we terminate
    # # with a closing bracket.
    # for (my $i = 1; $i < $#protos; $i++:
    #   protos[$i] .= ",\n")
    # }
    # protos[$#protos] .= ")")

    # for (my $i = 1; $i < $#send_protos; $i++:
    #   $send_protos[$i] .= ",\n")
    # }
    # $send_protos[$#send_protos] .= ")")

    # for (my $i = 1; $i < $#recv_protos; $i++:
    #   $recv_protos[$i] .= ",\n")
    # }
    # $recv_protos[$#recv_protos] .= ")")

    func.protos = protos
    func.send_request_protos = send_request_protos
    func.recv_request_protos = recv_request_protos
    func.send_response_protos = send_response_protos
    func.recv_response_protos = recv_response_protos
    func.send_args = send_args
    func.recv_args = recv_args

###############################################################################
#
# Emit a function to decode a block in a way that can be used from asynchronous
# code.  The opcode is expected to have been removed from the incoming call on
# the server side.
#
###############################################################################
class decode_phase:
    def __init__(self, form="flat", size=0, xdr_size=0, name=None):
        self.form = form
        self.size = size
        self.params = list()
        self.xdr_size = xdr_size
        self.elem_count = 0
        self.name = name

def emit_func_decode(o, func, side, subname, params):
    # We fetch the data in a number of phases.  Each phase receives a chunk of
    # data of a certain size.  A phase's size might be dependent on a variable
    # in the previous phase.  Variable-sized bulk arrays are split across
    # multiple phases, with the length being at the end of the first phase and
    # the data in the second.
    phases = list()
    phase = None
    have_bulk = False

    for p in params:
        o.where(func.name + ":" + p.name)
        ty = p.typespec

        if not phase:
            phase = decode_phase()
            phases.append(phase)

        if ty.is_single_int() or ty.is_single_struct():
            phase.size += ty.xdr_size
            phase.params.append(p)
        elif ty.is_single_blob():
            have_bulk = True

            # Blob objects begin with a size for which we institute a special
            # parameter
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
            phase = None

        elif ty.is_bulk():
            have_bulk = True

            # Bulk objects begin with an element count for which we institute a
            # special parameter
            phase.elem_count = phase.size
            phase.size +=  4

            count_type = xdr_type(o.xdr, base=o.xdr.get_type("uint32_t"))
            pseudoparam = xdr_member("nr__" + p.name, count_type, o.xdr)
            pseudoparam.special = "bulk_size"
            phase.params.append(pseudoparam)

            # Create a new phase
            phase = decode_phase(form="bulk", name=p.name, size=4, xdr_size=ty.xdr_size)
            phase.params.append(p)
            phases.append(phase)

            # We don't want to be asking recvmsg() for one object at a time if
            # they're really small.
            n_buf = 1
            if ty.xdr_size < 1020:
                n_buf = int(1020 / ty.xdr_size)
            n_buf *= ty.xdr_size
            phase.size = ty.xdr_size
            phase = None

        else:
            raise RuntimeError("Reply array not supported")

    # Function definition and arguments
    o.rxsrc("\n")
    o.rxsrc("static int rxgen_decode_", func.name, "_", subname, "(struct rx_call *call)\n")
    o.rxsrc("{\n")

    if not params:
        o.rxsrc("\treturn 0;\n")
        o.rxsrc("}\n")
        return

    # Local variables
    o.rxsrc("\tstruct ", func.name, "_", subname, " *obj = call->decoder_private;\n")
    o.rxsrc("\tunsigned count;\n")
    o.rxsrc("\tunsigned phase = call->phase;\n")

    # Deal with each phase
    o.rxsrc("\n")
    if have_bulk:
        o.rxsrc("select_phase:\n")
    o.rxsrc("\tcount = call->data_count;\n")
    o.rxsrc("\tswitch (phase) {\n")

    o.rxsrc("\tcase 0:\n")

    next_phase_id = 1
    for phase in phases:
        phase.phase_id = next_phase_id
        next_phase_id += 1

    phase_goto_label = None
    for phase in phases:
        phase_id = phase.phase_id
        o.rxsrc("\n")
        o.rxsrc("\t\t/* --- Phase ", phase_id, " --- */\n")

        if phase_goto_label == phase_id:
            o.rxsrc("\tphase_", phase_id, ":\n")
            phase_goto_label = None

        # Determine how big bulk objects are
        if phase.form == "blob":
            p = phase.params[0]
            o.rxsrc("\t\tcall->blob_size = obj->nr__", p.name, ";\n")
            o.rxsrc("\t\tcall->blob_offset = UINT_MAX;\n")
            o.rxsrc("\t\tif (obj->alloc__", p.name, "(call, &obj->token__", p.name, ") < 0)\n")
            o.rxsrc("\t\t\treturn -1;\n")
            o.rxsrc("\t\tif (call->blob_size == 0)\n")
            o.rxsrc("\t\t\tgoto phase_", phase_id + 1, ";\n")
            phase_goto_label = phase_id + 1
            o.rxsrc("\t\tcall->blob_offset = 0;\n")
        elif phase.form == "bulk":
            p = phase.params[0]
            o.rxsrc("\t\tcall->bulk_count = obj->nr__", p.name, ";\n")
            o.rxsrc("\t\tcall->bulk_index = UINT_MAX;\n")

            if ty.is_bulk_int():
                o.rxsrc("\t\tif (obj->store__", p.name, "(call, &obj->token__", p.name, ") < 0)\n")
            else:
                o.rxsrc("\t\tif (obj->alloc__", p.name, "(call, &obj->token__", p.name, ") < 0)\n")

            o.rxsrc("\t\t\treturn -1;\n")
            o.rxsrc("\t\tif (call->bulk_count == 0)\n")
            o.rxsrc("\t\t\tgoto phase_", phase_id + 1, ";\n")
            phase_goto_label = phase_id + 1
            o.rxsrc("\t\tcall->bulk_index = 0;\n")
        else:
            o.rxsrc("\t\tcall->need_size = ", phase.size, ";\n")

        # Entry point for a phase
        o.rxsrc("\t\tcall->phase = ", phase_id, ";\n")
        o.rxsrc("\tcase ", phase_id, ":\n")

        o.rxsrc("\t\tif (count < ", phase.size, ")")
        if phase.form == "bulk" and phase.xdr_size <= 512:
            o.rxsrc(" {\n")
            o.rxsrc("\t\t\tunsigned n = call->bulk_count - call->bulk_index;\n")
            o.rxsrc("\t\t\tn = MIN(n, ", int(1024 / phase.xdr_size), ");\n")
            o.rxsrc("\t\t\tcall->need_size = n * ", phase.xdr_size, ";\n")
            o.rxsrc("\t\t\treturn 1;\n")
            o.rxsrc("\t\t}")
        else:
            o.rxsrc("\n")
            o.rxsrc("\t\t\treturn 1;\n")

        # Unmarshal the data
        o.rxsrc("\n")
        for p in phase.params:
            o.where(func.name + ":" + p.name)
            ty = p.typespec
            if p.special == None:
                pass
            elif p.special == "blob_size" or p.special == "bulk_size":
                o.rxsrc("\t\tobj->", p.name, " = rxrpc_dec(call);\n")
                continue
            else:
                raise RuntimeError

            if ty.is_bulk_int():
                if ty.is_bulk_int32():
                    o.rxsrc("\t\tcall->bulk_u32 = rxrpc_dec(call);\n")
                    o.rxsrc("\t\tif (obj->store__", p.name, "(call, &obj->token__", p.name, ") < 0)\n")
                elif ty.is_bulk_int64():
                    o.rxsrc("\t\tcall->bulk_u64  = (uint64_t)rxrpc_dec(call) << 32;\n")
                    o.rxsrc("\t\tcall->bulk_u64 |= (uint64_t)rxrpc_dec(call);\n")
                    o.rxsrc("\t\tif (obj->store__", p.name, "(call, &obj->token__", p.name, ") < 0)\n")
                else:
                    raise RuntimeError
                o.rxsrc("\t\t\treturn -1;\n")
                o.rxsrc("\t\tcall->bulk_index++;\n")

            elif ty.is_bulk_struct():
                o.rxsrc("\t\tif (obj->alloc__", p.name, "(call, &obj->token__", p.name, ") < 0)\n")
                o.rxsrc("\t\t\treturn -1;\n")
                o.rxsrc("\t\trxgen_decode_", ty.name, "(call, call->bulk_item);\n")
                o.rxsrc("\t\tcall->bulk_index++;\n")
            elif ty.is_single_blob():
                o.rxsrc("\t\trxrpc_dec_blob(call);\n")
                o.rxsrc("\t\trxrpc_dec_align(call);\n")
            elif ty.is_single_int32():
                o.rxsrc("\t\tobj->", p.name, " = rxrpc_dec(call);\n")
            elif ty.is_single_int64():
                o.rxsrc("\t\tobj->", p.name, "  = (uint64_t)rxrpc_dec(call) << 32;\n")
                o.rxsrc("\t\tobj->", p.name, " |= (uint64_t)rxrpc_dec(call);\n")
            elif ty.is_single_struct():
                o.rxsrc("\t\trxgen_decode_", ty.name, "(call, obj->", p.name, ");\n")
            else:
                raise RuntimeError("Unsupported type in decode " + str(ty))

            if ty.is_single_blob():
                o.rxsrc("\t\tif (rxrpc_post_dec(call) < 0)\n")
                o.rxsrc("\t\t\treturn -1;\n")
                o.rxsrc("\t\tif (call->blob_offset < call->blob_size) {\n")
                o.rxsrc("\t\t\tphase = ", phase_id, ";\n")
                o.rxsrc("\t\t\tgoto select_phase;\n")
                o.rxsrc("\t\t}\n")
            elif ty.is_bulk():
                o.rxsrc("\t\tif (rxrpc_post_dec(call) < 0)\n")
                o.rxsrc("\t\t\treturn -1;\n")
                o.rxsrc("\t\tif (call->bulk_index < call->bulk_count) {\n")
                o.rxsrc("\t\t\tphase = ", phase_id, ";\n")
                o.rxsrc("\t\t\tgoto select_phase;\n")
                o.rxsrc("\t\t}\n")

        # --- TODO: Check the following condition as it must always be true
        if phase.form != "blob" or phase.form != "bulk":
            o.rxsrc("\t\tif (rxrpc_post_dec(call) < 0)\n")
            o.rxsrc("\t\t\treturn -1;\n")

    o.rxsrc("\n")
    o.rxsrc("\t\t/* --- Phase ", next_phase_id, " --- */\n")
    if phase_goto_label:
        o.rxsrc("\tphase_", next_phase_id, ":\n")
    o.rxsrc("\t\tcall->phase = ", next_phase_id, ";\n")
    o.rxsrc("\t\tcall->need_size = 0;\n")
    o.rxsrc("\tdefault:\n")
    o.rxsrc("\t\treturn 0;\n")
    o.rxsrc("\t}\n")
    o.rxsrc("}\n")


###############################################################################
#
# Emit a function to encode and dispatch a request or a response
#
###############################################################################
def emit_func_send(o, func, what):
    # Function definition and arguments
    if what == "request":
        protos = func.send_request_protos
        params = func.request
        bad_ret = "NULL"
    else:
        protos = func.send_response_protos
        params = func.response
        bad_ret = "-1"

    o.rxsrc("\n")
    if what == "request":
        o.rxsrc("struct rx_call *", func.name + "(\n")
        o.rxsrc("\tstruct rx_connection *z_conn")
    else:
        o.rxsrc("int respond_to_", func.name + "(\n")
        o.rxsrc("\tstruct rx_call *call")

    for proto in protos:
        o.rxsrc(",\n\t", proto)

    if what == "request" and func.response:
        o.rxsrc(",\n")
        o.rxsrc("\tstruct ", func.name, "_response *response")

    o.rxsrc(")\n")
    o.rxsrc("{\n")

    if what == "request":
        o.rxsrc("\tstruct rx_call *call;\n")

    blob_params = list()
    bulk_params = list()
    for p in params:
        ty = p.typespec
        if ty.is_single_blob():
            blob_params.append(p)
        if ty.is_bulk():
            bulk_params.append(p)

    # Local variables
    o.rxsrc("\tint ret;\n")

    # Check lengths
    if blob_params or bulk_params:
        o.rxsrc("\n")
        o.rxsrc("\tif (")
        first = True
        for p in blob_params:
            o.where(func.name + ":" + p.name)
            ty = p.typespec
            if first:
                first = False
            else:
                o.rxsrc(" ||\n\t    ")
            o.rxsrc("!", p.name)
            if ty.max_size:
                o.rxsrc(" || nr__", p.name, " > ", ty.max_size.name)

        for p in bulk_params:
            o.where(func.name + ":" + p.name)
            ty = p.typespec
            if first:
                first = False
            else:
                o.rxsrc(" ||\n\t    ")
            o.rxsrc("!get__", p.name)
            if ty.max_size:
                o.rxsrc(" || nr__", p.name, " > ", ty.max_size.name)

        o.rxsrc(") {\n")
        o.rxsrc("\t\terrno = EINVAL;\n")
        o.rxsrc("\t\treturn ", bad_ret, ";\n")
        o.rxsrc("\t};\n")

    # Allocate call
    if what == "request":
        o.rxsrc("\n")
        o.rxsrc("\tcall = rxrpc_alloc_call(z_conn, 0);\n")
        o.rxsrc("\tif (!call)\n")
        o.rxsrc("\t\treturn ", bad_ret, ";\n")
        o.rxsrc("\tcall->decoder = rxgen_decode_", func.name, "_response;\n")
        if func.response:
            o.rxsrc("\tcall->decoder_private = response;\n")

    # Marshal the data
    if what == "request" or params:
        o.rxsrc("\n")
    if what == "request":
        o.rxsrc("\trxrpc_enc(call, ", func.opcode.name, ");\n")

    for p in params:
        o.where(func.name + ":" + p.name)
        ty = p.typespec
        if ty.is_single_int32():
            o.rxsrc("\trxrpc_enc(call, ", p.name, ");\n")
        elif ty.is_single_int64():
            o.rxsrc("\trxrpc_enc(call, (uint32_t)", p.name, ");\n")
            o.rxsrc("\trxrpc_enc(call, (uint32_t)(", p.name, " >> 32));\n")
        elif ty.is_single_struct():
            o.rxsrc("\trxgen_encode_", ty.name, "(call, ", p.name, ");\n")
        elif ty.is_single_blob():
            o.rxsrc("\trxrpc_enc_blob(call, ", p.name, ", nr__", p.name, ");\n")
            o.rxsrc("\trxrpc_enc_align(call);\n")
        elif ty.is_bulk():
            o.rxsrc("\trxrpc_enc(call, nr__", p.name, ");\n")
            o.rxsrc("\tcall->bulk_count = nr__", p.name, ";\n")
            o.rxsrc("\tfor (call->bulk_index = 0; call->bulk_index < call->bulk_count; call->bulk_index++) {\n")
            o.rxsrc("\t\t", ty.c_name, " x;\n")

            o.rxsrc("\t\tcall->bulk_item = &x;\n")
            o.rxsrc("\t\tif (get__", p.name, "(call, token__", p.name, ") < 0)\n")
            o.rxsrc("\t\t\tgoto error;\n")
            if ty.is_bulk_int32():
                if not ty.name.startswith("u"):
                    o.rxsrc("\t\trxrpc_enc(call, (u", ty.name, ")x);\n")
                else:
                    o.rxsrc("\t\trxrpc_enc(call, x);\n")
            elif ty.is_bulk_int64():
                o.rxsrc("\t\trxrpc_enc(call, (uint32_t)", p.name, ");\n")
                o.rxsrc("\t\trxrpc_enc(call, (uint32_t)(", p.name, " >> 32));\n")
            elif ty.is_bulk_struct():
                o.rxsrc("\t\trxgen_encode_", ty.name, "(call, &x);\n")
            else:
                raise RuntimeError("No decoding for array type '" + str(ty) + "'")

            o.rxsrc("\t}\n")
        else:
            raise RuntimeError("Unsupported param encoding")

    o.rxsrc("\tif (rxrpc_post_enc(call) < 0)\n")
    o.rxsrc("\t\tgoto error;\n")
    o.rxsrc("\tcall->more_send = 0;\n")

    # Send the message
    o.rxsrc("\n")
    o.rxsrc("\tret = rxrpc_send_data(call);\n")
    o.rxsrc("\tif (ret < 0)\n")
    o.rxsrc("\t\tgoto error;\n")
    if what == "request":
        o.rxsrc("\treturn call;\n")
    else:
        o.rxsrc("\treturn 0;\n")

    o.rxsrc("\n")
    o.rxsrc("error:\n")
    o.rxsrc("\trxrpc_terminate_call(call, 0);\n")
    o.rxsrc("\treturn ", bad_ret, ";\n")
    o.rxsrc("}\n")
