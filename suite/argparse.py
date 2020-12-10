#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Parse an argument list for a subcommand
#
__copyright__ = """
Copyright (C) 2014 Red Hat, Inc. All Rights Reserved.
Written by David Howells (dhowells@redhat.com)

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public Licence
as published by the Free Software Foundation; either version
2 of the Licence, or (at your option) any later version.
"""

from exception import AFSArgumentError, AFSHelpFlag
from afs.lib.output import set_verbosity

def get_cell(switch, params):
    from afs.lib.cell import cell
    return cell(params[0])

def get_bosserver(switch, params):
    from afs.lib.bosserver import bosserver
    return bosserver(params[0])

def get_fileserver(switch, params):
    from afs.lib.fileserver import fileserver
    return fileserver(params[0])

def get_volserver(switch, params):
    from afs.lib.volserver import volserver
    return volserver(params[0])

def get_vlservers(switch, params):
    from afs.lib.vlserver import vlserver
    servers = []
    for i in params:
        servers.append(vlserver(params[0]))
    return servers

def get_volume_name(switch, params):
    return params[0]

def get_volume_names(switch, params):
    return params

def get_machine_name(switch, params):
    return params[0]

def get_machine_names(switch, params):
    return params

def get_path_name(switch, params):
    return params[0]

def get_path_names(switch, params):
    return params

def get_file_name(switch, params):
    return params[0]

def get_file_names(switch, params):
    return params

def get_partition_id(switch, params):
    from afs.lib.partition import part2id
    return part2id(params[0])

def get_auth(switch, params):
    return params

def get_uuid(switch, params):
    from afs.lib.uuid import str2uuid
    return str2uuid(params[0])

def get_string(switch, params):
    return params[0]

def get_strings(switch, params):
    return params

def get_dummy(switch, params):
    return params

def get_verbose(switch, params):
    set_verbosity()
    return params

def do_get_id(i):
    if i == "":
        raise AFSArgumentError("UID/GID identifier is empty string")
    if not i.isnumeric() and (i[0] != "-" or not i[1:].isnumeric()):
        raise AFSArgumentError("UID/GID identifier is not numeric")
    return int(i)

def get_id(switch, params):
    return do_get_id(params[0])

def get_ids(switch, params):
    ids = []
    for i in params:
        ids.append(do_get_id(i))
    return ids

def do_get_uid(i):
    if i == "":
        raise AFSArgumentError("UID identifier is empty string")
    if not i.isnumeric():
        raise AFSArgumentError("UID identifier is a positive integer")
    return int(i)

def get_uid(switch, params):
    return do_get_uid(params[0])

def get_uids(switch, params):
    ids = []
    for i in params:
        ids.append(do_get_uid(i))
    return ids

def do_get_gid(i):
    if i == "":
        raise AFSArgumentError("GID identifier is empty string")
    if i[0] != "-" or not i[1:].isnumeric():
        raise AFSArgumentError("GID identifier is a positive integer")
    return int(i)

def get_gid(switch, params):
    return do_get_gid(params[0])

def get_gids(switch, params):
    ids = []
    for i in params:
        ids.append(do_get_gid(i))
    return ids

