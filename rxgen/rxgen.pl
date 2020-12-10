#!/usr/bin/perl -w
#
# Tool for processing an RxRPC-based RPC API definition in a C header file to
# produce (un)marshalling code and RPC functions to implement that API.
#
# It also produces a python module containing wrappers for the types, RPC
# functions and constants in the API definition.
#
#
# Copyright (C) 2014 Red Hat, Inc. All Rights Reserved.
# Written by David Howells (dhowells@redhat.com)
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public Licence
# as published by the Free Software Foundation; either version
# 2 of the Licence, or (at your option) any later version.
#

use strict;
use lib "rxgen";
use emit_c_struct;
use emit_c_sync_funcs;
use emit_py_types;
use emit_py_sync_funcs;
use emit_py_module;

die "Need list of xg files to process\n" if ($#ARGV < 0);

our @structs = ();	# Structure definitions
our %struct_sizes = ();	# Structure sizes
our @funcs = ();	# Functions in declaration order
our %func_names = ();	# Function name uniquifier
our %constants = ();	# Constants
our %packages = ();	# Packages
our $abort_codes = ();	# Abort codes
our %abort_syms = ();	# Abort symbol to code map
our %abort_ids = ();	# Abort code to symbol map
our $abort_count = 0;	# Number of abort codes
our @py_type_defs = ();	# Python type definitions
our @py_func_defs = (); # Python function definitions

$constants{RXRPC_SECURITY_PLAIN}	= { name => "RXRPC_SECURITY_PLAIN",   val => 0 };
$constants{RXRPC_SECURITY_AUTH}		= { name => "RXRPC_SECURITY_AUTH",    val => 1 };
$constants{RXRPC_SECURITY_ENCRYPT}	= { name => "RXRPC_SECURITY_ENCRYPT", val => 2 };

#
# Divide the lines from the files up into typed collections
#
my $pkg = 0;
my $struct = 0;
my $func = 0;
my $cpp_exclude = 0;
my $error_codes = 0;
my $comment_discard = 0;

my @files = @ARGV;
my $file = "";
my $where = "";

###############################################################################
#
# Handle defined types.
#
# Each type is specified by a hash of the following elements:
#
#	class		Complexity class (basic, string, struct, blob, array, bulk)
#	type		Basic/struct type (char, {u,}int{8,16,32,64}_t, opaque, struct name)
#	elem		Ref to element type def (if array/bulk)
#	multi		1 if array or bulk type, 0 otherwise
#	dim		Number of elements in array or max elements in bulk array (if array/bulk)
#	members		Members of struct
#	xdr_size	Size of XDR encoded object
#	where		Where defined in file
#	banner		Banner comment
#
# Members/parameters take a copy of their parent type's hash and add:
#
#	name		Member or parameter name
#	ptr		"*" if a pointer
#	dir		Direction (IN, OUT or INOUT)
#
###############################################################################
# Defined types
our %types = (
    "char"	=> { class => "basic", type => "char",		xdr_size => 4, multi => 0, },
    "int8_t"	=> { class => "basic", type => "int8_t",	xdr_size => 4, multi => 0, },
    "int16_t"	=> { class => "basic", type => "int16_t",	xdr_size => 4, multi => 0, },
    "int32_t"	=> { class => "basic", type => "int32_t",	xdr_size => 4, multi => 0, },
    "int64_t"	=> { class => "basic", type => "int64_t",	xdr_size => 8, multi => 0, },
    "uint8_t"	=> { class => "basic", type => "uint8_t",	xdr_size => 4, multi => 0, },
    "uint16_t"	=> { class => "basic", type => "uint16_t",	xdr_size => 4, multi => 0, },
    "uint32_t"	=> { class => "basic", type => "uint32_t",	xdr_size => 4, multi => 0, },
    "uint64_t"	=> { class => "basic", type => "uint64_t",	xdr_size => 8, multi => 0, },
    "string"	=> { class => "string", type => "char",		xdr_size => 4, multi => 0, },
    "opaque"	=> { class => "opaque", type => "void",		xdr_size => 4, multi => 0, },
    );

sub look_up_type($)
{
    my ($type) = @_;

    die $where, ": Undefined type '$type'\n" unless exists $types{$type};
    return $types{$type};
}

sub define_type($$)
{
    my ($new_type, $as) = @_;
    die $where, ": Redefining type '$new_type'\n" if exists $types{$new_type};
    $as->{where} = $where;
    $types{$new_type} = $as;
}

sub define_typedef($$$)
{
    my ($new_type, $as, $flags) = @_;

    my $type = look_up_type($as);

    my %combined = %{$type};

    if (exists $flags->{class} && $flags->{class} eq "bulk") {
	if ($type->{class} eq "string" ||
	    $type->{class} eq "opaque") {
	    $flags->{class} = "blob";
	}
    }

    if (exists $flags->{class} &&
	($flags->{class} eq "blob" ||
	 $flags->{class} eq "bulk" ||
	 $flags->{class} eq "array")) {
	die $where, ": Typedef'ing array/bulk as array/bulk not supported\n"
	    if ($type->{multi});
	$combined{multi} = 1;
	$combined{class} = $flags->{class};
	$combined{elem} = $type;
	$combined{dim} = $flags->{dim} if (exists $flags->{dim});
	$combined{xdr_size} *= $combined{dim} if ($flags->{class} eq "array");
    }

    die if (exists $combined{dim} && $combined{dim} eq -1);

    define_type($new_type, \%combined);
}

###############################################################################
#
# Parse an xg interface definition
#
###############################################################################
sub parse_xg($) {
    my ($filename) = @_;
    $file = $filename;
    open my $APIHDR, "<$filename" || die $filename;
    while (my $line = <$APIHDR>) {
	my $pre_comment = "";
	$where = $file . ':' . $. ;

	# Detect #if 0/#endif pairs to exclude parts
	if ($line =~ m@^#\s*if\s+0@) {
	    die $where, ": Embedded #if 0 clause\n" if $cpp_exclude;
	    $cpp_exclude = 1;
	    next;
	}

	if ($line =~ m@^#\s*endif@) {
	    die $where, ": Unbalanced #endif\n" unless $cpp_exclude;
	    $cpp_exclude = 0;
	    next;
	}

	next if $cpp_exclude;

	chomp($line);

	# Extract error codes
	if ($line eq "/* Error codes */") {
	    $error_codes = 1;
	    next;
	}

	$error_codes = 0 if ($line eq "");

	# Discard comments
	my $line_comment = "";
find_comment_terminator:
	if ($comment_discard) {
	    # Find the terminator for a comment we're discarding
	    if ($line =~ m@(.*)[*]/(.*)@) {
		$line_comment = $1;
		$line = $pre_comment . $2;
		$comment_discard = 0;
	    } else {
		$line = $pre_comment;
		goto discarded_comments if ($line);
		next;
	    }
	}

	if ($line =~ m@(.*)/[*](.*)@) {
	    $pre_comment = $1;
	    $line = $2;
	    $comment_discard = 1;
	    goto find_comment_terminator;
	}

discarded_comments:
	# Remove leading/trailing whitespace and distil interior whitespace
	# down to a single space.  Also remove whitespace next to symbols
	# (excluding underscores) and remove blank lines.
	$line =~ s/^\s+//;
	$line =~ s/\s+$//;
	$line =~ s/\s+/\t/g; # Convert all whitespace to single tabs as an intermediate step
	# Convert any tab surrounded by two numbers/symbols into a space
	$line =~ s!([a-zA-Z0-9_])\t([a-zA-Z0-9_])!$1 $2!g;
	# Discard any remaining tabs (have an adjacent symbol)
	$line =~ s!\t!!g;
	next if (!$line);

	$line_comment =~ s/^\s+//;
	$line_comment =~ s/\s+$//;
	$line_comment =~ s/\s+/ /g;

	#print "'$line'\n";

	# Complain about #defines
	die $where, ": Use const not #define" if ($line =~ /^#define/);

	# Extract package prefix
	if ($line =~ /^package\s+([A-Za-z_][A-Za-z0-9_]*)/) {
	    my $prefix = $1;
	    my $name = $prefix;
	    $name =~ s/_$//;
	    $pkg = {
		name			=> $name,
		prefix			=> $prefix,
		abort_codes		=> [],
	    };
	    $packages{$prefix} = $pkg;
	    $abort_codes = $pkg->{abort_codes};
	    next;
	}

	#######################################################################
	# Extract constants
	#
	if ($line =~ /^const ([A-Za-z0-9_]+)=(.*);/) {
	    my $c = $1;
	    my $v = $2;
	    die $where, ": Duplicate constant $c (original at ", $constants{$c}->{where}, ": )"
		if (exists $constants{$c});
	    $v =~ s/^ //;
	    $v =~ s/ $//;
	    $constants{$c} = { name => $c,
			       val => $v,
			       where => $where,
	    };
	    if ($error_codes) {
		if ($v < 0) {
		    $v = 0xffffffff + $v + 1;
		}

		die $where, ": Duplicate abort ID"
		    if (exists $abort_ids{$v});

		my %abort = (
		    sym => $c,
		    id => $v,
		    msg => $line_comment,
		);

		push @{$abort_codes}, \%abort;
		$abort_syms{$c} = \%abort;
		$abort_ids{$v} = \%abort;
		$abort_count++;
	    }
	    next;
	}

	#######################################################################
	# Extract typedefs
	#
	if ($line =~ /^typedef ([a-zA-Z_][a-zA-Z0-9_]*) ([a-zA-Z_][a-zA-Z0-9_]*);/) {
	    define_typedef($2, $1, { });
	    next;
	}

	if ($line =~ /^typedef ([a-zA-Z_][a-zA-Z0-9_]*) ([a-zA-Z_][a-zA-Z0-9_]*)<>;/) {
	    define_typedef($2, $1, { class => "bulk" });
	    next;
	}

	if ($line =~ /^typedef ([a-zA-Z_][a-zA-Z0-9_]*) ([a-zA-Z_][a-zA-Z0-9_]*)<([a-zA-Z0-9_]+)>;/) {
	    define_typedef($2, $1, { class => "bulk", dim => $3 });
	    next;
	}

	#######################################################################
	# Extract structures
	#
	if ($line =~ /^struct ([a-zA-Z_][a-zA-Z0-9_]*){/) {
	    my %type = (
		class	=> "struct",
		type	=> $1,
		members	=> [],
		xdr_size => 0,
	    );
	    define_type($1, \%type);
	    push @structs, \%type;
	    $struct = \%type;
	    next;
	}

	if ($line =~ /};/ && $struct) {
	    $struct = 0;
	    next;
	}

	# Extract structure members
	if ($struct) {
	    if ($line =~ /([a-zA-Z_][a-zA-Z0-9_]*) ([a-zA-Z_][a-zA-Z0-9_]*);/) {
		my %member = %{look_up_type($1)};
		die $where, ": Don't support bulk constructs in structs\n"
		    if ($member{class} eq "bulk" || $member{class} eq "blob");
		$member{name} = $2;
		$member{where} = $where;
		push $struct->{members}, \%member;
		$struct->{xdr_size} += $member{xdr_size};
		#print "nonarray $2\n";
	    } elsif ($line =~ /([a-zA-Z_][a-zA-Z0-9_]*) ([a-zA-Z_][a-zA-Z0-9_]*)\[([^]]+)\];/) {
		my $element = look_up_type($1);
		die $where, ": Don't support arrays of bulk constructs or arrays\n"
		    if ($element->{multi});

		my %member = ();
		$member{class} = "array";
		$member{elem} = $element;
		$member{name} = $2;
		$member{dim}  = $3;
		$member{where} = $where;

		if ($member{dim} =~ /^[0-9]+$/) {
		    $constants{$member{dim}} = {
			val => $member{dim},
		    };
		} elsif (exists $constants{$member{dim}}) {
		} else {
		    die $where, ": No constant for [", $member{dim}, "]\n"
		}
		$member{xdr_size} = $constants{$member{dim}}->{val} * $element->{xdr_size};
		push $struct->{members}, \%member;
		$struct->{xdr_size} += $member{xdr_size};
		#print "array $2\n";
	    } else {
		die $where, ": Unrecognised struct member '$line'";
	    }
	}

	#######################################################################
	# Extract functions
	#
	if (!$func && $line =~ /^([a-zA-Z_][a-zA-Z0-9_]*)\((.*)$/) {
	    #print "func $1\n";
	    my $name = $1;
	    die $where, ": No package set" unless $pkg;
	    my $func_name = $pkg->{prefix} . $name;
	    my %function = (
		pkg	=> $pkg,
		rawname	=> $name,
		name	=> $func_name,
		params	=> [],
		where	=> $where,
		split	=> 0,
		multi	=> 0,
		);
	    die $where, ": Duplicate function name '$func_name'\n"
		if (exists($func_names{$func_name}));
	    $func_names{$func_name} = \%function;
	    push @funcs, \%function;
	    $func = \%function;
	    $line = $2;
	}

	# Extract function parameters
	if ($func) {
	  parse_param:
	    my $dir = "";
	    my $term = 0;
	    my $bulk_dim = 0;

	    # Split parameters that are on the same line and divide the last
	    # parameter from the function closure
	    my $clause = $line;
	    if ($line =~ /^([^,)]*),(.*)$/) {
		$clause = $1;
		$line = $2;
	    } elsif ($line =~ /^([^)]*)([)].*)$/) {
		$clause = $1;
		$line = $2;
	    }

	    #print "CLAUSE: '", $clause, "'\n";

	    $dir = $1 if ($clause =~ s@^(IN|OUT|INOUT) @@);

	    if ($clause =~ s@<>@@) {
		$bulk_dim = -1;
	    } elsif ($clause =~ s@<([0-9]+)>@@) {
		$bulk_dim = $1;
		$constants{$bulk_dim} = {
		    val => $bulk_dim,
		};
	    } elsif ($clause =~ s@<([a-zA-Z_][a-zA-Z0-9_]*)>@@) {
		die $where, ": No constant for $1\n" unless exists $constants{$1};
		$bulk_dim = $1;
	    }

	    if ($clause =~ /([a-zA-Z_][a-zA-Z0-9_]*)([*]*| )([a-zA-Z_][a-zA-Z0-9_]*)/) {
		die $where, ": No parameter direction specified\n" unless $dir;

		my $type = look_up_type($1);
		my %param = %{$type};
		$param{ptr} = $2;
		$param{name} = $3;
		$param{dir} = $dir;
		$param{where} = $where;

		die $where, ": 'string' only supported with IN\n"
		    if ($param{type} eq "string" && $dir ne "IN");
		die $where, ": Array parameters not supported\n"
		    if ($param{class} eq "array");
		if ($bulk_dim) {
		    die $where, ": Bulk-of-bulk parameters not supported\n"
			if ($param{class} eq "bulk");
		    if ($type->{class} eq "string" ||
			$type->{class} eq "opaque") {
			$param{class} = "blob";
		    } else {
			$param{class} = "bulk";
		    }
		    $param{elem} = $type;
		    $param{dim} = $bulk_dim unless $bulk_dim eq -1;
		}

		$param{ptr} = "*" if ($type->{class} eq "string");

		#print "- ", $1, " ", $param{name}, " ISA ", $param{class}, ".", $param{type}, " ", $param{dir}, "\n";
		push $func->{params}, \%param;

	    } elsif ($clause eq "") {
		# No parameter here
	    } else {
		die $where, ": Unhandled RPC call parameter '$clause'";
	    }

	    next unless ($line);
	    goto parse_param unless ($line =~ /^[)]/);

	    # Parse the function termination
	    if ($line =~ s/[)]=([a-zA-Z0-9_]*);$//) {
		$term = 1;
		$func->{opcode} = $1;
	    } elsif ($line =~ s/[)]split=([a-zA-Z0-9_]*);$//) {
		$func->{split} = 1;
		$term = 1;
		$func->{opcode} = $1;
	    } elsif ($line =~ s/[)]multi=([a-zA-Z0-9_]*);$//) {
		$func->{multi} = 1;
		$term = 1;
		$func->{opcode} = $1;
	    } else {
		die $where, ": Unexpected line termination '$line'";
	    }

	    if ($term) {
		$func = 0;
		next;
	    }
	}
    }

    close($APIHDR);
    $pkg = 0;
}

