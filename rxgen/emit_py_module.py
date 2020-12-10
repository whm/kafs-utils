#!/usr/bin/python3
#
# Emit python module definition.
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
# Emit python module definition.
#
###############################################################################
def emit_py_module(o):
    # We want an exception we can raise when we get a remote abort
    o.pyhdr("extern PyObject *kafs_remote_abort;\n")

    o.pysrc("\n")
    o.pysrc("/*\n")
    o.pysrc(" * The remote-abort exception.\n")
    o.pysrc(" */\n")
    o.pysrc("PyObject *kafs_remote_abort;\n")

    pkgnames = list(o.xdr.packages.keys())
    pkgnames.sort()

    for pkgname in pkgnames:
        pkg = o.xdr.packages[pkgname]
        codes = pkg.abort_codes
        if codes:
            o.pysrc("PyObject *kafs_", pkg.name, "_abort;\n")

    o.pysrc("\n")
    o.pyhdr("extern struct kafs_abort_list kafs_abort_map[", o.xdr.abort_count, "];\n")

    index = 0
    o.pysrc("struct kafs_abort_list kafs_abort_map[", o.xdr.abort_count, "] = {\n")
    abort_ids = list(o.xdr.abort_ids.keys())
    abort_ids.sort()
    for aid in abort_ids:
        abort = o.xdr.abort_ids[aid]
        o.pysrc("\t{ .id = ", abort.name)
        #if abort.msg:
        #    o.pysrc(", .msg = \"", abort.msg, "\"")
        o.pysrc(" }, /* ", abort.u32, " */\n")
        abort.index = index
        index += 1

    o.pysrc("};\n\n")

    # Emit python structure wrapper static method table
    o.pysrc("\n")
    o.pysrc("/*\n")
    o.pysrc(" * The static methods.\n")
    o.pysrc(" */\n")
    o.pysrc("static PyMethodDef module_methods[] = {\n")

    o.pysrc("\t{\"rx_new_connection\", (PyCFunction)kafs_py_rx_new_connection, METH_VARARGS, \"\" },\n")
    o.pysrc("\t{\"afs_string_to_key\", (PyCFunction)kafs_py_string_to_key, METH_VARARGS, \"\" },\n")

    for pyf in o.xdr.py_func_defs:
        o.pysrc("\t{\"", pyf.name, "\", (PyCFunction)", pyf.c_func, ", METH_VARARGS,")
        o.pysrc(" \"", pyf.doc, "\" },\n")

    o.pysrc("\t{}\n")
    o.pysrc("};\n")

    # Emit python structure wrapper loader
    o.pysrc("\n")

    o.pysrc("static PyModuleDef kafs_module = {\n")
    o.pysrc("\t.m_base = PyModuleDef_HEAD_INIT,\n")
    o.pysrc("\t.m_name = \"kafs\",\n")
    o.pysrc("\t.m_doc = \"AFS stuff.\",\n")
    o.pysrc("\t.m_size = -1,\n")
    o.pysrc("\t.m_methods = module_methods,\n")
    o.pysrc("};\n")

    o.pyhdr("\n")
    o.pyhdr("extern PyObject *pykafs_load_wrappers(void);\n")

    o.pysrc("\n")
    o.pysrc("PyObject *pykafs_load_wrappers(void)\n")
    o.pysrc("{\n")
    o.pysrc("\tPyObject *m;\n")

    # Load types
    if o.xdr.py_type_defs:
        o.pysrc("\tif (")
        o.pysrc("PyType_Ready(&py_rx_connectionType) < 0 ||\n\t    ")
        o.pysrc("PyType_Ready(&py_rx_split_infoType) < 0")
        for pyt in o.xdr.py_type_defs:
            o.pysrc(" ||\n\t    ")
            o.pysrc("PyType_Ready(&", pyt.c_type, ") < 0")
        o.pysrc(")\n")
        o.pysrc("\t\treturn NULL;\n")


    o.pysrc("\n")
    o.pysrc("\tm = PyModule_Create(&kafs_module);\n")
    o.pysrc("\tif (!m)\n")
    o.pysrc("\t\treturn NULL;\n")

    if o.xdr.constants:
        o.pysrc("\n")
        con_names = list(o.xdr.constants.keys())
        con_names.sort()
        for c in con_names:
            o.pysrc("\tPyModule_AddIntConstant(m, \"", c, "\", ", c, ");\n")

    if o.xdr.py_type_defs:
        o.pysrc("\n")
        for pyt in o.xdr.py_type_defs:
            o.pysrc("\tPy_INCREF(&", pyt.c_type, ");\n")
            o.pysrc("\tPyModule_AddObject(m, \"", pyt.name, "\", (PyObject *)&", pyt.c_type, ");\n")

    # Emit a base remote abort class that all others can be subclassed off
    o.pysrc("\n")
    o.pysrc("\tkafs_remote_abort = PyErr_NewException(\"kafs.RemoteAbort\", NULL, NULL);\n")
    o.pysrc("\tif (!kafs_remote_abort)\n")
    o.pysrc("\t\treturn NULL;\n")
    o.pysrc("\tPy_INCREF(kafs_remote_abort);\n")
    o.pysrc("\tPyModule_AddObject(m, \"RemoteAbort\", kafs_remote_abort);\n")

    for pkgname in pkgnames:
        pkg = o.xdr.packages[pkgname]
        abort_codes = pkg.abort_codes
        if not abort_codes:
            continue

        pkg_abort = pkg.name + "Abort"
        pkg_sym = "kafs_" + pkg.name + "_abort"

        o.pysrc("\n")
        o.pysrc("\t", pkg_sym, " = PyErr_NewException(\"kafs.", pkg_abort, "\", kafs_remote_abort, NULL);\n")
        o.pysrc("\tif (!", pkg_sym, ")\n")
        o.pysrc("\t\treturn NULL;\n")
        o.pysrc("\tPy_INCREF(", pkg_sym, ");\n")
        o.pysrc("\tPyModule_AddObject(m, \"", pkg_abort, "\", ", pkg_sym, ");\n")

        def get_constant_value(abort):
            return abort.u32
        abort_codes.sort(key=get_constant_value)

        for abort in abort_codes:
            abort_name = "Abort" + abort.name
            abort_var = "kafs_abort_map[" + str(abort.index) + "].obj"

            o.pysrc("\n")
            o.pysrc("\t", abort_var, " = PyErr_NewException(\"kafs.", abort_name, "\", ", pkg_sym, ", NULL);\n")
            o.pysrc("\tif (!", abort_var, ")\n")
            o.pysrc("\t\treturn NULL;\n")
            o.pysrc("\tPy_INCREF(", abort_var, ");\n")
            o.pysrc("\tPyModule_AddObject(m, \"", abort_name, "\", ", abort_var, ");\n")

    o.pysrc("\n")
    o.pysrc("\treturn m;\n")
    o.pysrc("}\n")
