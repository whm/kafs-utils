#
# Copyright (C) 2014 Red Hat, Inc. All Rights Reserved.
# Written by David Howells (dhowells@redhat.com)
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public Licence
# as published by the Free Software Foundation; either version
# 2 of the Licence, or (at your option) any later version.
#

my %bulk_get_helpers = ();
my %bulk_set_helpers = ();

###############################################################################
#
# Emit python objects to represent received parameter sets and received
# response sets for RPC calls.
#
###############################################################################
sub emit_py_func_param_object($$) {
    my ($func, $set) = @_;

    my $struct_req = "py_" . $func->{name}. "_". $set;
    my @basic = ();
    my @complex = ();
    my $params = ();
    my $division = "";

    push @py_type_defs, {
	name	=> $func->{name} . "_" . $set,
	c_type	=> $struct_req . "Type",
    };

    if ($set eq "request") {
	$params = $func->{request};
	$division = "calls";
    } else {
	$params = $func->{response};
	$division = "responses";
    }

    # Define a C structure to hold the python object header and the data.
    print PYHDR "\n";
    print PYHDR "struct ", $struct_req, " {\n";
    print PYHDR "\tstruct py_rx_", $set, " common;\n";
    if (@{$params}) {
	my $have_opaque = 0;
	print PYHDR "\tstruct {\n";
	foreach my $p (@{$params}) {
	    if ($p->{class} eq "basic") {
		push @basic, $p;
		print PYHDR "\t\t", $p->{type}, "\t", $p->{name}, ";\n";
	    } else {
		push @complex, $p;
		print PYHDR "\t\tPyObject\t*", $p->{name}, ";\n";
	    }
	    $have_opaque = 1 if ($p->{class} eq "blob" && $p->{elem}->{class} eq "opaque");
	}
	print PYHDR "\t} x;\n";
	print PYHDR "\tPy_buffer dec_buf;\n" if ($have_opaque);
    }
    print PYHDR "};\n";

    # We need to have a new function if the object is to be allocatable by the
    # Python interpreter
    print PYOUT "\n";
    print PYOUT "static PyObject *\n";
    print PYOUT $struct_req, "_new(PyTypeObject *subtype, PyObject *args, PyObject *kwds)\n";
    print PYOUT "{\n";
    print PYOUT "\tPyObject *obj;\n";
    print PYOUT "\n";
    print PYOUT "\tobj = subtype->tp_alloc(subtype, 1);\n";
    if (@{$params}) {
	print PYOUT "\tif (obj) {\n";
	print PYOUT "\t\tstruct ", $struct_req, " *self = (struct ", $struct_req, " *)obj;\n";
	print PYOUT "\t\tmemset(&self->x, 0, sizeof(self->x));\n";
	print PYOUT "\t}\n";
    }
    print PYOUT "\treturn obj;\n";
    print PYOUT "}\n";

    # We have to have a deallocation function
    print PYOUT "\n";
    print PYOUT "static void ", $struct_req, "_dealloc(struct ", $struct_req, " *self)\n";
    print PYOUT "{\n";
    foreach my $p (@complex) {
	print PYOUT "\tPy_XDECREF(self->x.", $p->{name}, ");\n";
    }
    print PYOUT "\tPy_TYPE(self)->tp_free((PyObject *)self);\n";
    print PYOUT "}\n";

    # All elements are made directly accessible to the Python interpreter,
    # either as integer types or as object types.
    if (@{$params}) {
	print PYOUT "\n";
	print PYOUT "static PyMemberDef ", $struct_req, "_members[] = {\n";
	foreach my $p (@{$params}) {
	    print PYOUT "\t{ \"", $p->{name}, "\", ";
	    if ($p->{class} eq "blob") {		print PYOUT "T_OBJECT_EX";
	    } elsif ($p->{class} eq "bulk") {		print PYOUT "T_OBJECT_EX";
	    } elsif ($p->{type} eq "char"    ) {	print PYOUT "T_CHAR";
	    } elsif ($p->{type} eq "int8_t"  ) {	print PYOUT "T_BYTE";
	    } elsif ($p->{type} eq "int16_t" ) {	print PYOUT "T_SHORT";
	    } elsif ($p->{type} eq "int32_t" ) {	print PYOUT "T_INT";
	    } elsif ($p->{type} eq "int64_t" ) {	print PYOUT "T_LONGLONG";
	    } elsif ($p->{type} eq "uint8_t" ) {	print PYOUT "T_UBYTE";
	    } elsif ($p->{type} eq "uint16_t") {	print PYOUT "T_USHORT";
	    } elsif ($p->{type} eq "uint32_t") {	print PYOUT "T_UINT";
	    } elsif ($p->{type} eq "uint64_t") {	print PYOUT "T_ULONGLONG";
	    } else {
		print PYOUT "T_OBJECT_EX";
	    }
	    print PYOUT ", offsetof(struct ", $struct_req, ", x.", $p->{name}, "), 0, \"\"},\n";
	}
	print PYOUT "\t{}\n";
	print PYOUT "};\n";
    }

    # Emit the Python type definition
    print PYOUT "\n";
    print PYOUT "static PyTypeObject ", $struct_req, "Type = {\n";
    print PYOUT "\tPyVarObject_HEAD_INIT(NULL, 0)\n";
    print PYOUT "\t\"kafs.", $func->{name}, "_", $set, "\",\t\t/*tp_name*/\n";
    print PYOUT "\tsizeof(struct ", $struct_req, "),\t/*tp_basicsize*/\n";
    print PYOUT "\t0,\t\t\t\t/*tp_itemsize*/\n";
    print PYOUT "\t(destructor)", $struct_req, "_dealloc, /*tp_dealloc*/\n";
    print PYOUT "\t0,\t\t\t\t/*tp_print*/\n";
    print PYOUT "\t0,\t\t\t\t/*tp_getattr*/\n";
    print PYOUT "\t0,\t\t\t\t/*tp_setattr*/\n";
    print PYOUT "\t0,\t\t\t\t/*tp_compare*/\n";
    print PYOUT "\t0,\t\t\t\t/*tp_repr*/\n";
    print PYOUT "\t0,\t\t\t\t/*tp_as_number*/\n";
    print PYOUT "\t0,\t\t\t\t/*tp_as_sequence*/\n";
    print PYOUT "\t0,\t\t\t\t/*tp_as_mapping*/\n";
    print PYOUT "\t0,\t\t\t\t/*tp_hash */\n";
    print PYOUT "\t0,\t\t\t\t/*tp_call */\n";
    print PYOUT "\t0,\t\t\t\t/*tp_str*/\n";
    print PYOUT "\t0,\t\t\t\t/*tp_getattro*/\n";
    print PYOUT "\t0,\t\t\t\t/*tp_setattro*/\n";
    print PYOUT "\t0,\t\t\t\t/*tp_as_buffer*/\n";
    print PYOUT "\tPy_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE, /*tp_flags*/\n";
    print PYOUT "\t\"\",\t\t\t\t/* tp_doc */\n";
    print PYOUT "\t0,\t\t\t\t/* tp_traverse */\n";
    print PYOUT "\t0,\t\t\t\t/* tp_clear */\n";
    print PYOUT "\t0,\t\t\t\t/* tp_richcompare */\n";
    print PYOUT "\t0,\t\t\t\t/* tp_weaklistoffset */\n";
    print PYOUT "\t0,\t\t\t\t/* tp_iter */\n";
    print PYOUT "\t0,\t\t\t\t/* tp_iternext */\n";
    print PYOUT "\t0,\t\t\t\t/* tp_methods */\n";
    if (@{$params}) {
	print PYOUT "\t", $struct_req, "_members,\n";
    } else {
	print PYOUT "\t0,\t\t\t\t/* tp_members */\n";
    }
    print PYOUT "\t0,\t\t\t\t/* tp_getset */\n";
    print PYOUT "\t0,\t\t\t\t/* tp_base */\n";
    print PYOUT "\t0,\t\t\t\t/* tp_dict */\n";
    print PYOUT "\t0,\t\t\t\t/* tp_descr_get */\n";
    print PYOUT "\t0,\t\t\t\t/* tp_descr_set */\n";
    print PYOUT "\t0,\t\t\t\t/* tp_dictoffset */\n";
    print PYOUT "\t0,\t\t\t\t/* tp_init */\n";
    print PYOUT "\t0,\t\t\t\t/* tp_alloc */\n";
    print PYOUT "\t", $struct_req, "_new,\n";
    print PYOUT "};\n";
}