foreach my $file (@files) {
    parse_xg($file);
}

print "Extracted ", scalar keys %constants, " constants\n";
print "Extracted ", scalar @structs, " structs\n";
print "Extracted ", scalar keys %types, " types\n";
print "Extracted ", scalar @funcs, " functions\n";

my @no_abort_codes = ();
foreach $_ (sort(keys(%packages))) {
    my $pkg = $packages{$_};
    if (@{$pkg->{abort_codes}}) {
	print "Extracted ", scalar @{$pkg->{abort_codes}}, " ", $pkg->{name}, " abort codes\n";
    } else {
	push @no_abort_codes, $pkg->{name};
    }
}
print "No abort codes for ", join(" ", @no_abort_codes), "\n" if (@no_abort_codes);

###############################################################################
#
# Create the output files and emit the file prologues.
#
###############################################################################
open RXHDR, ">afs_xg.h" || die "afs_xg.h";
print RXHDR "/* AUTOGENERATED */\n";
#print RXHDR "#define _XOPEN_SOURCE\n";
print RXHDR "#include <stdint.h>\n";
print RXHDR "#include \"rxgen.h\"\n";

open RXOUT, ">afs_xg.c" || die "afs_xg.c";
print RXOUT "/* AUTOGENERATED */\n";
print RXOUT "#include \"afs_xg.h\"\n";
print RXOUT "#include <stdio.h>\n";
print RXOUT "#include <stdlib.h>\n";
print RXOUT "#include <string.h>\n";
print RXOUT "#include <unistd.h>\n";
print RXOUT "#include <errno.h>\n";
print RXOUT "#include <sys/socket.h>\n";
print RXOUT "#include <sys/param.h>\n";
print RXOUT "#include <arpa/inet.h>\n";
print RXOUT "\n";

