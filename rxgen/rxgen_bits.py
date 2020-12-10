# Bits for rxgen implementation
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

import sys
from enum import Enum

class xdr_basic(Enum):
    int32 = 1
    int64 = 2
    string = 3
    opaque = 4
    struct = 5

class xdr_array(Enum):
    # single object is represented by None
    fixed = 1
    bulk = 2

class xdr_direction(Enum):
    IN = 1
    OUT = 2
    INOUT = 3

class xdr_context:
    def __init__(self):
        self.source = None              # Current source file
        self.lineno = None              # Current line number
        self.types = dict()             # List of types
        self.typedefs = dict()          # List of type aliases
        self.structs = dict()           # Structure definitions
        self.struct_sizes = dict()      # Structure sizes
        self.all_structs = list()       # Structures in order of declaration
        self.funcs = list()             # Functions in declaration order
        self.func_names = dict()        # Function name uniquifier
        self.constants = dict()         # Constants
        self.packages = dict()          # Packages
        self.pkg = None                 # Current package
        self.abort_syms = dict()        # Abort symbol to code map
        self.abort_ids = dict()         # Abort code to symbol map
        self.abort_count = 0            # Number of abort codes
        self.error_codes = False        # True if parsing error code list
        self.py_type_defs = list()      # Python type definitions
        self.py_func_defs = list()      # Python function definitions
        self.debug_level = False
        self.zero = xdr_constant("0", "0", self)
        self.typespecs = dict()

    def debug(self, *s):
        if (self.debug_level):
            print(*s)

    def error(self, *s):
        print("{:s}:{:d}: Error".format(self.source, self.lineno), *s)

    def add_package(self, name, prefix):
        if name in self.packages:
            self.error("Package {:s} already exists".format(name))
        else:
            pkg = xdr_package(name, prefix, self)
            self.packages[name] = pkg
            self.pkg = pkg
            self.debug("New package", name)

    def add_error_codes(self, codes):
        self.abort_count += len(codes)
        self.pkg.abort_codes += codes
        for code in codes:
            if not isinstance(code, xdr_constant):
                raise TypeError("Expecting xdr_constant, got " + str(type(code)))
            self.abort_syms[code.name] = code
            value = code.value
            suffix = ""
            if value.endswith("L"):
                value = value[0:-1]
                suffix = "L"
            if int(value) < 0:
                value = str(int(value) + 0x100000000)
            code.u32 = int(value)
            self.abort_ids[code.u32] = code

    def add_constant(self, name, value):
        if name in self.constants:
            self.error("Constant {:s} already exists".format(name))
        elif isinstance(value, xdr_constant):
            self.constants[name] = xdr_constant(name, value.value, self)
        else:
            self.constants[name] = xdr_constant(name, value, self)
            self.debug("New constant", name)
        return self.constants[name]

    def add_number(self, value):
        if value == 0:
            return self.zero
        return xdr_constant(value, value, self)

    def get_constant(self, name):
        if name not in self.constants:
            self.error("Constant {:s} undefined".format(name))
            return self.zero
        return self.constants[name]
    
    def add_type(self, name, typespec):
        if name in self.types:
            self.error("Type {:s} already exists".format(name))
        else:
            self.types[name] = typespec
            self.debug("New type", name)
        return self.types[name]
    
    def add_type_alias(self, name, alias):
        if name in self.typedefs:
            self.error("Type alias {:s} already exists".format(name))
            return self.typedefs[name]
        if name in self.structs:
            self.error("struct {:s} already exists, cannot shadow with alias".format(name))
            return alias

        self.typedefs[name] = alias
        self.debug("New typedef", name)

    def get_type(self, name):
        if name in self.types:
            typespec = self.types[name]
        elif name in self.typedefs:
            typespec = self.typedefs[name].typespec
        else:
            raise RuntimeError("Undefined type requested" + name);
        if not isinstance(typespec, xdr_type):
            raise TypeError("Retrieved type object is not xdr_type" + name + str(typespec));
        typespec.referenced = True
        return typespec

    def add_proc(self, proc):
        if not isinstance(proc, xdr_proc):
            raise KeyError("proc is not an xdr_proc", name, proc);
        name = proc.name
        if name in self.func_names:
            self.error("Proc {:s} already exists".format(name))
        else:
            self.func_names[name] = proc
            self.funcs.append(proc)
            self.debug("New proc", name)
        return self.func_names[name]

    def finished_parsing(self):
        self.all_constants = list(self.constants.keys())
        self.all_constants.sort()
        self.all_types = list(self.types.keys())
        self.all_types.sort()


###############################################################################
#
# Token base class
#
###############################################################################
class token_base(object):
    def __init__(self):
        self.source = None
        self.lineno = None
        self.name = None
        self.type = None

    def __str__(self):
        return "{:s} {:s} at {:s}:{:d}".format(
            self.type, self.name, self.source, self.lineno)