###############################################################################
#
# Parse an argument list according to a defined set of switches.
#
# The following is an excerpt from the AFS Reference Manual, Introduction to
# AFS commands:
#
# CONDITIONS FOR OMITTING SWITCHES
#
#    It is always acceptable to type the switch part of an argument, but in
#    many cases it is not necessary. Specifically, switches can be omitted if
#    the following conditions are met.
#
#    (*) All of the command's required arguments appear in the order prescribed
#        by the syntax statement.
#
#    (*) No switch is provided for any argument.
#
#    (*) There is only one value for each argument (but note the important
#        exception discussed in the following paragraph).
#
#    Omitting switches is possible only because there is a prescribed order for
#    each command's arguments. When the issuer does not include switches, the
#    command interpreter relies instead on the order of arguments; it assumes
#    that the first element after the operation code is the command's first
#    argument, the next element is the command's second argument, and so
#    on. The important exception is when a command's final required argument
#    accepts multiple values. In this case, the command interpreter assumes
#    that the issuer has correctly provided one value for each argument up
#    through the final one, so any additional values at the end belong to the
#    final argument.
#
#    The following list describes the rules for omitting switches from the
#    opposite perspective: an argument's switch must be provided when any of
#    the following conditions apply.
#
#    (*) The command's arguments do not appear in the prescribed order.
#
#    (*) An optional argument is omitted but a subsequent optional argument is
#        provided.
#
#    (*) A switch is provided for a preceding argument.
#
#    (*) More than one value is supplied for a preceding argument (which must
#        take multiple values, of course); without a switch on the current
#        argument, the command interpreter assumes that the current argument is
#        another value for the preceding argument.
#
###############################################################################
def parse_arguments(args, available_arguments, argument_size_limits,
                    cant_combine_arguments):
    result = {}
    need_switch = False
    i = 0       # Given arguments index
    av = 0      # Available arguments index

    #print args

    if len(args) == 0:
        if len(available_arguments) > 0 and available_arguments[0][0] == "r":
            raise AFSArgumentError("Missing required parameters")
        return result

    # Process all the optional arguments or switch-based required arguments
    while i < len(args):
        match = False
        params = []

        if args[i][0] != "-" or args[i][1:].isnumeric():
            # Deal with positional arguments
            if need_switch:
                raise AFSArgumentError("Need switch before argument " + i)
            if av >= len(available_arguments):
                raise AFSArgumentError("Unexpected positional argument")
            match = available_arguments[av]
            pattern = match[2]
            if pattern[0] == "f":
                raise AFSArgumentError("Unexpected positional argument")
            av = av + 1

            params.append(args[i])
            i = i + 1

            if match[2][1] == "m":
                # Multiple-value arguments that are not preceded by their
                # switch are forced to be single-value if there's yet another
                # required argument following.
                if av < len(available_arguments) and available_arguments[av][2][0] == "r":
                    pass
                else:
                    # All remaining arguments up to the next switch belong to this
                    while i < len(args):
                        if args[i][0] == "-" and not args[i][1:].isnumeric():
                            break
                        params.append(args[i])
                        i = i + 1
                    need_switch = True

        else:
            # Deal with tagged arguments
            switch = args[i][1:]
            i = i + 1

            if switch == "help":
                raise AFSHelpFlag
            if switch == "":
                raise AFSArgumentError("Missing switch name")

            # Look up the switch in the table of possible arguments and flags
            for j in available_arguments:
                if j[0] == switch:
                    match = j
                    break
                if j[0].startswith(switch):
                    if match:
                        raise AFSArgumentError("Ambiguous switch name abbreviation '-" + switch + "'")
                    match = j
            if not match:
                raise AFSArgumentError("Unsupported switch '-" + switch + "'")

            # Reject repeat flags
            if match[0] in result:
                raise AFSArgumentError("Duplicate switch '-" + switch + "' not permitted")

            # Arrange the parameters associated with the switch into a list
            while i < len(args):
                if args[i][0] == "-" and not args[i][1:].isnumeric():
                    break
                params.append(args[i])
                i = i + 1

        # Check that we have the number of arguments we're expecting
        pattern = match[2]
        if pattern[1] == "n" and len(params) != 0:
            raise AFSArgumentError("Switch '-" + switch + "' expects no arguments")
        if pattern[1] == "s" and len(params) != 1:
            raise AFSArgumentError("Switch '-" + switch + "' expects one argument")
        if pattern[1] == "m" and len(params) < 1:
            raise AFSArgumentError("Switch '-" + switch + "' expects one or more arguments")

        # Check that none of the arguments are too big
        if match[0] in argument_size_limits:
            limit = argument_size_limits[match[0]]
            for j in params:
                if len(j) > limit:
                    raise AFSArgumentError("Switch '-" + switch + "' has an overlong argument")

        # Call the syntax checker
        syntax = match[1]
        result["raw." + match[0]] = params
        result[match[0]] = syntax(match[0], params)

    # Check for missing required arguments
    for j in available_arguments:
        switch = j[0]
        pattern = j[2]
        if j[2][0] != "r":
            break
        if switch not in result:
            raise AFSArgumentError("Missing '-" + switch + "' argument")

    # Check for invalid argument combinations
    for i in cant_combine_arguments:
        if i[0] in result and i[1] in result:
            raise AFSArgumentError("Can't combine -" + i[0] + " with -" + i[1])

    return result