###############################################################################
#
# Emit functions to help deal with bulk lists
#
###############################################################################
sub emit_py_func_bulk_helper($)
{
    my ($func) = @_;

    foreach my $p (@{$func->{params}}) {
	next if ($p->{class} ne "bulk");

	# Data encoding
	if (!exists $bulk_get_helpers{$p->{type}}) {
	    $bulk_get_helpers{$p->{type}} = 1;

	    print PYOUT "\n";
	    print PYOUT "static __attribute__((unused))\n";
	    print PYOUT "int py_encode_bulk_", $p->{type}, "(struct rx_call *call, PyObject *list)\n";
	    print PYOUT "{\n";
	    print PYOUT "\tPyObject *item;\n";
	    print PYOUT "\tunsigned count, i;\n";
	    print PYOUT "\n";
	    print PYOUT "\tcount = PyList_Size(list);\n";
	    print PYOUT "\trxrpc_enc(call, count);\n";
	    print PYOUT "\n";
	    print PYOUT "\tfor (i = 0; i < count; i++) {\n";
	    print PYOUT "\t\titem = PyList_GetItem(list, i);\n";
	    print PYOUT "\t\tif (!item)\n";
	    print PYOUT "\t\t\treturn -1;\n";

	    print PYOUT "\n";
	    if ($p->{elem}->{class} eq "basic") {
		print PYOUT "\t\tif (!PyLong_Check(item)) {\n";
		print PYOUT "\t\t\tPyErr_SetString(PyExc_TypeError, \"Expected list of ", $p->{type}, "\");\n";
		print PYOUT "\t\t\treturn -1;\n";
		print PYOUT "\t\t}\n";
	    } else {
		print PYOUT "\t\tif (py_premarshal_", $p->{type}, "(item))\n";
		print PYOUT "\t\t\treturn -1;\n";
	    }

	    if ($p->{elem}->{class} eq "basic") {
		if ($p->{elem}->{type} eq "int64_t") {
		    print PYOUT "\t\tuint64_t x = PyLong_AsLongLong(item);\n";
		    print PYOUT "\t\trxrpc_enc(call, x >> 32);\n";
		    print PYOUT "\t\trxrpc_enc(call, x);\n";
		} elsif ($p->{elem}->{type} eq "uint64_t") {
		    print PYOUT "\t\tuint64_t x = PyLong_AsUnsignedLongLong(item);\n";
		    print PYOUT "\t\trxrpc_enc(call, x >> 32);\n";
		    print PYOUT "\t\trxrpc_enc(call, x);\n";
		} elsif ($p->{elem}->{type} =~ /^int/) {
		    print PYOUT "\t\trxrpc_enc(call, PyLong_AsLong(item));\n";
		} elsif ($p->{elem}->{type} =~ /^uint|^char/) {
		    print PYOUT "\t\trxrpc_enc(call, PyLong_AsUnsignedLong(item));\n";
		}
	    } else {
		print PYOUT "\t\trxgen_encode_", $p->{type}, "(call, &((struct py_", $p->{type}, " *)item)->x);\n";
	    }
	    print PYOUT "\t}\n";
	    print PYOUT "\treturn 0;\n";
	    print PYOUT "}\n";
	}
    }
}