open PYHDR, ">afs_py.h" || die "afs_py.h";
print PYHDR "/* AUTOGENERATED */\n";
print PYHDR "#include <Python.h>\n";
print PYHDR "#include \"afs_xg.h\"\n";
print PYHDR "#include \"py_rxgen.h\"\n";

open PYOUT, ">afs_py.c" || die "afs_py.c";
print PYOUT "/* AUTOGENERATED */\n";
print PYOUT "#include <Python.h>\n";
print PYOUT "#include \"structmember.h\"\n";
print PYOUT "#include \"afs_py.h\"\n";
print PYOUT "#include <arpa/inet.h>\n";
print PYOUT "\n";

# Declare constants
print RXHDR "\n";
foreach my $c (sort keys %constants) {
    print RXHDR "#define $c ", $constants{$c}->{val}, "\n" unless ($c =~ /^[0-9]/)
}

# Declare types
foreach my $s (@structs) {
    emit_struct_encdec_decls($s);
    emit_py_type_wrapper_decls($s);
}

foreach my $s (@structs) {
    emit_struct_encdec($s);
    emit_py_type_wrapper($s);
}

###############################################################################
#
# Emit RPC call functions.  For this we need to classify parameters according
# to input and output usage and work out how big the RPC messages will be.
#
###############################################################################
foreach $func (@funcs) {
    # Dump the banner comment block
    print RXOUT "/*\n";
    print RXOUT " * RPC Call ", $func->{name}, "\n";
    print RXOUT " */\n";

    # Find the Operation ID
    die "Operation ID unspecified for ", $func->{name}, "\n"
	unless exists $func->{opcode};

    # Filter the parameters into request and response
    my @request = ();
    my @response = ();

    foreach my $p (@{$func->{params}}) {
	#print RXOUT $dir, " ", $type, " ", $name, "\n";

	if ($p->{class} eq "basic") {
	    ;
	} elsif ($p->{class} eq "struct") {
	    die unless (exists $p->{xdr_size});
	} elsif ($p->{class} eq "blob") {
	    die $p->{where}, ": No element type" unless (exists $p->{elem});
	    if (exists $p->{dim}) {
		die $where, ": Missing constant ", $p->{dim} unless exists $constants{$p->{dim}};
	    }
	} elsif ($p->{class} eq "bulk") {
	    die $p->{where}, ": No element type" unless (exists $p->{elem});
	    die $p->{where}, ": Element has no XDR size" unless (exists $p->{elem}->{xdr_size});
	    if (exists $p->{dim} && $p->{elem}->{xdr_size} > 0) {
		die $where, ": Missing constant ", $p->{dim} unless exists $constants{$p->{dim}};
	    }
	} else {
	    die $p->{where}, ": Unsupported param class \"", $p->{class}, "\"";
	}

	if ($p->{dir} eq "IN") {
	    push @request, $p;
	} elsif ($p->{dir} eq "OUT") {
	    push @response, $p;
	} elsif ($p->{dir} eq "INOUT") {
	    push @response, $p;
	    push @request, $p;
	}
    }

    $func->{request} = \@request;
    $func->{response} = \@response;

    emit_func_prototype($func);
    emit_func_decode($func, "client", "response", \@response);
    emit_func_send($func, "request");
    #emit_func_decode($func, "server", "request", \@request);
    #emit_func_send($func, "response");

    emit_py_func_param_object($func, "request");
    emit_py_func_param_object($func, "response");
    emit_py_func_bulk_helper($func);
    emit_py_func_decode($func, "client", "response", \@response);
    emit_py_func_decode($func, "server", "request", \@request);
    emit_py_func_simple_sync_call($func);
}

emit_py_module();
