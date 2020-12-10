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
# Calculate the C function prototypes
#
###############################################################################
sub emit_func_prototype($)
{
    my ($func) = @_;

    # Function prototype lists (we add commas and the closing bracket later)
    my @protos = ( "int " . $func->{name} . "(\n" );
    my @send_request_protos = ();
    my @send_response_protos = ();
    my @recv_request_protos = ();
    my @recv_response_protos = ();

    # Arguments to pass when sending a call or processing a reply
    my @send_args = ();
    my @recv_args = ();

    foreach my $p (@{$func->{params}}) {
	my @enclines = ();
	my @declines = ();

	if ($p->{class} eq "array") {
	    die $p->{where}, ": Array arg not supported";
	} elsif ($p->{class} eq "bulk") {
	    # Encode
	    if ($p->{elem}->{class} eq "struct") {
		$proto  = "int (*get__" . $p->{name} . ")(struct rx_call *call, void *token)";
	    } else {
		$proto  = "int (*get__" . $p->{name} . ")(struct rx_call *call, void *token)";
	    }
	    push @enclines, $proto;
	    push @enclines, "void *token__" . $p->{name};
	    push @enclines, "size_t nr__" . $p->{name};
	    push @args, "get__" . $p->{name};
	    push @args, "token__" . $p->{name};
	    push @args, "nr__" . $p->{name};

	    # Decode
	    if ($p->{elem}->{class} eq "struct") {
		$proto  = "int (*alloc__" . $p->{name} . ")(struct rx_call *call, void **token)";
		push @args, "alloc__" . $p->{name};
	    } else {
		$proto  = "int (*store__" . $p->{name} . ")(struct rx_call *call, void **token)";
		push @args, "store__" . $p->{name};
	    }
	    push @declines, $proto;
	    push @declines, "void *token__" . $p->{name};
	    push @declines, "size_t nr__" . $p->{name};
	    push @args, "token__" . $p->{name};
	} elsif ($p->{class} eq "blob") {
	    $proto = $p->{type} . " " . $p->{ptr} . $p->{name};
	    push @enclines, "size_t nr__" . $p->{name};
	    push @enclines, "const " . $proto;

	    push @declines, "size_t nr__" . $p->{name};
	    push @declines, "void *token__" . $p->{name};
	    push @declines, "int (*alloc__" . $p->{name} . ")(struct rx_call *call, void **token)";
	    push @args, "nr__" . $p->{name};
	    push @args, $p->{name};
	    push @args, "alloc__" . $p->{name};
	} else {
	    my $enc_const = "";
	    $enc_const = "const " if ($p->{class} ne "basic");
	    $proto  = "";
	    $proto .= "struct " if ($p->{class} eq "struct");
	    $proto .= $p->{type} . " ";
	    $proto .= $p->{ptr} if ($p->{class} ne "basic");
	    $proto .= $p->{name};
	    push @enclines, $enc_const . $proto;
	    push @declines, $proto;
	    push @args, $p->{name};
	}

	push @send_request_protos,  @enclines  unless ($p->{dir} eq "OUT");
	push @recv_request_protos,  @declines unless ($p->{dir} eq "OUT");
	push @send_response_protos, @enclines  unless ($p->{dir} eq "IN");
	push @recv_response_protos, @declines unless ($p->{dir} eq "IN");
	push @send_args, @args unless ($p->{dir} eq "OUT");
	push @recv_args, @args unless ($p->{dir} eq "IN");
    }

    print RXHDR "\n";
    print RXHDR "/*\n";
    print RXHDR " * ", $func->{name}, "\n";
    print RXHDR " */\n";

    if (@recv_request_protos) {
	print RXHDR "struct ", $func->{name}, "_request {\n";
	foreach my $p (@recv_request_protos) {
	    print RXHDR "\t$p;\n";
	}
	print RXHDR "};\n";
    }

    print RXHDR "\n";
    if (@recv_response_protos) {
	print RXHDR "struct ", $func->{name}, "_response {\n";
	foreach my $p (@recv_response_protos) {
	    print RXHDR "\t$p;\n";
	}
	print RXHDR "};\n";
    }

    # # Terminate each line with a comma, excepting the last, which we terminate
    # # with a closing bracket.
    # for (my $i = 1; $i < $#protos; $i++) {
    # 	$protos[$i] .= ",\n";
    # }
    # $protos[$#protos] .= ")";

    # for (my $i = 1; $i < $#send_protos; $i++) {
    # 	$send_protos[$i] .= ",\n";
    # }
    # $send_protos[$#send_protos] .= ")";

    # for (my $i = 1; $i < $#recv_protos; $i++) {
    # 	$recv_protos[$i] .= ",\n";
    # }
    # $recv_protos[$#recv_protos] .= ")";

    $func->{protos} = \@protos;
    $func->{send_request_protos}  = \@send_request_protos;
    $func->{recv_request_protos}  = \@recv_request_protos;
    $func->{send_response_protos} = \@send_response_protos;
    $func->{recv_response_protos} = \@recv_response_protos;
    $func->{send_args} = \@send_args;
    $func->{recv_args} = \@recv_args;
}