###############################################################################
#
# XDR package
#
###############################################################################
class xdr_package(token_base):
    """The result of 'package ID'"""
    def __init__(self, name, prefix, xdr):
        self.type = 'package'
        self.name = name
        self.source = xdr.source
        self.lineno = xdr.lineno
        self.prefix = prefix
        self.abort_codes = list()

###############################################################################
#
# XDR constant
#
###############################################################################
class xdr_constant(token_base):
    """The result of 'CONST ID EQUALS constant SEMI'"""
    def __init__(self, name, value, xdr):
        self.type = 'const'
        self.name = name
        self.value = value
        self.source = xdr.source
        self.lineno = xdr.lineno
        if not isinstance(value, str):
            raise RuntimeError("Value should be a string");

    def get_value(self):
        if isinstance(self.value, xdr_constant):
            return self.value.get_value()
        return int(self.value)

    def __str__(self):
        return self.value

    def __repr__(self):
        return "constant {:s}={:s} at {:s}:{:d}".format(
            self.name, self.value, self.source, self.lineno)

###############################################################################
#
# XDR type definition
#
# Each type is specified by a hash of the following elements:
#
#       name            Name of non-anonymous type (char, {u,}int{8,16,32,64}_t, struct name)
#       basic           Basic XDR type (int32, int64, string, opaque, struct)
#       array           Array class (single, array, bulk)
#       dim             Number of elements in fixed-size array (or None)
#       max_size        Max elements in bulk array (if array/bulk)
#       members         Members of struct
#       xdr_size        Size of XDR encoded object
#       source/lineno   Where defined in which file
#
# Members/parameters take a copy of their parent type's hash and add:
#
#       name            Member or parameter name (overrides type name)
#       direction       Direction of parameter (IN, OUT or INOUT)
#
###############################################################################
class xdr_type(token_base):
    def __init__(self, xdr, base=None, name=None, c_name=None,
                 basic=None, array=None, dim=None, max_size=None,
                 xdr_size=None,
                 members=None):
        if not isinstance(xdr, xdr_context):
            raise TypeError("XDR context isn't")
        if array:
            if not isinstance(array, xdr_array):
                raise TypeError("Invalid array class")
            if array == xdr_array.fixed and not dim:
                raise RuntimeError("Dimension required for fixed-size array")
            if dim and max_size:
                raise RuntimeError("Can't be both variable and fixed-size array")
        elif basic == "string" or basic == "opaque" or base and base.is_blob():
            if dim:
                raise RuntimeError("Can't specify fixed dimension limits on string/opaque")
        else:
            if dim or max_size:
                raise RuntimeError("Can't specify dimension limits on non-array")

        self.source = xdr.source
        self.lineno = xdr.lineno
        self.referenced = False

        if base:
            if name:
               raise RuntimeError("Type basic name can't be changed on an extant type")
            if c_name:
               raise RuntimeError("Type C name can't be changed on an extant type")
            if basic:
               raise RuntimeError("Basic type can't be changed on an extant type")
            if members:
               raise RuntimeError("Members can't be added to an extant type")
            if not isinstance(base, xdr_type):
                raise TypeError("Base type is not a type", type(base))
            base.referenced = True
            self.referenced = True
            self.name = base.name
            self.c_name = base.c_name
            self.basic = base.basic
            self.array = base.array
            self.dim = base.dim
            self.max_size = base.max_size
            self.xdr_size = base.xdr_size
            self.members = base.members

            if array:
                if base.array:
                    xdr.error("Array-of-array not supported")
                self.array = array
                self.dim = dim
                self.max_size = max_size
                if self.xdr_size and dim:
                    self.xdr_size *= int(str(dim))
            elif self.is_single_blob() and max_size:
                if self.max_size:
                    xdr.error("Maximum size already set on string/opaque")
                self.max_size = max_size
        else:
            if name and not isinstance(name, str):
                raise TypeError("Type name is not a string")
            if c_name and not isinstance(c_name, str):
                raise TypeError("C type name is not a string")
            if basic and not isinstance(basic, xdr_basic):
                raise TypeError("Invalid basic XDR type")
            self.name = name
            self.c_name = c_name
            self.basic = basic
            self.array = array
            self.xdr_size = xdr_size
            self.array = array
            self.dim = dim
            self.max_size = max_size
            self.members = members
            self.xdr_size = xdr_size
            if members:
                if not isinstance(members, list):
                    raise RuntimeError("Members should be a list")
                self.xdr_size = 0
                for i in members:
                    if i.typespec.xdr_size:
                        self.xdr_size += i.typespec.xdr_size

        if not self.basic:
           raise RuntimeError("basic type unset")

        typespec = str(self)
        if typespec not in xdr.typespecs:
            xdr.typespecs[typespec] = self


    def is_int(self):
        return self.basic == xdr_basic.int32 or self.basic == xdr_basic.int64

    def is_int32(self):
        return self.basic == xdr_basic.int32

    def is_int64(self):
        return self.basic == xdr_basic.int64

    def is_string(self):
        return self.basic == xdr_basic.string

    def is_opaque(self):
        return self.basic == xdr_basic.opaque

    def is_struct(self):
        return self.basic == xdr_basic.struct

    def is_blob(self):
        return self.is_string() or self.is_opaque()
    
    def is_single_int(self):
        return not self.array and self.is_int()

    def is_single_int32(self):
        return not self.array and self.is_int32()

    def is_single_int64(self):
        return not self.array and self.is_int64()

    def is_single_string(self):
        return not self.array and self.is_string()

    def is_single_opaque(self):
        return not self.array and self.is_opaque()

    def is_single_blob(self):
        return not self.array and self.is_blob()

    def is_single_basic(self):
        return not self.array and not self.is_struct()

    def is_single_struct(self):
        return not self.array and self.is_struct()

    def is_single(self):
        return not self.array

    def is_array(self):
        return self.array == xdr_array.fixed

    def is_char_array(self):
        return self.array == xdr_array.fixed and self.name == "char"

    def is_int32_array(self):
        return self.array == xdr_array.fixed and self.is_int32()

    def is_int_array(self):
        return self.array == xdr_array.fixed and self.is_int()

    def is_struct_array(self):
        return self.array == xdr_array.fixed and self.is_struct()

    def is_bulk(self):
        return self.array == xdr_array.bulk

    def is_bulk_char(self):
        return self.is_bulk() and self.name == "char"

    def is_bulk_int32(self):
        return self.is_bulk() and self.is_int32()

    def is_bulk_int64(self):
        return self.is_bulk() and self.is_int64()

    def is_bulk_int(self):
        return self.is_bulk() and self.is_int()

    def is_bulk_struct(self):
        return self.is_bulk() and self.is_struct()

    def __str__(self):
        t = self.name
        if self.is_array():
            t += "[{:s}]".format(str(self.dim))
        elif self.is_bulk() or self.is_blob():
            if self.max_size:
                t += "<{:s}>".format(str(self.max_size))
            else:
                t += "<>"
        return t
    
