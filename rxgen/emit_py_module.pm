#
# Copyright (C) 2014 Red Hat, Inc. All Rights Reserved.
# Written by David Howells (dhowells@redhat.com)
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public Licence
# as published by the Free Software Foundation; either version
# 2 of the Licence, or (at your option) any later version.
#

###############################################################################
#
# Emit python module definition.
#
###############################################################################
sub emit_py_module() {
    # We want an exception we can raise when we get a remote abort
    print PYHDR "extern PyObject *kafs_remote_abort;\n";

    print PYOUT "\n";
    print PYOUT "/*\n";
    print PYOUT " * The remote-abort exception.\n";
    print PYOUT " */\n";
    print PYOUT "PyObject *kafs_remote_abort;\n";

    foreach $_ (sort(keys(%packages))) {
	my $pkg = $packages{$_};
	my $codes = $pkg->{abort_codes};
	next unless (@{$codes});
	print PYOUT "PyObject *kafs_", $pkg->{name}, "_abort;\n";
    }

    print PYOUT "\n";
    print PYHDR "extern struct kafs_abort_list kafs_abort_map[", $abort_count, "];\n";

    my $index = 0;
    print PYOUT "struct kafs_abort_list kafs_abort_map[", $abort_count, "] = {\n";
    foreach my $id (sort {$a <=> $b} keys(%abort_ids)) {
	my $abort = $abort_ids{$id};
	print PYOUT "\t{ .id = ", $abort->{sym};
	print PYOUT ", .msg = \"", $abort->{msg}, "\"" if ($abort->{msg});
	print PYOUT " }, /* ", $abort->{id}, " */\n";
	$abort->{index} = $index++;
    }
    print PYOUT "};\n\n";

    # Emit python structure wrapper static method table
    print PYOUT "\n";
    print PYOUT "/*\n";
    print PYOUT " * The static methods.\n";
    print PYOUT " */\n";
    print PYOUT "static PyMethodDef module_methods[] = {\n";

    print PYOUT "\t{\"rx_new_connection\", (PyCFunction)kafs_py_rx_new_connection, METH_VARARGS, \"\" },\n";
    print PYOUT "\t{\"afs_string_to_key\", (PyCFunction)kafs_py_string_to_key, METH_VARARGS, \"\" },\n";

    foreach my $def (@py_func_defs) {
	print PYOUT "\t{\"", $def->{name}, "\", (PyCFunction)", $def->{c_func}, ", METH_VARARGS,";
	print PYOUT " \"", $def->{doc}, "\" },\n";
    }

    print PYOUT "\t{}\n";
    print PYOUT "};\n";

    # Emit python structure wrapper loader
    print PYOUT "\n";

    print PYOUT "static PyModuleDef kafs_module = {\n";
    print PYOUT "\t.m_base = PyModuleDef_HEAD_INIT,\n";
    print PYOUT "\t.m_name = \"kafs\",\n";
    print PYOUT "\t.m_doc = \"AFS stuff.\",\n";
    print PYOUT "\t.m_size = -1,\n";
    print PYOUT "\t.m_methods = module_methods,\n";
    print PYOUT "};\n";

    print PYHDR "\n";
    print PYHDR "extern PyObject *pykafs_load_wrappers(void);\n";

    print PYOUT "\n";
    print PYOUT "PyObject *pykafs_load_wrappers(void)\n";
    print PYOUT "{\n";
    print PYOUT "\tPyObject *m;\n";

    # Load types
    if (@py_type_defs) {
	print PYOUT "\tif (";
	print PYOUT "PyType_Ready(&py_rx_connectionType) < 0 ||\n\t    ";
	print PYOUT "PyType_Ready(&py_rx_split_infoType) < 0";
	my $first = 0;
	foreach my $def (@py_type_defs) {
	    print PYOUT " ||\n\t    " unless ($first);
	    print PYOUT "PyType_Ready(&", $def->{c_type}, ") < 0";
	    $first = 0;
	}
	print PYOUT ")\n";
	print PYOUT "\t\treturn NULL;\n";
    }

    print PYOUT "\n";
    print PYOUT "\tm = PyModule_Create(&kafs_module);\n";
    print PYOUT "\tif (!m)\n";
    print PYOUT "\t\treturn NULL;\n";

    if (%constants) {
	print PYOUT "\n";
	foreach my $c (sort grep /^[^0-9]/, keys %constants) {
	    print PYOUT "\tPyModule_AddIntConstant(m, \"$c\", $c);\n";
	}
    }

    if (@py_type_defs) {
	print PYOUT "\n";
	foreach my $def (@py_type_defs) {
	    print PYOUT "\tPy_INCREF(&", $def->{c_type}, ");\n";
	    print PYOUT "\tPyModule_AddObject(m, \"", $def->{name}, "\", (PyObject *)&", $def->{c_type}, ");\n";
	}
    }

    # Emit a base remote abort class that all others can be subclassed off
    print PYOUT "\n";
    print PYOUT "\tkafs_remote_abort = PyErr_NewException(\"kafs.RemoteAbort\", NULL, NULL);\n";
    print PYOUT "\tif (!kafs_remote_abort)\n";
    print PYOUT "\t\treturn NULL;\n";
    print PYOUT "\tPy_INCREF(kafs_remote_abort);\n";
    print PYOUT "\tPyModule_AddObject(m, \"RemoteAbort\", kafs_remote_abort);\n";

    foreach $_ (sort(keys(%packages))) {
	my $pkg = $packages{$_};
	my $abort_codes = $pkg->{abort_codes};
	next unless (@{$abort_codes});

	my $pkg_abort = $pkg->{name} . "Abort";
	my $pkg_sym = "kafs_" . $pkg->{name} . "_abort";

	print PYOUT "\n";
	print PYOUT "\t", $pkg_sym, " = PyErr_NewException(\"kafs.", $pkg_abort, "\", kafs_remote_abort, NULL);\n";
	print PYOUT "\tif (!", $pkg_sym, ")\n";
	print PYOUT "\t\treturn NULL;\n";
	print PYOUT "\tPy_INCREF(", $pkg_sym, ");\n";
	print PYOUT "\tPyModule_AddObject(m, \"", $pkg_abort, "\", ", $pkg_sym, ");\n";

	foreach my $abort (sort { $a->{id} <=> $b->{id}; } @{$abort_codes}) {
	    my $abort_name = "Abort" . $abort->{sym};
	    my $abort_var = "kafs_abort_map[" . $abort->{index} . "].obj";

	    print PYOUT "\n";
	    print PYOUT "\t", $abort_var, " = PyErr_NewException(\"kafs.", $abort_name, "\", ", $pkg_sym, ", NULL);\n";
	    print PYOUT "\tif (!", $abort_var, ")\n";
	    print PYOUT "\t\treturn NULL;\n";
	    print PYOUT "\tPy_INCREF(", $abort_var, ");\n";
	    print PYOUT "\tPyModule_AddObject(m, \"", $abort_name, "\", ", $abort_var, ");\n";
	}
    }

    print PYOUT "\n";
    print PYOUT "\treturn m;\n";
    print PYOUT "}\n";
}

1;
