#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Tool for processing an RxRPC-based RPC API definition in a C header file to
# produce (un)marshalling code and RPC functions to implement that API.
#
# It also produces a python module containing wrappers for the types, RPC
# functions and constants in the API definition.

__copyright__ = """
Copyright (C) 2015 Red Hat, Inc. All Rights Reserved.
Written by David Howells (dhowells@redhat.com)

Yacc & Lex bits based on pynfs rpcgen.py code:

    Written by Fred Isaman <iisaman@citi.umich.edu>
    Copyright (C) 2004 University of Michigan, Center for
                       Information Technology Integration
    Based on version written by Peter Astrand <peter@cendio.se>
    Copyright (C) 2001 Cendio Systems AB (http://www.cendio.se)

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

import sys
import keyword
import time
import os
from rxgen_bits import *
from emit_c_struct import *
from emit_c_sync_funcs import *
from emit_py_types import *
from emit_py_sync_funcs import *
from emit_py_module import *

xdr = None              # Current context

##########################################################################
#                                                                        #
#                            Lexical analysis                            #
#                                                                        #
##########################################################################
import ply.lex as lex

basic_types = (
    ( "char",      "char",      xdr_basic.int32,   4 ),
    ( "int8_t",    "int8_t",    xdr_basic.int32,   4 ),
    ( "int16_t",   "int16_t",   xdr_basic.int32,   4 ),
    ( "int32_t",   "int32_t",   xdr_basic.int32,   4 ),
    ( "int64_t",   "int64_t",   xdr_basic.int64,   8 ),
    ( "uint8_t",   "uint8_t",   xdr_basic.int32,   4 ),
    ( "uint16_t",  "uint16_t",  xdr_basic.int32,   4 ),
    ( "uint32_t",  "uint32_t",  xdr_basic.int32,   4 ),
    ( "uint64_t",  "uint64_t",  xdr_basic.int64,   8 ),
    ( "string",    "char",      xdr_basic.string,  4 ),
    ( "opaque",    "void",      xdr_basic.opaque,  4 ),
    )

def load_basic_types(xdr):
    global basic_types
    for i in basic_types:
        name = i[0]
        t = xdr_type(xdr, name=name, c_name=i[1], basic=i[2], xdr_size=i[3])
        xdr.types[name] = t

keywords = (
    "IN",
    "INOUT",
    "OUT",
    "const",
    "enum",
    "multi",
    "package",
    "split",
    "struct",
    "typedef",
) + tuple([i[0] for i in basic_types])

# Required by lex.  Each token also allows a function t_<token>.
tokens = tuple([t.upper() for t in keywords]) + (
    "ID", "CONST10", "CONST8", "CONST16",
    # ( ) [ ] { }
    "LPAREN", "RPAREN", "LSQUARE", "RSQUARE", "LBRACE", "RBRACE",
    # ; : < > * = ,
    "SEMI", "LT", "GT", "STAR", "EQUALS", "COMMA",
    "BEGIN_ERROR_CODES", "END_ERROR_CODES", "NEWFILE"
)

# t_<name> functions are used by lex.  They are called with t.value==<match
# of rule in comment>, and t.type==<name>.  They expect a return value
# with attribute type=<token>

# Tell lexer to ignore Whitespace.
t_ignore = " \t"

def t_NEWFILE(t):
    r'__NEWFILE__ [^\n]*'
    t.lexer.source = t.value[12:]
    t.lexer.lineno = 0
    return t

def t_ID(t):
    r'[A-Za-z][A-Za-z0-9_]*'
    if t.value in keywords:
        t.type = t.value.upper()
    return t

def t_CONST16(t):
    r'0x[0-9a-fA-F]+'
    return t

def t_CONST8(t):
    r'0[0-7]+'
    return t

def t_CONST10(t):
    r'-?(([1-9]\d*)|0)'
    return t

# Tokens
t_LPAREN           = r'\('
t_RPAREN           = r'\)'
t_LSQUARE          = r'\['
t_RSQUARE          = r'\]'
t_LBRACE           = r'\{'
t_RBRACE           = r'\}'
t_SEMI             = r';'
t_LT               = r'<'
t_GT               = r'>'
t_STAR             = r'\*'
t_EQUALS           = r'='
t_COMMA            = r','
t_BEGIN_ERROR_CODES = r'__BEGIN_ERROR_CODES__'
t_END_ERROR_CODES  = r'__END_ERROR_CODES__'

def t_newline(t):
    r'\n+'
    t.lexer.lineno += t.value.count("\n")

def t_error(t):
    print("Illegal character {:s} at {:d} type {:s}".format(repr(t.value[0]),
                                                            t.lineno, t.type))
    t.lexer.skip(1)

# Build the lexer
lex.lex(debug=0)

##########################################################################
#                                                                        #
#                          Yacc Parsing Info                             #
#                                                                        #
##########################################################################

def p_specification(t):
    '''specification : NEWFILE definition_list'''

def p_definition_list(t):
    '''definition_list : definition definition_list
                       | empty'''

def p_definition(t):
    '''definition : package_def
                  | constant_def
                  | enum_def
                  | type_def
                  | error_code_list_def
                  | proc_spec'''

def p_package_def(t):
    '''package_def : PACKAGE ID'''
    prefix = t[2]
    name = t[2]
    if name.endswith("_"):
        name = name[:-1]
    global xdr
    xdr.lineno = t.lineno(1)
    xdr.add_package(name, prefix)

###############################################################################
#
# Constants and values
#
def p_constant_def(t):
    '''constant_def : CONST ID EQUALS constant SEMI'''
    name = t[2]
    value = t[4]
    global xdr
    xdr.lineno = t.lineno(1)
    t[0] = xdr.add_constant(name, value)

def p_constant(t):
    '''constant : CONST10
                | CONST8
                | CONST16'''
    value = t[1]
    if len(value) > 9:
        value = value + 'L'
    global xdr
    xdr.lineno = t.lineno(1)
    t[0] = xdr.add_number(value)

def p_value_1(t):
    '''value : constant'''
    t[0] = t[1]

def p_value_2(t):
    '''value : ID'''
    name = t[1]
    global xdr
    xdr.lineno = t.lineno(1)
    t[0] = xdr.get_constant(name)

def p_optional_value(t):
    '''optional_value : value
                      | empty'''
    # return value or None.
    t[0] = t[1]

def p_constant_list_1(t):
    '''constant_list  : constant_def constant_list'''
    t[0] = [t[1]] + t[2]

def p_constant_list_2(t):
    '''constant_list  : constant_def'''
    t[0] = [t[1]]

def p_error_code_list_def(t):
    '''error_code_list_def : BEGIN_ERROR_CODES constant_list END_ERROR_CODES'''
    global xdr
    xdr.lineno = t.lineno(1)
    xdr.add_error_codes(t[2])

def p_enum_def(t):
    '''enum_def       : ENUM ID LBRACE enum_list RBRACE SEMI'''
    '''enum_def       : ENUM ID LBRACE enum_list COMMA RBRACE SEMI'''
    name = t[2]
    global xdr
    xdr.lineno = t.lineno(1)
    enum = xdr_type(xdr, base=xdr.get_type("int32_t"))
    t[0] = xdr.add_type(name, enum)

def p_enum_list_1(t):
    '''enum_list      : enum_term'''
    t[0] = [t[1]]

def p_enum_list_2(t):
    '''enum_list      : enum_term COMMA enum_list'''
    t[0] = [t[1]] + t[3]

def p_enum_term(t):
    '''enum_term      : ID EQUALS constant'''
    name = t[1]
    value = t[3]
    global xdr
    xdr.lineno = t.lineno(1)
    t[0] = xdr.add_constant(name, value)

###############################################################################
#
# Type definition
#
def p_type_def_1(t):
    '''type_def : TYPEDEF declaration SEMI'''
    name = t[2].name
    typespec = t[2].typespec
    global xdr
    xdr.lineno = t.lineno(1)
    alias = xdr_type_alias(name, typespec, xdr)
    xdr.add_type_alias(name, alias)
    #xdr.debug("Typedef", name)

def p_type_def_2(t):
    '''type_def : STRUCT ID struct_body SEMI'''
    name = t[2]
    body = t[3]
    global xdr
    xdr.lineno = t.lineno(1)
    if name in xdr.structs:
        xdr.error("Structure {:s} already exists".format(name))
    else:
        s = xdr_type(xdr, name=name, c_name="struct " + name,
                     basic=xdr_basic.struct, members=body)
        xdr.structs[name] = s
        xdr.all_structs.append(s)
        xdr.add_type(name, s)
    xdr.debug("New struct", name)

###############################################################################
#
# Type specification
#
def p_declaration_1(t):
    '''declaration : type_specifier ID'''
    typespec = t[1]
    name = t[2]
    global xdr
    xdr.lineno = t.lineno(1)
    t[0] = xdr_member(name, typespec, xdr);

def p_declaration_2(t):
    '''declaration : type_specifier STAR ID'''
    # We ignore the pointer type marker
    typespec = t[1]
    name = t[3]
    global xdr
    xdr.lineno = t.lineno(1)
    ty = xdr_type(xdr, base=typespec)
    t[0] = xdr_member(name, ty, xdr)

def p_declaration_3(t):
    '''declaration : type_specifier ID LSQUARE value RSQUARE'''
    typespec = t[1]
    name = t[2]
    array_size = t[4]
    if not isinstance(typespec, xdr_type):
        raise RuntimeError("Type is not type" + str(typespec))
    global xdr
    xdr.lineno = t.lineno(1)
    ty = xdr_type(xdr, base=typespec, array=xdr_array.fixed, dim=array_size)
    t[0] = xdr_member(name, ty, xdr)

def p_declaration_4(t):
    '''declaration : type_specifier ID LT optional_value GT'''
    typespec = t[1]
    name = t[2]
    max_size = t[4]
    global xdr
    xdr.lineno = t.lineno(1)
    if typespec.is_single_blob():
        ty = xdr_type(xdr, base=typespec, max_size=max_size)
    else:
        ty = xdr_type(xdr, base=typespec, array=xdr_array.bulk, max_size=max_size)
    t[0] = xdr_member(name, ty, xdr)

def p_declaration_5(t):
    '''declaration : type_specifier STAR ID LT optional_value GT'''
    typespec = t[1]
    name = t[3]
    max_size = t[5]
    global xdr
    xdr.lineno = t.lineno(1)
    if typespec.is_single_blob():
        ty = xdr_type(xdr, base=typespec, max_size=max_size)
    else:
        ty = xdr_type(xdr, base=typespec, array=xdr_array.bulk, max_size=max_size)
    t[0] = xdr_member(name, ty, xdr)

def p_declaration_6(t):
    '''declaration : type_specifier LT optional_value GT STAR ID'''
    typespec = t[1]
    max_size = t[3]
    name = t[6]
    global xdr
    xdr.lineno = t.lineno(1)
    ty = xdr_type(xdr, base=typespec, array=xdr_array.bulk, max_size=max_size)
    t[0] = xdr_member(name, ty, xdr)

def p_type_specifier_1(t):
    '''type_specifier : CHAR
                      | INT8_T
                      | INT16_T
                      | INT32_T
                      | INT64_T
                      | UINT8_T
                      | UINT16_T
                      | UINT32_T
                      | UINT64_T
                      | STRING
                      | OPAQUE'''
    name = t[1]
    global xdr
    xdr.lineno = t.lineno(1)
    t[0] = xdr.types[name]
    if not isinstance(t[0], xdr_type):
        raise RuntimeError("Type is not type" + typespec);

def p_type_specifier_2(t):
    '''type_specifier : ID'''
    name = t[1]
    global xdr
    xdr.lineno = t.lineno(1)
    t[0] = xdr.get_type(t[1])

def p_type_specifier_3(t):
    '''type_specifier : struct_type_spec'''
    t[0] = t[1]

def p_type_specifier_4(t):
    '''type_specifier : STRUCT ID'''
    name = t[2]
    global xdr
    xdr.lineno = t.lineno(1)
    t[0] = xdr.get_type(name)


###############################################################################
#
# Structure specification
#
def p_struct_type_spec(t):
    '''struct_type_spec : STRUCT struct_body'''
    t[0] = xdr_type(xdr, name="<anon struct {:s}>".format(t.lineno), c_name="struct",
                    compound=xdr_compound.struct, basic_type="struct", members=t[2])

def p_struct_body(t):
    '''struct_body : LBRACE member_list RBRACE'''
    t[0] = t[2]

def p_member_list_1(t):
    '''member_list : declaration SEMI'''
    t[0] = [t[1]]

def p_member_list_2(t):
    '''member_list : declaration SEMI member_list'''
    t[0] = [t[1]] + t[3]

###############################################################################
#
# Procedure specification
#
def p_proc_spec_1(t):
    '''proc_spec : ID LPAREN parameters RPAREN EQUALS value SEMI'''
    name = t[1]
    params = t[3]
    op = t[6]
    global xdr
    proc = xdr_proc(name, xdr, params, op)
    xdr.add_proc(proc)

def p_proc_spec_2(t):
    '''proc_spec : ID LPAREN parameters RPAREN SPLIT EQUALS value SEMI'''
    name = t[1]
    params = t[3]
    op = t[7]
    global xdr
    proc = xdr_proc(name, xdr, params, op, split=True)
    xdr.add_proc(proc)

def p_proc_spec_3(t):
    '''proc_spec : ID LPAREN parameters RPAREN MULTI EQUALS value SEMI'''
    name = t[1]
    params = t[3]
    op = t[7]
    global xdr
    proc = xdr_proc(name, xdr, params, op, multi=True)
    xdr.add_proc(proc)

def p_parameters_0(t):
    '''parameters : '''
    t[0] = []

def p_parameters_1(t):
    '''parameters : parameter'''
    t[0] = [t[1]]

def p_parameters_2(t):
    '''parameters : parameter COMMA parameters'''
    t[0] = [t[1]] + t[3]

def p_parameter_1(t):
    '''parameter : IN declaration'''
    t[2].direction = xdr_direction.IN
    t[0] = t[2]

def p_parameter_2(t):
    '''parameter : INOUT declaration'''
    t[2].direction = xdr_direction.INOUT
    t[0] = t[2]

def p_parameter_3(t):
    '''parameter : OUT declaration'''
    t[2].direction = xdr_direction.OUT
    t[0] = t[2]

###############################################################################
#
# Miscellany
#
def p_empty(t):
    'empty :'

def p_error(t):
    global error_occurred
    error_occurred = True
    if t:
        print(t)
        print("Syntax error at '{:s}' (lineno {:d})".format(t.value, t.lineno))
    else:
        print("Syntax error: unexpectedly hit EOF")

##########################################################################
#                                                                        #
#                          Global Variables                              #
#                                                                        #
##########################################################################

error_occurred = False # Parsing of infile status



##########################################################################
#                                                                        #
#                       C Preprocessor                                   #
#                                                                        #
##########################################################################
def cpp(data, filename):
    # Remove C comments
    lines = data.splitlines()
    inside_C_comment = False
    inside_error_code_list = False

    for i in range(0, len(lines)):
        l = lines[i]
        begin = None
        if inside_C_comment:
            begin = 0
        cursor = 0

        # We need to capture the error code list so that we can build a set of
        # Python exceptions for it - but the only way to do that is to snoop
        # the comments
        #
        if not inside_C_comment:
            if l == "/* Error codes */" and not inside_error_code_list:
                inside_error_code_list = True
                lines[i] = "__BEGIN_ERROR_CODES__"
                continue

            if inside_error_code_list and l == "":
                inside_error_code_list = False
                lines[i] = "__END_ERROR_CODES__"
                continue

        while True:
            if inside_C_comment:
                p = l.find("*/", cursor)
                if p == -1:
                    l = l[:begin]
                    lines[i] = l
                    break
                l = l[:begin] + l[p + 2:]
                lines[i] = l
                cursor = begin
                begin = None
                inside_C_comment = False
            else:
                p = l.find("/*");
                if p == -1:
                    break
                inside_C_comment = True
                begin = p
                cursor += 2

    if inside_error_code_list:
        lines.append("__END_ERROR_CODES__")

    # Remove C++ comments
    for i in range(0, len(lines)):
        l = lines[i]
        p = l.find("//")
        if p != -1:
            lines[i] = l[:p]

    # Remove directives
    skipping = False
    for i in range(0, len(lines)):
        l = lines[i]
        if skipping:
            if l == "#endif":
                skipping = False;
            lines[i] = ""
            continue
        if l == "#if 0":
            skipping = True;
            lines[i] = ""
            continue
        if (l.startswith("#include") or
            l.startswith("#define") or
            l.startswith("%")):
            lines[i] = ""
            continue

    lines.insert(0, "__NEWFILE__ {:s}".format(filename))
    return "\n".join(lines)

##########################################################################
#                                                                        #
#                          Main Loop                                     #
#                                                                        #
##########################################################################
xdr = xdr_context()
load_basic_types(xdr)
xdr.add_constant("RXRPC_SECURITY_PLAIN",   "0")
xdr.add_constant("RXRPC_SECURITY_AUTH",    "1")
xdr.add_constant("RXRPC_SECURITY_ENCRYPT", "2")

# Parse the input data with yacc
import ply.yacc as yacc
yacc.yacc(debug=0)

def parse(infile, debug=False):
    global xdr
    xdr.source = infile
    xdr.lineno = 0

    f = open(infile)
    data = f.read()
    f.close()

    data = cpp(data, infile)

    print("Parsing", infile);
    global yacc
    yacc.parse(data, debug=debug)

    if error_occurred:
        print
        print("Error occurred, did not write output files")
        return False
    return True

#
# Section: main
#
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: {:s} <filename>*".format(sys.argv[0]))
        sys.exit(1)

    for f in sys.argv[1:]:
        if not parse(f):
            break

    xdr.finished_parsing()

    o = file_generator(xdr)
    o.rxhdr("/* AUTOGENERATED */\n")
    #o.rxhdr("#define _XOPEN_SOURCE\n";
    o.rxhdr("#include <stdint.h>\n")
    o.rxhdr("#include \"rxgen.h\"\n")

    o.rxsrc("/* AUTOGENERATED */\n")
    o.rxsrc("#include \"afs_xg.h\"\n")
    o.rxsrc("#include <stdio.h>\n")
    o.rxsrc("#include <stdlib.h>\n")
    o.rxsrc("#include <string.h>\n")
    o.rxsrc("#include <unistd.h>\n")
    o.rxsrc("#include <errno.h>\n")
    o.rxsrc("#include <sys/socket.h>\n")
    o.rxsrc("#include <sys/param.h>\n")
    o.rxsrc("#include <arpa/inet.h>\n")
    o.rxsrc("\n")

    o.pyhdr("/* AUTOGENERATED */\n")
    o.pyhdr("#include <Python.h>\n")
    o.pyhdr("#include \"afs_xg.h\"\n")
    o.pyhdr("#include \"py_rxgen.h\"\n")

    o.pysrc("/* AUTOGENERATED */\n")
    o.pysrc("#include <Python.h>\n")
    o.pysrc("#include \"structmember.h\"\n")
    o.pysrc("#include \"afs_py.h\"\n")
    o.pysrc("#include <arpa/inet.h>\n")
    o.pysrc("\n")

    # Declare constants
    o.rxhdr("\n")
    for name in xdr.all_constants:
        c = xdr.constants[name]
        o.rxhdr("#define ", c.name, " ", c.value, "\n")

    # Declare structure types
    for s in xdr.all_structs:
        emit_struct_encdec_decl(o, s)
        emit_py_type_wrapper_decls(o, s)

    for s in xdr.all_structs:
        emit_struct_encdec(o, s);
        emit_py_type_wrapper(o, s);

    # Emit RPC call functions.  For this we need to classify parameters according
    # to input and output usage and work out how big the RPC messages will be.
    #
    for f in xdr.funcs:
        # Dump the banner comment block
        o.rxsrc("/*\n")
        o.rxsrc(" * RPC Call ", f.name, "\n")
        o.rxsrc(" */\n")

        # Find the Operation ID
        if not f.opcode:
            raise RuntimeError("Operation ID unspecified for " + f.name)

        # Filter the parameters into request and response
        f.request = list()
        f.response = list()

        for p in f.params:
            o.where(f.name + ":" + p.name)
            ty = p.typespec
            if ty.is_single_basic():
                pass
            elif ty.is_struct():
                assert(ty.xdr_size)
            elif ty.is_single_blob():
                # Could validate max_size attribute
                pass
            elif ty.is_bulk():
                assert(ty.xdr_size)
            else:
                raise RuntimeError("Unsupported param type \"" + str(ty) + "\"")

            if p.direction == xdr_direction.IN:
                f.request.append(p)
            elif p.direction == xdr_direction.OUT:
                f.response.append(p)
            elif p.direction == xdr_direction.INOUT:
                f.request.append(p)
                f.response.append(p)

        emit_func_prototype(o, f)
        emit_func_decode(o, f, "client", "response", f.response)
        emit_func_send(o, f, "request")
        #emit_func_decode(f, "server", "request", request)
        #emit_func_send(f, "response")

        emit_py_func_param_object(o, f, "request")
        emit_py_func_param_object(o, f, "response")
        emit_py_func_bulk_helper(o, f)
        emit_py_func_decode(o, f, "client", "response", f.response)
        emit_py_func_decode(o, f, "server", "request", f.request)
        emit_py_func_simple_sync_call(o, f)

    emit_py_module(o);