###############################################################################
#
# XDR structure member definition
#
###############################################################################
class xdr_member(token_base):
    """A structure member"""
    def __init__(self, name, typespec, xdr):
        self.typespec = typespec
        self.name = name
        self.source = xdr.source
        self.lineno = xdr.lineno
        self.special = None
    
###############################################################################
#
# XDR type alias definition
#
###############################################################################
class xdr_type_alias(token_base):
    """A type alias"""
    def __init__(self, name, typespec, xdr):
        if not isinstance(typespec, xdr_type):
            raise TypeError("Base type is not a type")
        self.name = name
        self.typespec = typespec
        self.source = xdr.source
        self.lineno = xdr.lineno

###############################################################################
#
# XDR procedure member definition
#
###############################################################################
class xdr_proc(token_base):
    """An XDR procedure"""
    def __init__(self, name, xdr, params, opcode, multi=False, split=False):
        self.name = xdr.pkg.name + "_" + name
        self.source = xdr.source
        self.lineno = xdr.lineno
        self.params = params
        self.opcode = opcode
        self.multi = multi
        self.split = split

###############################################################################
#
# Generated file writer class
#
###############################################################################
class file_generator:
    """File generator class"""
    def __init__(self, xdr):
        self.xdr = xdr
        self._rxhdr = open("2_afs_xg.h", "w", encoding="utf-8")
        self._rxsrc = open("2_afs_xg.c", "w", encoding="utf-8")
        self._pyhdr = open("2_afs_py.h", "w", encoding="utf-8")
        self._pysrc = open("2_afs_py.c", "w", encoding="utf-8")

    def rxhdr(self, *va):
        for i in va:
            self._rxhdr.write(str(i))

    def rxsrc(self, *va):
        for i in va:
            self._rxsrc.write(str(i))

    def pyhdr(self, *va):
        for i in va:
            self._pyhdr.write(str(i))

    def pysrc(self, *va):
        for i in va:
            self._pysrc.write(str(i))

    def rxhdrf(self, fmt, *va):
        self._rxhdr.write(fmt.format(*va))

    def rxsrcf(self, fmt, *va):
        self._rxsrc.write(fmt.format(*va))

    def pyhdrf(self, fmt, *va):
        self._pyhdr.write(fmt.format(*va))

    def pysrcf(self, fmt, *va):
        self._pysrc.write(fmt.format(*va))

    def where(self, loc):
        self._where = loc + ": "
        
    def error(self, *va):
        if self._where:
            sys.stdout.write(self._where)
        for i in va:
            sys.stdout.write(str(i))
        sys.stdout.write("\n")

###############################################################################
#
# Python type def
#
###############################################################################
class py_type_def:
    def __init__(self, name, c_type):
        self.name = name
        self.c_type = c_type

###############################################################################
#
# Python function def
#
###############################################################################
class py_func_def:
    def __init__(self, name, c_func, doc=""):
        self.name = name
        self.c_func = c_func
        self.doc = doc