###############################################################################
#
# Emit a function to encode a block in a way that can be used from asynchronous
# code.
#
###############################################################################
sub emit_func_encode($$$$)
{
    my ($func, $side, $subname, $paramlist) = @_;
    my @params = @{$paramlist};
    my $ptr;

    if ($side eq "client") {
	my %op_id = (
	    class	=> "opcode",
	    type	=> "uint32_t",
	    name	=> $func->{opcode},
	    where	=> $func->{where},
	    xdr_size	=> 4,
	);
	unshift @params, \%op_id;
	$ptr = "call->req.";
    } else {
	$ptr = "call->resp.";
    }

    # We marshal the data in a number of phases.  Each phase marshals a chunk
    # of data of a certain size.  A phase's size might be dependent on a
    # variable in the previous phase.  Variable-sized bulk arrays are split
    # across multiple phases, with the length being at the end of the first
    # phase and the data in the second.
    my @phases = ();
    my $phase = 0;
    my $have_bulk = 0;

    foreach my $p (@params) {
	unless ($phase) {
	    $phase = { type => "flat", size => 0, params => [] };
	    push @phases, $phase;
	}

	if ($p->{class} eq "opcode" ||
	    $p->{class} eq "basic" ||
	    $p->{class} eq "struct"
	    ) {
	    $phase->{size} +=  $p->{xdr_size};
	    push @{$phase->{params}}, $p;
	} elsif ($p->{class} eq "blob") {
	    $have_bulk = 2;

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
		type	=> "blob",
		name	=> $p->{name},
		elem	=> $p->{elem},
		params	=> [ $p ],
		xdr_size => $p->{xdr_size},
		size	=> $p->{xdr_size},
	    };
	    push @phases, $phase;

	    $phase->{size} = 4;
	    $phase = 0;
	} elsif ($p->{class} eq "bulk") {
	    $have_bulk = 1 if ($have_bulk == 0);

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
		type	=> "bulk",
		name	=> $p->{name},
		elem	=> $p->{elem},
		params	=> [ $p ],
		xdr_size => $p->{xdr_size},
		size	=> $p->{xdr_size},
	    };
	    push @phases, $phase;

	    # We don't want to be sending one object at a time if they're
	    # really small.
	    my $n_buf = ($p->{xdr_size} < 1020) ? int(1020 / $p->{xdr_size}) : 1;
	    $n_buf *= $p->{xdr_size};
	    $phase->{size} = $p->{xdr_size};
	    $phase = 0;
	} else {
	    die $p->{where}, "Encode array arg not supported";
	}
    }

    # Function definition (data gets passed in *call)
    print RXOUT "\n";
    print RXOUT "int ", $func->{name}, "_", $subname, "(\n";
    print RXOUT "\tstruct rx_connection *z_conn,\n";
    print RXOUT "\tstruct ", $func->{name}, "_", $side, "_call *call)\n";
    print RXOUT "{\n";

    unless (@params) {
	die if ($side eq "client");
	print RXOUT "\tcall->more_send = 0;\n";
	print RXOUT "\treturn 0;\n";
	print RXOUT "}\n";
	return;
    }

    # Local variables
    print RXOUT "\tunsigned phase = call->phase;\n";

    # Deal with each phase
    print RXOUT "\n";
    print RXOUT "select_phase:\n" if ($have_bulk);
    print RXOUT "\tswitch (phase) {\n";

    print RXOUT "\tcase 0:\n";
    print RXOUT "\t\tcall->more_send = 1;\n";

    my $phase_goto_label = 0;
    my $phix;
    for ($phix = 1; $phix <= $#phases + 1; $phix++) {
	$phase = $phases[$phix - 1];
	print RXOUT "\n";
	print RXOUT "\t\t/* --- Phase ", $phix, " --- */\n";
	if ($phase_goto_label == $phix) {
	    print RXOUT "\tphase_", $phix, ":\n";
	    $phase_goto_label = 0;
	}

	# Determine how big bulk objects are
	if ($phase->{type} eq "blob") {
	    my $p = $phase->{params}->[0];
	    print RXOUT "\t\tcall->blob_size = ", $ptr, "nr__", $p->{name}, ";\n";
	    print RXOUT "\t\tif (call->blob_size == 0)\n";
	    print RXOUT "\t\t\tgoto phase_", $phix + 1, ";\n";
	    $phase_goto_label = $phix + 1;
	    print RXOUT "\t\tcall->blob_offset = 0;\n";
	} elsif ($phase->{type} eq "bulk") {
	    my $p = $phase->{params}->[0];
	    print RXOUT "\t\tcall->bulk_count = ", $ptr, "nr__", $p->{name}, ";\n";
	    print RXOUT "\t\tif (call->bulk_count == 0)\n";
	    print RXOUT "\t\t\tgoto phase_", $phix + 1, ";\n";
	    $phase_goto_label = $phix + 1;
	    print RXOUT "\t\tcall->bulk_index = 0;\n";
	}

	# Entry point for a phase
	print RXOUT "\t\tcall->phase = ", $phix, ";\n";
	print RXOUT "\tcase ", $phix, ":\n";

	# Marshal the data
	foreach my $p (@{$phase->{params}}) {
	    if ($p->{type} eq "blob_size") {
		print RXOUT "\t\trxrpc_enc(call, ", $ptr, "nr__", $p->{name}, ");\n";
		$close_phase = 0;
		next;
	    } elsif ($p->{type} eq "bulk_size") {
		print RXOUT "\t\trxrpc_enc(call, ", $ptr, "nr__", $p->{name}, ");\n";
		$close_phase = 0;
		next;
	    }

	    if ($p->{class} eq "bulk" && $p->{elem}->{class} eq "basic") {
		if ($p->{elem}->{xdr_size} == 4) {
		    print RXOUT "\t\tif (", $ptr, "get__", $p->{name}, "(call, &", $ptr, "token__", $p->{name}, ") < 0)\n";
		} else {
		    print RXOUT "\t\tif (", $ptr, "get__", $p->{name}, "(call, &", $ptr, "token__", $p->{name}, ") < 0)\n";
		}
		print RXOUT "\t\t\treturn -1;\n";

		if ($p->{elem}->{xdr_size} == 4) {
		    print RXOUT "\t\trxrpc_enc(call, call->bulk_u32);\n";
		} elsif ($p->{elem}->{xdr_size} == 8) {
		    print RXOUT "\t\trxrpc_enc(call, call->bulk_u64 >> 32)\n";
		    print RXOUT "\t\trxrpc_enc(call, (uint32_t)call->bulk_u64)\n";
		} else {
		    die;
		}
		print RXOUT "\t\tcall->bulk_index++;\n";
	    } elsif ($p->{class} eq "bulk" && $p->{elem}->{class} eq "struct") {
		print RXOUT "\t\tif (", $ptr, "get__", $p->{name}, "(call, &", $ptr, "token__", $p->{name}, ") < 0)\n";
		print RXOUT "\t\t\treturn -1;\n";
		print RXOUT "\t\trxgen_encode_", $p->{type}, "(call, call->bulk_item);\n";
		print RXOUT "\t\tcall->bulk_index++;\n";
	    } elsif ($p->{class} eq "bulk" && ($p->{elem}->{class} eq "string" ||
					       $p->{elem}->{class} eq "opaque")) {
		print RXOUT "\t\trxrpc_enc_bytes(call, ", $ptr, $p->{name}, ", call);\n";
		print RXOUT "\t\trxrpc_enc_align(call);\n";
	    } elsif ($p->{class} eq "opcode") {
		print RXOUT "\t\trxrpc_enc(call, ", $p->{name}, ");\n";
	    } elsif ($p->{class} eq "basic" && $p->{xdr_size} == 4) {
		print RXOUT "\t\trxrpc_enc(call, ", $ptr, $p->{name}, ");\n";
	    } elsif ($p->{class} eq "basic" && $p->{xdr_size} == 8) {
		print RXOUT "\t\trxrpc_enc(call, ", $ptr, $p->{name}, " >> 32);\n";
		print RXOUT "\t\trxrpc_enc(call, (uint32_t)", $ptr, $p->{name}, ");\n";
	    } elsif ($p->{class} eq "struct") {
		print RXOUT "\t\trxgen_encode_", $p->{type}, "(call, ", $ptr, $p->{name}, ");\n";
	    } else {
		die $p->{where}, ": Unsupported type in decode";
	    }

	    if ($p->{class} eq "blob") {
		print RXOUT "\t\tif (call->blob_offset < call->blob_size) {\n";
		print RXOUT "\t\t\tphase = ", $phix, ";\n";
		print RXOUT "\t\t\tgoto select_phase;\n";
		print RXOUT "\t\t}\n";
	    } elsif ($p->{class} eq "bulk") {
		print RXOUT "\t\tif (call->bulk_index < call->bulk_count) {\n";
		print RXOUT "\t\t\tphase = ", $phix, ";\n";
		print RXOUT "\t\t\tgoto select_phase;\n";
		print RXOUT "\t\t}\n";
	    }
	}
    }

    print RXOUT "\n";
    print RXOUT "\t\t/* --- Phase ", $phix, " --- */\n";
    if ($phase_goto_label == $phix) {
	print RXOUT "\tphase_", $phix, ":\n";
	$phase_goto_label = 0;
    }
    print RXOUT "\t\tcall->phase = ", $phix, ";\n";
    print RXOUT "\tcase ", $phix, ":\n";
    print RXOUT "\t\tif (rxrpc_post_enc(call) < 0)\n";
    print RXOUT "\t\t\treturn -1;\n";
    print RXOUT "\t\tcall->more_send = 0;\n";
    print RXOUT "\t\tbreak;\n";
    print RXOUT "\t}\n";

    print RXOUT "\treturn 0;\n";
    print RXOUT "}\n";
}

