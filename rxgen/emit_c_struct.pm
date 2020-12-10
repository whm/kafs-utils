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
# Emit structure encoders and decoders predeclarations
#
###############################################################################
sub emit_struct_encdec_decls ($) {
    my ($struct) = @_;

    print RXOUT "/* ", $struct->{type}, " XDR size ", $struct->{xdr_size}, " */\n"
}

###############################################################################
#
# Emit structure encoders and decoders
#
###############################################################################
sub emit_struct_encdec ($) {
    my ($struct) = @_;

    # Write out a C structure definition for this type
    print RXHDR "struct ", $struct->{type}, " {\n";
    foreach my $m (@{$struct->{members}}) {
	if ($m->{class} eq "basic") {
	    print RXHDR "\t", $m->{type}, "\t", $m->{name};
	} elsif ($m->{class} eq "struct") {
	    print RXHDR "\tstruct ", $m->{type}, "\t", $m->{name};
	} elsif ($m->{class} eq "array") {
	    if ($m->{elem}->{class} eq "basic") {
		print RXHDR "\t", $m->{elem}->{type}, "\t", $m->{name}, "[", $m->{dim}, "]";
	    } else {
		print RXHDR "\tstruct ", $m->{elem}->{type}, "\t", $m->{name}, "[", $m->{dim}, "]";
	    }
	} else {
	    die $m->{where}, ": Unsupported type class '", $m->{class}, "'\n";
	}
	print RXHDR ";\n";
    }
    print RXHDR "};\n";

    # Write an encoding function
    print RXHDR "extern void rxgen_encode_", $struct->{type}, "(struct rx_call *call, const struct ", $struct->{type}, " *p);\n";

    print RXOUT "void rxgen_encode_", $struct->{type}, "(struct rx_call *call, const struct ", $struct->{type}, " *p)\n";
    print RXOUT "{\n";

    foreach my $m (@{$struct->{members}}) {
	if ($m->{class} eq "array") {
	    print RXOUT "\tint i;\n\n";
	    last;
	}
    }

    foreach my $m (@{$struct->{members}}) {
	if ($m->{class} eq "basic") {
	    if ($m->{type} !~ /64/) {
		print RXOUT "\trxrpc_enc(call, p->", $m->{name}, ");\n";
	    } else {
		die $m->{where}, ": No encoding for type '", $m->{type}, "'";
	    }
	} elsif ($m->{class} eq "struct") {
	    print RXOUT "\trxgen_encode_", $m->{type}, "(call, &p->", $m->{name}, ");\n";
	} elsif ($m->{class} eq "array") {
	    print RXOUT "\tfor (i = 0; i < ", $m->{dim}, "; i++)\n";
	    if ($m->{elem}->{class} eq "basic" && $m->{elem}->{type} !~ /64/) {
		print RXOUT "\t\trxrpc_enc(call, p->", $m->{name}, "[i]);\n";
	    } elsif ($m->{elem}->{class} eq "struct") {
		print RXOUT "\t\trxgen_encode_", $m->{elem}->{type},
				"(call, &p->", $m->{name}, "[i]);\n";
	    } else {
		die $m->{where}, ": No encoding for array type '", $m->{elem}->{type}, "'";
	    }
	} else {
	    die $m->{where}, "No encoding for type class '$class'";
	}
    }

    print RXOUT "}\n";
    print RXOUT "\n";

    # Write a decoding function
    print RXHDR "extern void rxgen_decode_", $struct->{type}, "(struct rx_call *call, struct ", $struct->{type}, " *p);\n";

    print RXOUT "void rxgen_decode_", $struct->{type}, "(struct rx_call *call, struct ", $struct->{type}, " *p)\n";
    print RXOUT "{\n";

    foreach my $m (@{$struct->{members}}) {
	if ($m->{class} eq "array") {
	    print RXOUT "\tint i;\n\n";
	    last;
	}
    }

    foreach my $m (@{$struct->{members}}) {
	if ($m->{class} eq "basic") {
	    if ($m->{type} !~ /64/) {
		print RXOUT "\tp->", $m->{name}, " = rxrpc_dec(call);\n";
	    } else {
		die $m->{where}, "No decoding for type '$type'";
	    }
	} elsif ($m->{class} eq "struct") {
	    print RXOUT "\trxgen_decode_", $m->{type}, "(call, &p->", $m->{name}, ");\n";
	} elsif ($m->{class} eq "array") {
	    print RXOUT "\tfor (i = 0; i < ", $m->{dim}, "; i++)\n";
	    if ($m->{elem}->{class} eq "basic" && $m->{elem}->{type} !~ /64/) {
		print RXOUT "\t\tp->", $m->{name}, "[i] = rxrpc_dec(call);\n";
	    } elsif ($m->{elem}->{class} eq "struct") {
		print RXOUT "\t\trxgen_decode_", $m->{elem}->{type}, "(call, &p->", $m->{name}, "[i]);\n";
	    } else {
		die $m->{where}, "No decoding for array type '$type'";
	    }
	} else {
	    die $m->{where}, "No decoding for type class '$class'";
	}
    }

    print RXOUT "}\n";
}

1;
