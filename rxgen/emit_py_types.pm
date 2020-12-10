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
# Emit python type wrapper declarations
#
###############################################################################
sub emit_py_type_wrapper_decls($) {
    my ($s) = @_;

    print PYOUT "static PyTypeObject py_", $s->{type}, "Type;\n";
}

###############################################################################
#
# Emit python type wrappers for C structs.
#
###############################################################################
sub emit_py_type_wrapper($) {
    my ($struct) = @_;

    push @py_type_defs, {
	name	=> $struct->{type},
	c_type	=> "py_" . $struct->{type} . "Type",
    };

    # Divide the struct members into single ints, single structs, char arrays
    # (strings) and other arrays
    my @single_ints = ();
    my @single_structs = ();
    my @char_arrays = ();
    my @arrays = ();
    foreach my $m (@{$struct->{members}}) {
	if ($m->{class} eq "array" && $m->{elem}->{type} eq "char") {
	    push @char_arrays, $m;
	} elsif ($m->{class} eq "basic") {
	    push @single_ints, $m;
	} elsif ($m->{class} eq "struct") {
	    push @single_structs, $m;
	} elsif ($m->{class} eq "array") {
	    push @arrays, $m;
	} else {
	    die $m->{where}, ": Unsupported struct member type";
	}
    }

    # Write a python wrapper struct
    #
    # We have a copy of the raw struct and we also have caches for python
    # objects for non-integer, non-array bits of the struct.  We populate the
    # caches when these bits are called for and then fold their contents back
    # into the raw struct when we're about to marshal it.
    #
    print PYHDR "\n";
    print PYHDR "struct py_", $struct->{type}, " {\n";
    print PYHDR "\tPyObject_HEAD\n";
    print PYHDR "\tstruct ", $struct->{type}, " x;\n";
    if ($#single_structs + $#arrays > -2) {
	print PYHDR "\tstruct {\n";
	foreach my $m (@single_structs, @arrays) {
	    print PYHDR "\t\tPyObject *", $m->{name}, ";\n";
	}
	print PYHDR "\t} c;\n";
    }
    print PYHDR "};\n";

    # We need to have a new function if the object is to be allocatable by the
    # Python interpreter
    print PYOUT "\n";
    print PYOUT "static PyObject *\n";
    print PYOUT "py_", $struct->{type}, "_new(PyTypeObject *subtype, PyObject *args, PyObject *kwds)\n";
    print PYOUT "{\n";
    print PYOUT "\treturn subtype->tp_alloc(subtype, 1);\n;";
    print PYOUT "}\n";

    # We have to have a deallocation function
    print PYOUT "\n";
    print PYOUT "static void\n";
    print PYOUT "py_", $struct->{type}, "_dealloc(struct py_", $struct->{type}, " *self)\n";
    print PYOUT "{\n";
    foreach my $m (@single_structs, @arrays) {
	print PYOUT "\tPy_XDECREF(self->c.", $m->{name}, ");\n";
    }
    print PYOUT "\tPy_TYPE(self)->tp_free((PyObject *)self);\n";
    print PYOUT "}\n";

    # Any integer non-array elements are made directly accessible to the Python
    # interpreter
    if (@single_ints) {
	print PYOUT "\n";
	print PYOUT "static PyMemberDef py_", $struct->{type}, "_members[] = {\n";
	foreach my $m (@single_ints) {
	    print PYOUT "\t{ \"", $m->{name}, "\", ";
	    if ($m->{type} eq "char") {		 print PYOUT "T_CHAR";
	    } elsif ($m->{type} eq "int8_t") {	 print PYOUT "T_BYTE";
	    } elsif ($m->{type} eq "int16_t") {	 print PYOUT "T_SHORT";
	    } elsif ($m->{type} eq "int32_t") {	 print PYOUT "T_INT";
	    } elsif ($m->{type} eq "int64_t") {	 print PYOUT "T_LONGLONG";
	    } elsif ($m->{type} eq "uint8_t") {	 print PYOUT "T_UBYTE";
	    } elsif ($m->{type} eq "uint16_t") { print PYOUT "T_USHORT";
	    } elsif ($m->{type} eq "uint32_t") { print PYOUT "T_UINT";
	    } elsif ($m->{type} eq "uint64_t") { print PYOUT "T_ULONGLONG";
	    } else {
		die $m->{where}, ": Unsupported type \"", $m->{type}, "\"";
	    }
	    print PYOUT ", offsetof(struct py_", $struct->{type}, ", x.", $m->{name}, "), 0, \"\"},\n";
	}
	print PYOUT "\t{}\n";
	print PYOUT "};\n";
    }

    # Non-single integer elements need to be turned into their respective
    # Python types and returned.

    # Array elements have to be accessed through ->tp_[sg]etattro() as
    # tuples (int[]/uint[]/struct[]) or strings (char[])
    if ($#single_structs + $#arrays + $#char_arrays > -3) {
	# The attribute get function
	print PYOUT "\n";
	print PYOUT "static PyObject *\n";
	print PYOUT "py_", $struct->{type}, "_getattro(PyObject *_self, PyObject *name)\n";
	print PYOUT "{\n";
	print PYOUT "\tstruct py_", $struct->{type}, " *self = (struct py_", $struct->{type}, " *)_self;\n";
	print PYOUT "\n";
	print PYOUT "\tif (PyUnicode_Check(name)) {\n";

	foreach my $m (@char_arrays, @single_structs, @arrays) {
	    print PYOUT "\t\tif (PyUnicode_CompareWithASCIIString(name, \"", $m->{name}, "\") == 0)\n";
	    if ($m->{class} eq "struct") {
		print PYOUT "\t\t\treturn py_rxgen_get_struct(&self->x.", $m->{name}, ",\n";
		print PYOUT "\t\t\t\t\t\t   &self->c.", $m->{name}, ",\n";
		print PYOUT "\t\t\t\t\t\t   py_data_to_", $m->{type}, ");\n";
	    } elsif ($m->{class} ne "array") {
		die $m->{where}, ": Unsupported type class \"", $m->{class}, "\"";
	    } elsif ($m->{elem}->{class} eq "struct") {
		print PYOUT "\t\t\treturn py_rxgen_get_structs(&self->x.", $m->{name}, ", ", $m->{dim}, ",\n";
		print PYOUT "\t\t\t\t\t\t    sizeof(struct ", $m->{elem}->{type}, "),\n";
		print PYOUT "\t\t\t\t\t\t    &self->c.", $m->{name}, ",\n";
		print PYOUT "\t\t\t\t\t\t    py_data_to_", $m->{elem}->{type}, ");\n";
	    } elsif ($m->{elem}->{class} ne "basic") {
		die $m->{where}, ": Unsupported array type class \"", $m->{elem}->{class}, "\"";
	    } elsif ($m->{elem}->{type} eq "char") {
		print PYOUT "\t\t\treturn py_rxgen_get_string(&self->x.", $m->{name}, ", ", $m->{dim}, ");\n";
	    } elsif ($m->{elem}->{type} eq "uint8_t") {
		print PYOUT "\t\t\treturn py_rxgen_get_uint8(&self->x.", $m->{name}, ", ", $m->{dim}, ",\n";
		print PYOUT "\t\t\t\t\t\t  &self->c.", $m->{name}, ");\n";
	    } elsif ($m->{elem}->{type} eq "uint16_t") {
		print PYOUT "\t\t\treturn py_rxgen_get_uint16(&self->x.", $m->{name}, ", ", $m->{dim}, ",\n";
		print PYOUT "\t\t\t\t\t\t   &self->c.", $m->{name}, ");\n";
	    } elsif ($m->{elem}->{type} eq "uint32_t") {
		print PYOUT "\t\t\treturn py_rxgen_get_uint32(&self->x.", $m->{name}, ", ", $m->{dim}, ",\n";
		print PYOUT "\t\t\t\t\t\t   &self->c.", $m->{name}, ");\n";
	    } elsif ($m->{elem}->{type} eq "int8_t") {
		print PYOUT "\t\t\treturn py_rxgen_get_int8(&self->x.", $m->{name}, ", ", $m->{dim}, ",\n";
		print PYOUT "\t\t\t\t\t\t  &self->c.", $m->{name}, ");\n";
	    } elsif ($m->{elem}->{type} eq "int16_t") {
		print PYOUT "\t\t\treturn py_rxgen_get_int16(&self->x.", $m->{name}, ", ", $m->{dim}, ",\n";
		print PYOUT "\t\t\t\t\t\t   &self->c.", $m->{name}, ");\n";
	    } elsif ($m->{elem}->{type} eq "int32_t") {
		print PYOUT "\t\t\treturn py_rxgen_get_int32(&self->x.", $m->{name}, ", ", $m->{dim}, ",\n";
		print PYOUT "\t\t\t\t\t\t   &self->c.", $m->{name}, ");\n";
	    } else {
		die $m->{where}, ": Unsupported array type \"", $m->{elem}->{type}, "\"";
	    }
	}

	print PYOUT "\t}\n";
	print PYOUT "\n";
	print PYOUT "\treturn PyObject_GenericGetAttr(_self, name);\n";
	print PYOUT "}\n";
	print PYOUT "\n";

	# The attribute set function
	print PYOUT "static int\n";
	print PYOUT "py_", $struct->{type}, "_setattro(PyObject *_self, PyObject *name, PyObject *val)\n";
	print PYOUT "{\n";
	print PYOUT "\tstruct py_", $struct->{type}, " *self = (struct py_", $struct->{type}, " *)_self;\n";
	print PYOUT "\n";
	print PYOUT "\tif (PyUnicode_Check(name)) {\n";

	foreach my $m (@char_arrays, @single_structs, @arrays) {
	    print PYOUT "\t\tif (PyUnicode_CompareWithASCIIString(name, \"", $m->{name}, "\") == 0)\n";
	    if ($m->{class} eq "struct") {
		print PYOUT "\t\t\treturn py_rxgen_set_struct(&self->c.", $m->{name}, ",\n";
		print PYOUT "\t\t\t\t\t\t   &py_", $m->{type}, "Type, val);\n";
	    } elsif ($m->{class} ne "array") {
		die $m->{where}, ": Unsupported type class \"", $m->{class}, "\"";
	    } elsif ($m->{elem}->{type} eq "char") {
		print PYOUT "\t\t\treturn py_rxgen_set_string(&self->x.", $m->{name}, ", ", $m->{dim}, ", val);\n";
	    } elsif ($m->{elem}->{class} eq "basic" ||
		     $m->{elem}->{class} eq "struct") {
		print PYOUT "\t\t\treturn py_rxgen_set_array(", $m->{dim}, ", &self->c.", $m->{name}, ", val);\n";
	    } else {
		die $m->{where}, ": Unsupported array type \"", $m->{elem}->{type}, "\"";
	    }
	}

	print PYOUT "\t}\n";
	print PYOUT "\n";
	print PYOUT "\treturn PyObject_GenericSetAttr(_self, name, val);\n";
	print PYOUT "}\n";
	print PYOUT "\n";
    }

    # Emit the Python type definition
    print PYOUT "static PyTypeObject py_", $struct->{type}, "Type = {\n";
    print PYOUT "\tPyVarObject_HEAD_INIT(NULL, 0)\n";
    print PYOUT "\t\"kafs.", $struct->{type}, "\",\t\t/*tp_name*/\n";
    print PYOUT "\tsizeof(struct py_", $struct->{type}, "),\t/*tp_basicsize*/\n";
    print PYOUT "\t0,\t\t\t\t/*tp_itemsize*/\n";
    print PYOUT "\t(destructor)py_", $struct->{type}, "_dealloc, /*tp_dealloc*/\n";
    print PYOUT "\t0,\t\t\t\t/*tp_print*/\n";
    print PYOUT "\t0,\t\t\t\t/*tp_getattr*/\n";
    print PYOUT "\t0,\t\t\t\t/*tp_setattr*/\n";
    print PYOUT "\t0,\t\t\t\t/*tp_compare*/\n";
    print PYOUT "\t0,\t\t\t\t/*tp_repr*/\n";
    print PYOUT "\t0,\t\t\t\t/*tp_as_number*/\n";
    print PYOUT "\t0,\t\t\t\t/*tp_as_sequence*/\n";
    print PYOUT "\t0,\t\t\t\t/*tp_as_mapping*/\n";
    print PYOUT "\t0,\t\t\t\t/*tp_hash */\n";
    print PYOUT "\t0,\t\t\t\t/*tp_call*/\n";
    print PYOUT "\t0,\t\t\t\t/*tp_str*/\n";
    if ($#single_structs + $#arrays + $#char_arrays > -3) {
	print PYOUT "\tpy_", $struct->{type}, "_getattro,\n";
	print PYOUT "\tpy_", $struct->{type}, "_setattro,\n";
    } else {
	print PYOUT "\t0,\t\t\t\t/*tp_getattro*/\n";
	print PYOUT "\t0,\t\t\t\t/*tp_setattro*/\n";
    }
    print PYOUT "\t0,\t\t\t\t/*tp_as_buffer*/\n";
    print PYOUT "\tPy_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE, /*tp_flags*/\n";
    if (@comments) {
	print PYOUT "\t";
	foreach my $c (@comments) {
	    $c =~ s/\s+$//;
	    $c =~ s/^\s+//;
	    next if ($c eq "/*" || $c eq "*/");
	    $c =~ s/^[*] //;
	    $c =~ s/^[*]$//;
	    print PYOUT "\n\t\t\"", $c, "\\n\"";
	}
	print PYOUT ",\n";
    } else {
	print PYOUT "\t\"\",\t\t\t/* tp_doc */\n";
    }
    print PYOUT "\t0,\t\t\t\t/* tp_traverse */\n";
    print PYOUT "\t0,\t\t\t\t/* tp_clear */\n";
    print PYOUT "\t0,\t\t\t\t/* tp_richcompare */\n";
    print PYOUT "\t0,\t\t\t\t/* tp_weaklistoffset */\n";
    print PYOUT "\t0,\t\t\t\t/* tp_iter */\n";
    print PYOUT "\t0,\t\t\t\t/* tp_iternext */\n";
    print PYOUT "\t0,\t\t\t\t/* tp_methods */\n";
    if (@single_ints) {
	print PYOUT "\tpy_", $struct->{type}, "_members,\n";
    } else {
	print PYOUT "\t0,\t\t\t/* tp_members */\n";
    }
    print PYOUT "\t0,\t\t\t\t/* tp_getset */\n";
    print PYOUT "\t0,\t\t\t\t/* tp_base */\n";
    print PYOUT "\t0,\t\t\t\t/* tp_dict */\n";
    print PYOUT "\t0,\t\t\t\t/* tp_descr_get */\n";
    print PYOUT "\t0,\t\t\t\t/* tp_descr_set */\n";
    print PYOUT "\t0,\t\t\t\t/* tp_dictoffset */\n";
    print PYOUT "\t0,\t\t\t\t/* tp_init */\n";
    print PYOUT "\t0,\t\t\t\t/* tp_alloc */\n";
    print PYOUT "\tpy_", $struct->{type}, "_new,\n";
    print PYOUT "};\n";

    # Emit a function to allocate such a type
    print PYHDR "extern PyObject *kafs_new_py_", $struct->{type}, "(PyObject *, PyObject *);\n";

    print PYOUT "\n";
    print PYOUT "PyObject *\n";
    print PYOUT "kafs_new_py_", $struct->{type}, "(PyObject *_self, PyObject *args)\n";
    print PYOUT "{\n";
    print PYOUT "\tPyObject *obj = _PyObject_New(&py_", $struct->{type}, "Type);\n";
    print PYOUT "\tstruct py_", $struct->{type}, " *self = (struct py_", $struct->{type}, " *)obj;\n";
    print PYOUT "\tif (!obj)\n";
    print PYOUT "\t\treturn PyExc_MemoryError;\n";
    print PYOUT "\tmemset(&self->x, 0, sizeof(self->x));\n";
    if ($#single_structs + $#arrays > -2) {
	print PYOUT "\tmemset(&self->c, 0, sizeof(self->c));\n";
    }
    print PYOUT "\treturn obj;\n";
    print PYOUT "}\n";

    # Emit a function to create an object of this type from raw data
    print PYHDR "extern PyObject *py_data_to_", $struct->{type}, "(const void *);\n";

    print PYOUT "\n";
    print PYOUT "PyObject *py_data_to_", $struct->{type}, "(const void *data)\n";
    print PYOUT "{\n";
    print PYOUT "\tPyObject *obj = _PyObject_New(&py_", $struct->{type}, "Type);\n";
    print PYOUT "\tstruct py_", $struct->{type}, " *self = (struct py_", $struct->{type}, " *)obj;\n";
    print PYOUT "\tif (!obj)\n";
    print PYOUT "\t\treturn PyExc_MemoryError;\n";
    print PYOUT "\tmemcpy(&self->x, data, sizeof(self->x));\n";
    if ($#single_structs + $#arrays > -2) {
	print PYOUT "\tmemset(&self->c, 0, sizeof(self->c));\n";
    }
    print PYOUT "\treturn obj;\n";
    print PYOUT "}\n";

    # Emit a function to unmarshal on object of this type.
    print PYOUT "\n";
    print PYOUT "PyObject *py_decode_", $struct->{type}, "(struct rx_call *call)\n";
    print PYOUT "{\n";
    print PYOUT "\tPyObject *obj = _PyObject_New(&py_", $struct->{type}, "Type);\n";
    print PYOUT "\tstruct py_", $struct->{type}, " *self = (struct py_", $struct->{type}, " *)obj;\n";
    print PYOUT "\tif (!obj)\n";
    print PYOUT "\t\treturn PyExc_MemoryError;\n";
    print PYOUT "\trxgen_decode_", $struct->{type}, "(call, &self->x);\n";
    if ($#single_structs + $#arrays > -2) {
	print PYOUT "\tmemset(&self->c, 0, sizeof(self->c));\n";
    }
    print PYOUT "\treturn obj;\n";
    print PYOUT "}\n";

    # Emit a function to premarshal such a type.  This checks the Python object
    # type and folds the contents of the cached Python objects into their raw
    # fields.
    #
    print PYHDR "extern int py_premarshal_", $struct->{type}, "(PyObject *);\n";

    print PYOUT "\n";
    print PYOUT "int py_premarshal_", $struct->{type}, "(PyObject *_self)\n";
    print PYOUT "{\n";
    print PYOUT "\tstruct py_", $struct->{type}, " *self = (struct py_", $struct->{type}, " *)_self;\n";

    # Check that the type we've been given is the right one
    print PYOUT "\n";
    print PYOUT "\tif (!PyObject_TypeCheck(self, &py_", $struct->{type}, "Type)) {\n";
    print PYOUT "\t\tPyErr_Format(PyExc_TypeError, \"Expected object of type ", $struct->{type}, "\");\n";
    print PYOUT "\t\treturn -1;\n";
    print PYOUT "\t}\n";

    if ($#single_structs + $#arrays > -2) {
	print PYOUT "\n";
	my $first = 1;
	foreach my $m (@single_structs, @arrays) {
	    if ($first) {
		print PYOUT "\tif (";
		$first = 0;
	    } else {
		print PYOUT " ||\n";
		print PYOUT "\t    ";
	    }

	    if ($m->{class} eq "struct") {
		print PYOUT "py_rxgen_premarshal_struct(&self->x.", $m->{name}, ",\n";
		print PYOUT "\t\t\t\t      sizeof(struct ", $m->{type}, "),\n";
		print PYOUT "\t\t\t\t      offsetof(struct py_", $m->{type}, ", x),\n";
		print PYOUT "\t\t\t\t      self->c.", $m->{name}, ",\n";
		print PYOUT "\t\t\t\t      py_premarshal_", $m->{type}, ") < 0";
	    } elsif ($m->{class} ne "array") {
		die $m->{where}, ": Unsupported type class \"", $m->{class}, "\"";
	    } elsif ($m->{elem}->{class} eq "struct") {
		print PYOUT "py_rxgen_premarshal_structs(&self->x.", $m->{name}, ",\n";
		print PYOUT "\t\t\t\t\t", $m->{dim}, ", sizeof(struct ", $m->{elem}->{type}, "),\n";
		print PYOUT "\t\t\t\t\toffsetof(struct py_", $m->{elem}->{type}, ", x),\n";
		print PYOUT "\t\t\t\t\tself->c.", $m->{name}, ",\n";
		print PYOUT "\t\t\t\t\tpy_premarshal_", $m->{elem}->{type}, ") < 0";
	    } elsif ($m->{elem}->{class} ne "basic") {
		die $m->{where}, ": Unsupported array type class \"", $m->{elem}->{class}, "\"";
	    } elsif ($m->{elem}->{type} eq "uint8_t") {
		print PYOUT "py_rxgen_premarshal_uint8(&self->x.", $m->{name}, ", ", $m->{dim}, ", self->c.", $m->{name}, ") < 0";
	    } elsif ($m->{elem}->{type} eq "uint16_t") {
		print PYOUT "py_rxgen_premarshal_uint16(&self->x.", $m->{name}, ", ", $m->{dim}, ", self->c.", $m->{name}, ") < 0";
	    } elsif ($m->{elem}->{type} eq "uint32_t") {
		print PYOUT "py_rxgen_premarshal_uint32(&self->x.", $m->{name}, ", ", $m->{dim}, ", self->c.", $m->{name}, ") < 0";
	    } elsif ($m->{elem}->{type} eq "int8_t") {
		print PYOUT "py_rxgen_premarshal_int8(&self->x.", $m->{name}, ", ", $m->{dim}, ", self->c.", $m->{name}, ") < 0";
	    } elsif ($m->{elem}->{type} eq "int16_t") {
		print PYOUT "py_rxgen_premarshal_int16(&self->x.", $m->{name}, ", ", $m->{dim}, ", self->c.", $m->{name}, ") < 0";
	    } elsif ($m->{elem}->{type} eq "int32_t") {
		print PYOUT "py_rxgen_premarshal_int32(&self->x.", $m->{name}, ", ", $m->{dim}, ", self->c.", $m->{name}, ") < 0";
	    } else {
		die $m->{where}, ": Unsupported array type \"", $m->{elem}->{type}, "\"";
	    }
	}

	print PYOUT ")\n";
	print PYOUT "\t\treturn -1;\n";
    }

    print PYOUT "\treturn 0;\n";
    print PYOUT "}\n";
}

1;