###############################################################################
#
# Emit a function to decode a block in a way that can be used from asynchronous
# code.  The opcode is expected to have been removed from the incoming call on
# the server side.
#
###############################################################################
sub emit_func_decode($$$$)
{
    my ($func, $side, $subname, $paramlist) = @_;
    my @params = @{$paramlist};
    my $ptr = "obj->";

    # We fetch the data in a number of phases.  Each phase receives a chunk of
    # data of a certain size.  A phase's size might be dependent on a variable
    # in the previous phase.  Variable-sized bulk arrays are split across
    # multiple phases, with the length being at the end of the first phase and
    # the data in the second.
    my @phases = ();
    my $phase = 0;
    my $have_bulk = 0;

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
		size => 4,
		xdr_size => $p->{xdr_size},
	    };
	    push @phases, $phase;
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

	    # We don't want to be asking recvmsg() for one object at a time if
	    # they're really small.
	    my $n_buf = ($p->{xdr_size} < 1020) ? int(1020 / $p->{xdr_size}) : 1;
	    $n_buf *= $p->{xdr_size};
	    $phase->{size} = $p->{xdr_size};
	    $phase = 0;
	} else {
	    die $p->{where}, "Reply array not supported";
	}
    }

    # Function definition and arguments
    print RXOUT "\n";
    print RXOUT "static int rxgen_decode_", $func->{name}, "_", $subname, "(struct rx_call *call)\n";
    print RXOUT "{\n";

    unless (@params) {
	print RXOUT "\treturn 0;\n";
	print RXOUT "}\n";
	return;
    }

    # Local variables
    print RXOUT "\tstruct ", $func->{name}, "_", $subname, " *obj = call->decoder_private;\n";
    print RXOUT "\tunsigned count;\n";
    print RXOUT "\tunsigned phase = call->phase;\n";

    # Deal with each phase
    print RXOUT "\n";
    print RXOUT "select_phase:\n" if ($have_bulk);
    print RXOUT "\tcount = call->data_count;\n";
    print RXOUT "\tswitch (phase) {\n";

    print RXOUT "\tcase 0:\n";

    my $phase_goto_label = 0;
    my $phix;
    for ($phix = 1; $phix <= $#phases + 1; $phix++) {
	print RXOUT "\n";
	print RXOUT "\t\t/* --- Phase ", $phix, " --- */\n";
	$phase = $phases[$phix - 1];
	if ($phase_goto_label == $phix) {
	    print RXOUT "\tphase_", $phix, ":\n";
	    $phase_goto_label = 0;
	}

	# Determine how big bulk objects are
	if ($phase->{type} eq "blob") {
	    my $p = $phase->{params}->[0];
	    print RXOUT "\t\tcall->blob_size = ", $ptr, "nr__", $p->{name}, ";\n";
	    print RXOUT "\t\tcall->blob_offset = UINT_MAX;\n";
	    print RXOUT "\t\tif (", $ptr, "alloc__", $p->{name}, "(call, &", $ptr, "token__", $p->{name}, ") < 0)\n";
	    print RXOUT "\t\t\treturn -1;\n";
	    print RXOUT "\t\tif (call->blob_size == 0)\n";
	    print RXOUT "\t\t\tgoto phase_", $phix + 1, ";\n";
	    $phase_goto_label = $phix + 1;
	    print RXOUT "\t\tcall->blob_offset = 0;\n";
	} elsif ($phase->{type} eq "bulk") {
	    my $p = $phase->{params}->[0];
	    print RXOUT "\t\tcall->bulk_count = ", $ptr, "nr__", $p->{name}, ";\n";
	    print RXOUT "\t\tcall->bulk_index = UINT_MAX;\n";

	    if ($p->{elem}->{class} eq "basic") {
		print RXOUT "\t\tif (", $ptr, "store__", $p->{name}, "(call, &", $ptr, "token__", $p->{name}, ") < 0)\n";
	    } else {
		print RXOUT "\t\tif (", $ptr, "alloc__", $p->{name}, "(call, &", $ptr, "token__", $p->{name}, ") < 0)\n";
	    }
	    print RXOUT "\t\t\treturn -1;\n";
	    print RXOUT "\t\tif (call->bulk_count == 0)\n";
	    print RXOUT "\t\t\tgoto phase_", $phix + 1, ";\n";
	    $phase_goto_label = $phix + 1;
	    print RXOUT "\t\tcall->bulk_index = 0;\n";
	} else {
	    print RXOUT "\t\tcall->need_size = ", $phase->{size}, ";\n"
	}

	# Entry point for a phase
	print RXOUT "\t\tcall->phase = ", $phix, ";\n";
	print RXOUT "\tcase ", $phix, ":\n";

	print RXOUT "\t\tif (count < ", $phase->{size}, ")";
	if ($phase->{type} eq "bulk" &&
	    $phase->{xdr_size} <= 512
	    ) {
	    print RXOUT " {\n";
	    print RXOUT "\t\t\tunsigned n = call->bulk_count - call->bulk_index;\n";
	    print RXOUT "\t\t\tn = MIN(n, ", int(1024 / $phase->{xdr_size}), ");\n";
	    print RXOUT "\t\t\tcall->need_size = n * ", $phase->{xdr_size}, ";\n";
	    print RXOUT "\t\t\treturn 1;\n";
	    print RXOUT "\t\t}";
	} else {
	    print RXOUT "\n";
	    print RXOUT "\t\t\treturn 1;\n";
	}

	# Unmarshal the data
	print RXOUT "\n";
	foreach my $p (@{$phase->{params}}) {
	    if ($p->{type} eq "blob_size") {
		print RXOUT "\t\t", $ptr, "nr__", $p->{name}, " = rxrpc_dec(call);\n";
		next;
	    } elsif ($p->{type} eq "bulk_size") {
		print RXOUT "\t\t", $ptr, "nr__", $p->{name}, " = rxrpc_dec(call);\n";
		next;
	    }

	    if ($p->{class} eq "bulk" && $p->{elem}->{class} eq "basic") {
		if ($p->{elem}->{xdr_size} == 4) {
		    print RXOUT "\t\tcall->bulk_u32 = rxrpc_dec(call);\n";
		    print RXOUT "\t\tif (", $ptr, "store__", $p->{name}, "(call, &", $ptr, "token__", $p->{name}, ") < 0)\n";
		} elsif ($p->{elem}->{xdr_size} == 8) {
		    print RXOUT "\t\tcall->bulk_u64  = (uint64_t)rxrpc_dec(call) << 32;\n";
		    print RXOUT "\t\tcall->bulk_u64 |= (uint64_t)rxrpc_dec(call);\n";
		    print RXOUT "\t\tif (", $ptr, "store__", $p->{name}, "(call, &", $ptr, "token__", $p->{name}, ") < 0)\n";
		} else {
		    die;
		}
		print RXOUT "\t\t\treturn -1;\n";
		print RXOUT "\t\tcall->bulk_index++;\n";

	    } elsif ($p->{class} eq "bulk" && $p->{elem}->{class} eq "struct") {
		print RXOUT "\t\tif (", $ptr, "alloc__", $p->{name}, "(call, &", $ptr, "token__", $p->{name}, ") < 0)\n";
		print RXOUT "\t\t\treturn -1;\n";
		print RXOUT "\t\trxgen_decode_", $p->{type}, "(call, call->bulk_item);\n";
		print RXOUT "\t\tcall->bulk_index++;\n";
	    } elsif ($p->{class} eq "blob") {
		print RXOUT "\t\trxrpc_dec_blob(call);\n";
		print RXOUT "\t\trxrpc_dec_align(call);\n";
	    } elsif ($p->{class} eq "basic" && $p->{xdr_size} == 4) {
		print RXOUT "\t\t", $ptr, $p->{name}, " = rxrpc_dec(call);\n";
	    } elsif ($p->{class} eq "basic" && $p->{xdr_size} == 8) {
		print RXOUT "\t\t", $ptr, $p->{name}, "  = (uint64_t)rxrpc_dec(call) << 32;\n";
		print RXOUT "\t\t", $ptr, $p->{name}, " |= (uint64_t)rxrpc_dec(call);\n";
	    } elsif ($p->{class} eq "struct") {
		print RXOUT "\t\trxgen_decode_", $p->{type}, "(call, ", $ptr, $p->{name}, ");\n";
	    } else {
		die $p->{where}, ": Unsupported type in decode";
	    }

	    if ($p->{class} eq "blob") {
		print RXOUT "\t\tif (rxrpc_post_dec(call) < 0)\n";
		print RXOUT "\t\t\treturn -1;\n";
		print RXOUT "\t\tif (call->blob_offset < call->blob_size) {\n";
		print RXOUT "\t\t\tphase = ", $phix, ";\n";
		print RXOUT "\t\t\tgoto select_phase;\n";
		print RXOUT "\t\t}\n";
	    } elsif ($p->{class} eq "bulk") {
		print RXOUT "\t\tif (rxrpc_post_dec(call) < 0)\n";
		print RXOUT "\t\t\treturn -1;\n";
		print RXOUT "\t\tif (call->bulk_index < call->bulk_count) {\n";
		print RXOUT "\t\t\tphase = ", $phix, ";\n";
		print RXOUT "\t\t\tgoto select_phase;\n";
		print RXOUT "\t\t}\n";
	    }
	}

	if ($phase->{type} ne "blob" && $phase->{type} ne "bulk") {
	    print RXOUT "\t\tif (rxrpc_post_dec(call) < 0)\n";
	    print RXOUT "\t\t\treturn -1;\n";
	}
    }

    print RXOUT "\n";
    print RXOUT "\t\t/* --- Phase ", $phix, " --- */\n";
    if ($phase_goto_label == $phix) {
	print RXOUT "\tphase_", $phix, ":\n";
	$phase_goto_label = 0;
    }
    print RXOUT "\t\tcall->phase = ", $phix, ";\n";
    print RXOUT "\t\tcall->need_size = 0;\n";
    print RXOUT "\tdefault:\n";
    print RXOUT "\t\treturn 0;\n";
    print RXOUT "\t}\n";
    print RXOUT "}\n";
}

