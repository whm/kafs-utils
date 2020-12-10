#!/usr/bin/python3
#
# Emit C structure
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
# Emit structure encoders and decoders predeclarations
#
###############################################################################
def emit_struct_encdec_decl(o, struct):
    o.rxsrc("/* ", struct.name, " XDR size ", struct.xdr_size, " */\n")

###############################################################################
#
# Emit structure encoders and decoders
#
###############################################################################
def emit_struct_encdec(o, struct):
    # Write out a C structure definition for this type
    o.rxhdr("struct ", struct.name, " {\n")
    for m in struct.members:
        ty = m.typespec
        o.where(struct.name + "::" + m.name)
        if ty.is_single():
            o.rxhdr("\t", ty.c_name, "\t", m.name)
        elif ty.is_int_array() or ty.is_struct_array():
            o.rxhdr("\t", ty.c_name, "\t", m.name, "[", ty.dim, "]")
        else:
            o.error("Unsupported type '", ty, "'\n")
        o.rxhdr(";\n")
    o.rxhdr("};\n")

    # Write an encoding function
    o.rxhdr("extern void rxgen_encode_", struct.name,
            "(struct rx_call *call, const struct ", struct.name, " *p);\n")

    o.rxsrc("void rxgen_encode_", struct.name,
            "(struct rx_call *call, const struct ", struct.name, " *p)\n")
    o.rxsrc("{\n")

    for m in struct.members:
        ty = m.typespec
        if ty.is_array():
            o.rxsrc("\tint i;\n\n")
            break

    for m in struct.members:
        ty = m.typespec
        o.where(struct.name + "::" + m.name)
        if ty.is_single_int32():
            o.rxsrc("\trxrpc_enc(call, p->", m.name, ");\n")
        elif ty.is_single_struct():
            o.rxsrc("\trxgen_encode_", ty.name, "(call, &p->", m.name, ");\n")
        elif ty.is_array():
            o.rxsrc("\tfor (i = 0; i < ", ty.dim.name, "; i++)\n")
            if ty.is_int32_array():
                o.rxsrc("\t\trxrpc_enc(call, p->", m.name, "[i]);\n")
            elif ty.is_struct_array():
                o.rxsrc("\t\trxgen_encode_", ty.name, "(call, &p->", m.name, "[i]);\n")
            else:
                o.error("No encoding for array type '", ty, "'")
        else:
            o.error("No encoding for type '", ty, "'")

    o.rxsrc("}\n")
    o.rxsrc("\n")

    # Write a decoding function
    o.rxhdr("extern void rxgen_decode_", struct.name,
            "(struct rx_call *call, struct ", struct.name, " *p);\n")

    o.rxsrc("void rxgen_decode_", struct.name,
            "(struct rx_call *call, struct ", struct.name, " *p)\n")
    o.rxsrc("{\n")

    for m in struct.members:
        ty = m.typespec
        if ty.is_array():
            o.rxsrc("\tint i;\n\n")
            break

    for m in struct.members:
        ty = m.typespec
        o.where(struct.name + "::" + m.name)
        if ty.is_single_int32():
            o.rxsrc("\tp->", m.name, " = rxrpc_dec(call);\n")
        elif ty.is_single_struct():
            o.rxsrc("\trxgen_decode_", ty.name, "(call, &p->", m.name, ");\n")
        elif ty.is_array():
            o.rxsrc("\tfor (i = 0; i < ", ty.dim.name, "; i++)\n")
            if ty.is_int32_array():
                o.rxsrc("\t\tp->", m.name, "[i] = rxrpc_dec(call);\n")
            elif ty.is_struct_array():
                o.rxsrc("\t\trxgen_decode_", ty.name, "(call, &p->", m.name, "[i]);\n")
            else:
                o.error("No decoding for array type '", ty, "'")
        else:
            o.error("No decoding for type '", ty, "'")

    o.rxsrc("}\n")