###############################################################################
#
# Emit a python wrapper function to make a simple synchronous call
#
###############################################################################
sub emit_py_func_simple_sync_call($)
{
    my ($func) = @_;

    push @py_func_defs, {
	name	=> $func->{name},
	c_func	=> "kafs_" . $func->{name},
	doc	=> "",
    };

    print PYOUT "\n";
    print PYOUT "PyObject *\n";
    print PYOUT "kafs_", $func->{name}, "(PyObject *_self, PyObject *args)\n";
    print PYOUT "{\n";

    # Local variable declarations representing parameters to send
    print PYOUT "\tstruct rx_call *call;\n";
    print PYOUT "\tstruct py_rx_connection *z_conn;\n";
    print PYOUT "\tstruct py_", $func->{name}, "_response *response;\n";
    foreach my $p (@{$func->{request}}) {
	if ($p->{class} eq "blob") {
	    print PYOUT "\tPy_buffer param_", $p->{name}, ";\n";
	} elsif ($p->{class} eq "basic") {
	    print PYOUT "\t", $p->{type}, " param_", $p->{name}, ";\n";
	} elsif ($p->{class} eq "struct") {
	    print PYOUT "\tstruct py_", $p->{type}, " *param_", $p->{name}, ";\n";
	} elsif ($p->{class} eq "bulk") {
	    print PYOUT "\tPyObject *param_", $p->{name}, ";\n"
		unless ($p->{dir} eq "OUT");
	} else {
	    die $p->{where}, ": Unsupported type \"", $p->{type}, "\"";
	}
    }

    print PYOUT "\tPyObject *split_callback, *split_info;\n" if ($func->{split});
    print PYOUT "\tPyObject *res = NULL;\n";
    print PYOUT "\tint ret;\n";

    # Make use of the tuple parser to extract the arguments and check their
    # types for us.
    print PYOUT "\n";
    print PYOUT "\tif (!PyArg_ParseTuple(args, \"O!";

    foreach my $p (@{$func->{request}}) {
	if ($p->{class} eq "bulk") {		print PYOUT "O!";
	} elsif ($p->{type} eq "int8_t") {	print PYOUT "B";
	} elsif ($p->{type} eq "int16_t") {	print PYOUT "h";
	} elsif ($p->{type} eq "int32_t") {	print PYOUT "i";
	} elsif ($p->{type} eq "int64_t") {	print PYOUT "L";
	} elsif ($p->{type} eq "uint8_t") {	print PYOUT "b";
	} elsif ($p->{type} eq "uint16_t") {	print PYOUT "H";
	} elsif ($p->{type} eq "uint32_t") {	print PYOUT "I";
	} elsif ($p->{type} eq "uint64_t") {	print PYOUT "K";
	} elsif ($p->{class} eq "struct") {	print PYOUT "O!";
	} elsif ($p->{class} eq "blob" && $p->{elem}->{class} eq "string") {
	    print PYOUT "s*";
	} elsif ($p->{class} eq "blob" && $p->{elem}->{class} eq "opaque") {
	    print PYOUT "z*";
	} else {
	    die $p->{where}, ": No py parse for param";
	}
    }

    print PYOUT "O" if ($func->{split});
    print PYOUT "\",\n";
    print PYOUT "\t\t\t      &py_rx_connectionType, &z_conn";

    foreach my $p (@{$func->{request}}) {
	print PYOUT ",\n";
	print PYOUT "\t\t\t      ";
	if ($p->{class} eq "basic") {
	    print PYOUT "&param_", $p->{name};
	} elsif ($p->{class} eq "struct") {
	    print PYOUT "&py_", $p->{type}, "Type, &param_", $p->{name};
	} elsif ($p->{class} eq "blob") {
	    print PYOUT "&param_", $p->{name};
	} elsif ($p->{class} eq "bulk") {
	    print PYOUT "&PyList_Type, &param_", $p->{name};
	} else {
	    die $p->{where}, ": Unsupported type \"", $p->{type}, "\"";
	}
    }
    print PYOUT ",\n\t\t\t      &split_callback" if ($func->{split});
    print PYOUT "))\n";
    print PYOUT "\t\treturn NULL;\n";

    if ($func->{split}) {
	print PYOUT "\n";
	print PYOUT "\tsplit_info = py_rxgen_split_client_prepare();\n";
	print PYOUT "\tif (!split_info)\n";
	print PYOUT "\t\treturn NULL;\n";
    }

    print PYOUT "\n";
    print PYOUT "\tcall = rxrpc_alloc_call(z_conn->x, 0);\n";
    print PYOUT "\tif (!call) {\n";
    print PYOUT "\t\tPy_XDECREF(split_info);\n" if ($func->{split});
    print PYOUT "\t\treturn PyErr_NoMemory();\n";
    print PYOUT "\t}\n";
    print PYOUT "\tcall->decoder_cleanup = py_rxgen_decoder_cleanup;\n";
    print PYOUT "\tpy_rxgen_split_client_set(call, split_callback, split_info);\n"
	if ($func->{split});

    # Marshal the arguments
    print PYOUT "\n";
    print PYOUT "\trxrpc_enc(call, ", $func->{opcode}, ");\n";
    foreach my $p (@{$func->{request}}) {
	if ($p->{class} eq "blob") {
	    my $dim = -1;
	    $dim = $p->{dim} if exists $p->{dim};
	    print PYOUT "\tif (py_enc_buffer(call, &param_", $p->{name}, ", ", $dim, ") < 0) {\n";
	    print PYOUT "\t\trxrpc_terminate_call(call, EINVAL);\n";
	    print PYOUT "\t\treturn NULL;\n";
	    print PYOUT "\t}\n";
	} elsif ($p->{class} eq "bulk") {
	    print PYOUT "\tif (py_encode_bulk_", $p->{type}, "(call, param_", $p->{name}, ") < 0)\n";
	    print PYOUT "\t\tgoto error;\n";
	} elsif ($p->{class} eq "basic" && $p->{xdr_size} == 4) {
	    print PYOUT "\trxrpc_enc(call, param_", $p->{name}, ");\n";
	} elsif ($p->{class} eq "basic" && $p->{xdr_size} == 8) {
	    print PYOUT "\trxrpc_enc(call, param_", $p->{name}, " >> 32);\n";
	    print PYOUT "\trxrpc_enc(call, param_", $p->{name}, ");\n";
	} elsif ($p->{class} eq "struct") {
	    print PYOUT "\tif (py_premarshal_", $p->{type}, "((PyObject *)param_", $p->{name}, ")) {\n";
	    print PYOUT "\t\trxrpc_terminate_call(call, EINVAL);\n";
	    print PYOUT "\t\treturn NULL;\n";
	    print PYOUT "\t}\n";
	    print PYOUT "\trxgen_encode_", $p->{type}, "(call, &param_", $p->{name}, "->x);\n";
	} else {
	    die $p->{where}, ": Unsupported type in decode";
	}
    }

    print PYOUT "\tif (rxrpc_post_enc(call) < 0)\n";
    print PYOUT "\t\tgoto error_no_res;\n";

    # Allocate a reply object
    print PYOUT "\n";
    print PYOUT "\tres = _PyObject_New(&py_", $func->{name}, "_responseType);\n";
    print PYOUT "\tresponse = (struct py_", $func->{name}, "_response *)res;\n";
    print PYOUT "\tif (!response)\n";
    print PYOUT "\t\tgoto enomem;\n";
    print PYOUT "\tmemset(&response->x, 0, sizeof(response->x));\n"
	    if (@{$func->{response}});
    print PYOUT "\tcall->decoder = py_", $func->{name}, "_decode_response;\n";
    print PYOUT "\tcall->decoder_private = response;\n";

    # Transmit the split data
    if ($func->{split}) {
	print PYOUT "\tif (py_rxgen_split_transmit(call) < 0)\n";
	print PYOUT "\t\tgoto error_no_res;\n";
    } else {
	print PYOUT "\tcall->more_send = 0;\n";

	# Make the call
	print PYOUT "\n";
	print PYOUT "\tret = rxrpc_send_data(call);\n";
	print PYOUT "\tif (ret == -1)\n";
	print PYOUT "\t\tgoto error;\n";
    }

    # Wait for the reply
    #
    # If we're dealing with a split function or are in asynchronous mode, we
    # need to return the call here.
    #
    print PYOUT "\n";
    print PYOUT "\tret = rxrpc_run_sync_call(call);\n";
    print PYOUT "\tif (ret == -1)\n";
    print PYOUT "\t\tgoto error;\n";

    # Successful return
    print PYOUT "\n";
    print PYOUT "\trxrpc_terminate_call(call, 0);\n";
    print PYOUT "\treturn res;\n";

    # Error cleanups
    print PYOUT "\n";
    print PYOUT "error:\n";
    print PYOUT "\tPy_XDECREF(res);\n";
    print PYOUT "error_no_res:\n";
    print PYOUT "\tif (errno == ENOMEM)\n";
    print PYOUT "enomem:\n";
    print PYOUT "\t\tres = PyErr_NoMemory();\n";
    print PYOUT "\telse if (errno == ECONNABORTED)\n";
    print PYOUT "\t\tres = py_rxgen_received_abort(call);\n";
    print PYOUT "\telse\n";
    print PYOUT "\t\tres = PyErr_SetFromErrno(PyExc_IOError);\n";
    print PYOUT "\trxrpc_terminate_call(call, ENOMEM);\n";
    print PYOUT "\treturn res;\n";

    # End the function
    print PYOUT "}\n";
}