###############################################################################
#
# Emit a function to encode and dispatch a request or a response
#
###############################################################################
sub emit_func_send($$)
{
    my ($func, $what) = @_;
    my $params;
    my $bad_ret;

    # Function definition and arguments
    my @protos;
    if ($what eq "request") {
	@protos = @{$func->{send_request_protos}};
	$params = $func->{request};
	$bad_ret = "NULL";
    } else {
	@protos = @{$func->{send_response_protos}};
	$params = $func->{response};
	$bad_ret = "-1";
    }
    print RXOUT "\n";
    if ($what eq "request") {
	print RXOUT "struct rx_call *", $func->{name} . "(\n";
	print RXOUT "\tstruct rx_connection *z_conn";
    } else {
	print RXOUT "int respond_to_", $func->{name} . "(\n";
	print RXOUT "\tstruct rx_call *call";
    }
    foreach $proto (@protos) {
	print RXOUT ",\n\t", $proto;
    }
    if ($what eq "request" && @{$func->{response}}) {
	print RXOUT ",\n";
	print RXOUT "\tstruct ", $func->{name}, "_response *response";
    }
    print RXOUT ")\n";
    print RXOUT "{\n";

    print RXOUT "\tstruct rx_call *call;\n" if ($what eq "request");

    my @blob_params = grep { $_->{class} eq "blob"; } @{$params};
    my @bulk_params = grep { $_->{class} eq "bulk"; } @{$params};

    # Local variables
    print RXOUT "\tint ret;\n";

    # Check lengths
    if (@blob_params || @bulk_params) {
	print RXOUT "\n";
	print RXOUT "\tif (";
	my $first = 1;
	foreach my $p (@blob_params) {
	    if ($first) {
		$first = 0;
	    } else {
		print RXOUT " ||\n\t    ";
	    }
	    print RXOUT "!", $p->{name};
	    if (exists($p->{dim})) {
		print RXOUT " || nr__", $p->{name}, " > ", $p->{dim};
	    }
	}
	foreach my $p (@bulk_params) {
	    if ($first) {
		$first = 0;
	    } else {
		print RXOUT " ||\n\t    ";
	    }
	    print RXOUT "!get__", $p->{name};
	    if (exists($p->{dim})) {
		print RXOUT " || nr__", $p->{name}, " > ", $p->{dim};
	    }
	}
	print RXOUT ") {\n";
	print RXOUT "\t\terrno = EINVAL;\n";
	print RXOUT "\t\treturn ", $bad_ret, ";\n";
	print RXOUT "\t};\n";
    }

    # Allocate call
    if ($what eq "request") {
	print RXOUT "\n";
	print RXOUT "\tcall = rxrpc_alloc_call(z_conn, 0);\n";
	print RXOUT "\tif (!call)\n";
	print RXOUT "\t\treturn ", $bad_ret, ";\n";
	print RXOUT "\tcall->decoder = rxgen_decode_", $func->{name}, "_response;\n";
	print RXOUT "\tcall->decoder_private = response;\n" if (@{$func->{response}});
    }

    # Marshal the data
    print RXOUT "\n" if ($what eq "request" || @{$params});
    print RXOUT "\trxrpc_enc(call, ", $func->{opcode}, ");\n" if ($what eq "request");
    foreach my $p (@{$params}) {
	if ($p->{class} eq "basic" && $p->{type} !~ /64/) {
	    print RXOUT "\trxrpc_enc(call, ", $p->{name}, ");\n";
	} elsif ($p->{class} eq "basic" && $p->{type} =~ /64/) {
	    print RXOUT "\trxrpc_enc(call, (uint32_t)", $p->{name}, ");\n";
	    print RXOUT "\trxrpc_enc(call, (uint32_t)(", $p->{name}, " >> 32));\n";
	} elsif ($p->{class} eq "struct") {
	    print RXOUT "\trxgen_encode_", $p->{type}, "(call, ", $p->{name}, ");\n";
	} elsif ($p->{class} eq "blob") {
	    print RXOUT "\trxrpc_enc_blob(call, ", $p->{name}, ", nr__", $p->{name}, ");\n";
	    print RXOUT "\trxrpc_enc_align(call);\n";
	} elsif ($p->{class} eq "bulk") {
	    print RXOUT "\trxrpc_enc(call, nr__", $p->{name}, ");\n";
	    print RXOUT "\tcall->bulk_count = nr__", $p->{name}, ";\n";
	    print RXOUT "\tfor (call->bulk_index = 0; call->bulk_index < call->bulk_count; call->bulk_index++) {\n";
	    if ($p->{elem}->{class} eq "struct") {
		print RXOUT "\t\tstruct ", $p->{elem}->{type}, " x;\n";
	    } else {
		print RXOUT "\t\t", $p->{elem}->{type}, " x;\n";
	    }
	    print RXOUT "\t\tcall->bulk_item = &x;\n";
	    print RXOUT "\t\tif (get__", $p->{name}, "(call, token__", $p->{name}, ") < 0)\n";
	    print RXOUT "\t\t\tgoto error;\n";
	    if ($p->{elem}->{class} eq "basic" && $p->{elem}->{type} !~ /64/) {
		if ($p->{type} !~ /^u/) {
		    print RXOUT "\t\trxrpc_enc(call, (u", $p->{type}, ")x);\n";
		} else {
		    print RXOUT "\t\trxrpc_enc(call, x);\n";
		}
	    } elsif ($p->{class} eq "basic" && $p->{type} =~ /64/) {
		print RXOUT "\t\trxrpc_enc(call, (uint32_t)", $p->{name}, ");\n";
		print RXOUT "\t\trxrpc_enc(call, (uint32_t)(", $p->{name}, " >> 32));\n";
	    } elsif ($p->{elem}->{class} eq "struct") {
		print RXOUT "\t\trxgen_encode_", $p->{elem}->{type}, "(call, &x);\n";
	    } else {
		die $p->{where}, "No decoding for array type '$type'";
	    }
	    print RXOUT "\t}\n";
	} else {
	    die $p->{where}, ": Unsupported param encoding";
	}
    }

    print RXOUT "\tif (rxrpc_post_enc(call) < 0)\n";
    print RXOUT "\t\tgoto error;\n";
    print RXOUT "\tcall->more_send = 0;\n";

    # Send the message
    print RXOUT "\n";
    print RXOUT "\tret = rxrpc_send_data(call);\n";
    print RXOUT "\tif (ret < 0)\n";
    print RXOUT "\t\tgoto error;\n";
    if ($what eq "request") {
	print RXOUT "\treturn call;\n";
    } else {
	print RXOUT "\treturn 0;\n";
    }

    print RXOUT "\n";
    print RXOUT "error:\n";
    print RXOUT "\trxrpc_terminate_call(call, 0);\n";
    print RXOUT "\treturn ", $bad_ret, ";\n";
    print RXOUT "}\n";
}

1;