###############################################################################
#
# Emit a function to decode a block into a python object in a way that can be
# used from asynchronous code.  The opcode is expected to have been removed
# from the incoming call on the server side.
#
###############################################################################
sub emit_py_func_decode($$$$)
{
    my ($func, $side, $subname, $paramlist) = @_;
    my @params = @{$paramlist};
    my $ptr;

    $ptr = "obj->";

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
    my @phases = ();
    my $phase = 0;
    my $have_bulk = 0;
    my $want_item = 0;

    if ($func->{split} && $subname eq "response") {
	$phase = {
	    type => "split",
	    size => "py_rxgen_split_receive(call)",
	    params => []
	};
	push @phases, $phase;
	$phase = 0;
	$have_bulk = 1;
    }

    foreach my $p (@params) {
	unless ($phase) {
	    $phase = { type => "flat", size => 0, params => [] };
	    push @phases, $phase;
	}

	if ($p->{class} eq "basic" ||
	    $p->{class} eq "struct"
	    ) {
	    $phase->{size} +=  $p->{xdr_size};
	    push @{$phase->{params}}, $p;
	} elsif ($p->{class} eq "blob") {
	    $have_bulk = 1;

	    # Bulk objects begin with an element count
	    $phase->{elem_count} = $phase->{size};
	    $phase->{size} +=  4;

	    my %pseudoparam = (
		class	=> "basic",
		type	=> "blob_size",
		name	=> $p->{name},
		elem	=> $p->{elem},
		where	=> $p->{where},
		xdr_size => $p->{xdr_size},
		);
	    push @{$phase->{params}}, \%pseudoparam;

	    # Create a new phase
	    $phase = {
		type => "blob",
		name => $p->{name},
		params => [ $p ],
		xdr_size => $p->{xdr_size},
	    };
	    push @phases, $phase;

	    # We don't want to be asking recvmsg() for one object at a time if
	    # they're really small.
	    $phase->{size} = $p->{xdr_size};
	    $phase = 0;
	} elsif ($p->{class} eq "bulk") {
	    $have_bulk = 1;

	    # Bulk objects begin with an element count
	    $phase->{elem_count} = $phase->{size};
	    $phase->{size} +=  4;

	    my %pseudoparam = (
		class	=> "basic",
		type	=> "bulk_size",
		name	=> $p->{name},
		elem	=> $p->{elem},
		where	=> $p->{where},
		xdr_size => $p->{xdr_size},
		);
	    push @{$phase->{params}}, \%pseudoparam;

	    # Create a new phase
	    $phase = {
		type => "bulk",
		name => $p->{name},
		params => [ $p ],
		xdr_size => $p->{xdr_size},
	    };
	    push @phases, $phase;

	    $want_item = 1;

	    # We don't want to be asking recvmsg() for one object at a time if
	    # they're really small.
	    $phase->{size} = $p->{xdr_size};
	    $phase = 0;
	} else {
	    die $p->{where}, "Reply array not supported";
	}
    }

    if ($func->{split} && $subname eq "request") {
	$phase = {
	    type => "split",
	    size => "py_rxgen_split_receive(call)",
	    params => []
	};
	push @phases, $phase;
	$phase = 0;
	$have_bulk = 1;
    }

    # Function definition and arguments
    print PYOUT "\n";
    print PYOUT "int py_", $func->{name}, "_decode_", $subname, "(struct rx_call *call)\n";
    print PYOUT "{\n";

    unless (@params || $func->{split}) {
	print PYOUT "\treturn 0;\n";
	print PYOUT "}\n";
	return;
    }

    # Local variables
    print PYOUT "\tstruct py_", $func->{name}, "_", $subname, " *obj = call->decoder_private;\n"
	if (@params);
    print PYOUT "\tPyObject *item;\n" if ($want_item);
    print PYOUT "\tunsigned phase = call->phase;\n";
    print PYOUT "\tunsigned count;\n";

    # Deal with each phase
    print PYOUT "\n";
    print PYOUT "select_phase:\n" if ($have_bulk);
    print PYOUT "\tcount = call->data_count;\n";
    #print PYOUT "\tprintf(\"-- Phase %u (%u) --\\n\", phase, count);\n";
    print PYOUT "\tswitch (phase) {\n";

    print PYOUT "\tcase 0:\n";

    my $phase_goto_label = 0;
    my $phix;
    for ($phix = 1; $phix <= $#phases + 1; $phix++) {
	print PYOUT "\n";
	print PYOUT "\t\t/* --- Phase ", $phix, " --- */\n";
	$phase = $phases[$phix - 1];
	if ($phase_goto_label == $phix) {
	    print PYOUT "\tphase_", $phix, ":\n";
	    $phase_goto_label = 0;
	}

	# Determine how big bulk objects are
	if ($phase->{type} eq "blob") {
	    my $p = $phase->{params}->[0];
	    if ($p->{elem}->{class} eq "string") {
		print PYOUT "\t\tswitch (py_dec_init_string(call, &obj->x.", $p->{name}, ")) {\n";
	    } elsif ($p->{elem}->{class} eq "opaque") {
		print PYOUT "\t\tobj->x.", $p->{name}, " = PyByteArray_FromStringAndSize(\"\", 0);\n";
		print PYOUT "\t\tif (!obj->x.", $p->{name}, ")\n";
		print PYOUT "\t\t\treturn -1;\n";
		print PYOUT "\t\tif (PyByteArray_Resize(obj->x.", $p->{name}, ", call->blob_size) == -1)\n";
		print PYOUT "\t\t\treturn -1;\n";

		print PYOUT "\t\tswitch (py_dec_init_opaque(call, obj->x.", $p->{name}, ")) {\n";
	    } else {
		die;
	    }
	    print PYOUT "\t\tcase -1: return -1;\n";
	    print PYOUT "\t\tcase  0: goto phase_", $phix + 1, ";\n";
	    print PYOUT "\t\tcase  1: break;\n";
	    print PYOUT "\t\t}\n";
	    $phase_goto_label = $phix + 1;
	} elsif ($phase->{type} eq "bulk") {
	    my $p = $phase->{params}->[0];
	    if ($p->{elem}->{class} eq "basic" ||
		$p->{elem}->{class} eq "struct") {
		print PYOUT "\t\tobj->x.", $p->{name}, " = PyList_New(call->bulk_count);\n";
		print PYOUT "\t\tif (!obj->x.", $p->{name}, ")\n";
		print PYOUT "\t\t\treturn -1;\n";
	    } else {
		die;
	    }

	    print PYOUT "\t\tif (call->bulk_count == 0)\n";
	    print PYOUT "\t\t\tgoto phase_", $phix + 1, ";\n";
	    $phase_goto_label = $phix + 1;
	    print PYOUT "\t\tcall->bulk_index = 0;\n";
	}

	# Entry point for a phase
	if ($phase->{type} eq "split") {
	    print PYOUT "\t\tif (py_rxgen_split_receive(call, 1) < 0)\n";
	    print PYOUT "\t\t\treturn -1;\n";
	    print PYOUT "\t\tif (call->need_size == 0)\n";
	    print PYOUT "\t\t\tgoto phase_", $phix + 1, ";\n";
	    $phase_goto_label = $phix + 1;
	}
	print PYOUT "\t\tcall->phase = ", $phix, ";\n";
	print PYOUT "\tcase ", $phix, ":\n";

	if ($phase->{type} ne "split") {
	    print PYOUT "\t\tcall->need_size = ", $phase->{size}, ";\n";
	    print PYOUT "\t\tif (count < call->need_size)\n";
	    print PYOUT "\t\t\treturn 1;\n";
	} else {
	    print PYOUT "\t\tif (call->need_size == UINT_MAX ? count == 0 : count < call->need_size) {\n";
	    #print PYOUT "\t\t\tprintf(\"NEED %u (phase %u)\\n\", call->need_size, phase);\n";
	    print PYOUT "\t\t\treturn 1;\n";
	    print PYOUT "\t\t}\n";
	}

	# Unmarshal the data
	print PYOUT "\n";
	foreach my $p (@{$phase->{params}}) {
	    if ($p->{type} eq "blob_size") {
		print PYOUT "\t\tcall->blob_size = rxrpc_dec(call);\n";
		next;
	    } elsif ($p->{type} eq "bulk_size") {
		print PYOUT "\t\tcall->bulk_count = rxrpc_dec(call);\n";
		next;
	    }

	    if ($p->{class} eq "bulk") {
		if ($p->{elem}->{class} eq "struct") {
		    print PYOUT "\t\titem = py_decode_", $p->{type}, "(call);\n";
		} elsif ($p->{elem}->{xdr_size} == 4 && $p->{type} =~ /^u/) {
		    print PYOUT "\t\titem = PyLong_FromUnsignedLong((", $p->{type}, ")rxrpc_dec(call));\n";
		} elsif ($p->{elem}->{xdr_size} == 4) {
		    print PYOUT "\t\titem = PyLong_FromLong((", $p->{type}, ")rxrpc_dec(call));\n";
		} elsif ($p->{elem}->{xdr_size} == 8 && $p->{type} =~ /^u/) {
		    print PYOUT "\t\tcall->bulk_u64  = (uint64_t)rxrpc_dec(call) << 32;\n";
		    print PYOUT "\t\tcall->bulk_u64 |= (uint64_t)rxrpc_dec(call);\n";
		    print PYOUT "\t\titem = PyLong_FromUnsignedLongLong(call->bulk_u64);\n";
		} elsif ($p->{elem}->{xdr_size} == 8) {
		    print PYOUT "\t\tcall->bulk_s64  = (int64_t)rxrpc_dec(call) << 32;\n";
		    print PYOUT "\t\tcall->bulk_s64 |= (int64_t)rxrpc_dec(call);\n";
		    print PYOUT "\t\titem = PyLong_FromLongLong(call->bulk_s64);\n";
		} else {
		    die;
		}

		print PYOUT "\t\tif (!item)\n";
		print PYOUT "\t\t\treturn -1;\n";
		print PYOUT "\t\tif (PyList_SetItem(obj->x.", $p->{name}, ", call->bulk_index, item) < 0)\n";
		print PYOUT "\t\t\treturn -1;\n";
		print PYOUT "\t\tcall->bulk_index++;\n";

	    } elsif ($p->{class} eq "blob") {
		if ($p->{elem}->{class} eq "string") {
		    print PYOUT "\t\tswitch (py_dec_into_string(call)) {\n";
		} else {
		    print PYOUT "\t\tswitch (py_dec_into_buffer(call)) {\n";
		}
		print PYOUT "\t\tcase -1: return -1;\n";
		print PYOUT "\t\tcase  0: break;\n";
		print PYOUT "\t\tcase  1: phase = ", $phix, "; goto select_phase;\n";
		print PYOUT "\t\t}\n";
	    } elsif ($p->{class} eq "basic" && $p->{xdr_size} == 4) {
		print PYOUT "\t\tobj->x.", $p->{name}, " = (", $p->{type}, ")rxrpc_dec(call);\n";
	    } elsif ($p->{class} eq "basic" && $p->{xdr_size} == 8) {
		print PYOUT "\t\tobj->x.", $p->{name}, " = (", $p->{type}, ")rxrpc_dec(call) << 32;\n";
		print PYOUT "\t\tobj->x.", $p->{name}, " |= (", $p->{type}, ")rxrpc_dec(call) << 32;\n";
	    } elsif ($p->{class} eq "struct") {
		print PYOUT "\t\tobj->x.", $p->{name}, " = py_decode_", $p->{type}, "(call);\n";
	    } else {
		die $p->{where}, ": Unsupported type in decode";
	    }

	    if ($p->{class} eq "blob" &&  $p->{elem}->{class} eq "string") {
		print PYOUT "\t\tif (rxrpc_post_dec(call) < 0)\n";
		print PYOUT "\t\t\treturn -1;\n";
		print PYOUT "\t\tif (call->blob_offset < call->blob_size) {\n";
		print PYOUT "\t\t\tphase = ", $phix, ";\n";
		print PYOUT "\t\t\tgoto select_phase;\n";
		print PYOUT "\t\t}\n";
	    } elsif ($p->{class} eq "bulk") {
		print PYOUT "\t\tif (rxrpc_post_dec(call) < 0)\n";
		print PYOUT "\t\t\treturn -1;\n";
		print PYOUT "\t\tif (call->bulk_index < call->bulk_count) {\n";
		print PYOUT "\t\t\tphase = ", $phix, ";\n";
		print PYOUT "\t\t\tgoto select_phase;\n";
		print PYOUT "\t\t}\n";
	    }
	}

	if ($phase->{type} eq "split") {
	    print PYOUT "\t\tswitch (py_rxgen_split_receive(call, 0)) {\n";
	    print PYOUT "\t\tcase -1: return -1;\n";
	    print PYOUT "\t\tcase  0: break;\n";
	    print PYOUT "\t\tcase  1: phase = ", $phix, "; goto select_phase;\n";
	    print PYOUT "\t\t}\n";
	    #print PYOUT "\t\tif (rxrpc_post_dec(call) < 0)\n";
	    #print PYOUT "\t\t\treturn -1;\n";
	    #print PYOUT "\t\tif (call->need_size != 0) {\n";
	    #print PYOUT "\t\t\tphase = ", $phix, ";\n";
	    #print PYOUT "\t\t\tgoto select_phase;\n";
	    #print PYOUT "\t\t}\n";
	}

	if ($phase->{type} ne "bulk" && $phase->{type} ne "blob") {
	    print PYOUT "\t\tif (rxrpc_post_dec(call) < 0)\n";
	    print PYOUT "\t\t\treturn -1;\n";
	}
    }

    print PYOUT "\n";
    print PYOUT "\t\t/* --- Phase ", $phix, " --- */\n";
    if ($phase_goto_label == $phix) {
	print PYOUT "\tphase_", $phix, ":\n";
	$phase_goto_label = 0;
    }
    print PYOUT "\t\tcall->phase = ", $phix, ";\n";
    print PYOUT "\t\tcall->need_size = 0;\n";
    print PYOUT "\tdefault:\n";
    print PYOUT "\t\treturn 0;\n";
    print PYOUT "\t}\n";

    print PYOUT "}\n";
}

1;
