#!/usr/bin/python3
# AFS Toolset commandline tab completion expander
# -*- coding: utf-8 -*-
#

__copyright__ = """
Copyright (C) 2014 Red Hat, Inc. All Rights Reserved.
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

import sys, os

import afs.commands
from afs.argparse import *
from afs.lib.output import *

logfile = None

def log(*args):
    global logfile
    
    if True:
        return  # Don't actually log

    if not logfile:
        logfile = open("/tmp/afs_completer.log", "a")
    for i in args:
        logfile.write(str(i))

###############################################################################
#
# Generate a list of matching cell names
#
###############################################################################
def expand_cell_list(prefix):
    cells = []
    for line in open("/etc/openafs/CellServDB", "r", encoding="iso8859_1"):
        line = str(line.rstrip())
        if line == "":
            continue
        comment_ix = line.find("#")
        if comment_ix == 0:
            continue
        comment = ""
        if comment_ix > 0:
            comment = line[comment_ix + 1:].lstrip()
            line = line[:comment_ix].rstrip()
        if line[0] == ">":
            # New cell name
            if line[1:].startswith(prefix):
                if line[1:] not in cells:
                    cells.append(line[1:])
    return cells

###############################################################################
#
# Expand the name from a string list
#
###############################################################################
def expand_from_stringlist(comp_words, comp_cword, names):
    reply = ""
    for i in names:
        if i.startswith(comp_words[comp_cword]):
            reply += " " + i
    output(reply.lstrip(), "\n")
    sys.exit(0)

def main():
    if len(sys.argv) < 3:
        log("Insufficient arguments\n")
        sys.exit(2)

    # The word we're trying to expand
    comp_cword = int(sys.argv[1])

    # The words so far on the command line
    comp_words = sys.argv[2:]

    log(comp_cword, " ", comp_words, "\n")

    # Determine the command actually being run
    cmdset = comp_words[0]
    s = cmdset.rfind("/")
    if s != -1:
        cmdset = cmdset[s + 1:]
    del s

    # If we're starting from the "afs" program, we need to select the command set
    cmdsets = afs.commands.get_command_sets()
    #log("Command sets ", cmdsets, "\n")
    if cmdset == "afs":
        set_program_name("afs")
        if comp_cword == 1:
            expand_from_stringlist(comp_words, comp_cword, cmdsets)

        if len(sys.argv) < 5:
            log("Insufficient arguments\n")
            sys.exit(2)

        # Drop the "afs" element of the list
        comp_words = sys.argv[3:]
        comp_cword -= 1
        cmdset = comp_words[0]
    else:
        set_program_name(cmdset)

    # The command set must be one we know
    if cmdset not in cmdsets:
        error("Unknown command set '", cmdset, "'\n")
        sys.exit(1)

    cmdsetmod = afs.commands.import_command_set(cmdset)
    commands = cmdsetmod.get_command_list()
    commands.append("help")
    commands.append("apropos")
    #log("Commands ", commands, "\n")
    if comp_cword == 1:
        expand_from_stringlist(comp_words, comp_cword, commands)
    cmd = comp_words[1]

    # See if the command is in the set
    found = False
    for i in commands:
        if i == cmd:
            found = cmd
            break
        if i.startswith(cmd):
            if found:
                error("Command '" + cmd + "' is ambiguous\n")
                sys.exit(1)
            found = i
    if not found:
        error("Unknown Command '" + cmd + "'\n")
        sys.exit(1)
    cmd = found

    # Load the command
    if cmd == "help":
        command = __import__("afs.help", globals(), locals(), ['*'])
    elif cmd == "apropos":
        command = __import__("afs.apropos", globals(), locals(), ['*'])
    else:
        command = cmdsetmod.get_command(cmd)
        # If it's an alias, then switch to the real module
        if hasattr(command, "alias"):
            cmd = command.alias
            command = cmdsetmod.get_command(cmd)

    # Find the command's argument description
    arglist = command.command_arguments

    if hasattr(command, "cant_combine_arguments"):
        cant_combine_arguments = command.cant_combine_arguments
    else:
        cant_combine_arguments = {}

    # Discard the first two words of the nascent command line
    comp_words = comp_words[2:]
    comp_cword -= 2

    # Ignore any arguments after the one being expanded
    if comp_cword < len(comp_words) - 1:
        comp_words = comp_words[0:comp_cword + 1]

    # Determine a list of canonicalised flag names and initialise an array to
    # keep track of the non-flag argument types.
    #
    # An argument beginning with a dash that directly follows on from a flag
    # that takes an argument is assumed to be an argument, not a flag.
    canon_flags = []
    word_types = []
    additional_args = []
    skip_flag = False
    for i in range(0, len(comp_words)):
        word = comp_words[i]
        if word.startswith("-") and not skip_flag:
            switch = word[1:]
            match = None
            for j in arglist:
                if j[0] == switch:
                    match = j
                    break
                if j[0].startswith(switch):
                    if match:
                        # Ambiguous
                        match = None
                        break
                    match = j
            if match:
                log("CANON ", switch, "\n")
                canon_flags.append(match)
                if match[2] != "fn":
                    skip_flag = True
            else:
                canon_flags.append(None)
            word_types.append(None)
            del j, switch, match
        else:
            canon_flags.append(None)
            word_types.append(None)
            skip_flag = False
        additional_args.append(False)
        del word
    del i, skip_flag

    # We need to eliminate any arguments that have already been used
    argnames = []
    for i in arglist:
        argnames.append(i[0])
    del i

    log("ARGNAMES 0 ", argnames, "\n")

    # Firstly, we try to eliminate required arguments by position where the
    # flag is implicit
    pos = 0
    for arg in arglist:
        if pos >= len(comp_words):
            break
        word = comp_words[pos]
        if word.startswith("-"):
            break
        spec = arg[2]
        if spec[0] != "r":
            break

        # We have a required argument.  If the first word of this argument is
        # currently being expanded and is blank, then we stick the flag in
        # first.
        if word == "" and pos == comp_cword:
            output("-", arg[0], "\n")
            sys.exit(0)

        word_types[pos] = arg
        argnames.remove(arg[0])
        pos += 1
        if spec[1] == "s":
            continue
        while pos < len(comp_words):
            word = comp_words[pos]
            if word.startswith("-"):
                break
            word_types[pos] = arg
            additional_args[pos] = True
            pos += 1
        break
    del arg, pos

    log("ARGNAMES 1 ", argnames, "\n")

    # Secondly, eliminate flags by name where unambiguous
    for i in canon_flags:
        if i and i[0] in argnames:
            argnames.remove(i[0])
    del i

    log("ARGNAMES 2 ", argnames, "\n")

    # Work out the types of any optional arguments
    last_flag = None
    additional_arg = False
    for i in range(0, len(comp_words)):
        if canon_flags[i]:
            switch = canon_flags[i]
            if switch[2] != "fn":
                last_flag = switch
            else:
                last_flag = None
            additional_arg = False
        elif last_flag:
            word_types[i] = last_flag
            additional_args[i] = additional_arg
            if last_flag[2][1] == "s":
                last_flag = None
            else:
                additional_arg = True
    del i, last_flag, additional_arg

    log("TYPES [")
    for i in range(0, len(comp_words)):
        if canon_flags[i]:
            log(" -", canon_flags[i][0])
        elif word_types[i] == "-":
            log(" -?")
        elif word_types[i]:
            log(" ", word_types[i][3])
        else :
            log(" ??")
    del i
    log(" ]\n")

    # Try to determine how to deal with the word being expanded
    word = comp_words[comp_cword]
    word_type = word_types[comp_cword]
    canon = canon_flags[comp_cword]
    additional_arg = additional_args[comp_cword]
    log("WORD \"", word, "\"\n")
    log("WORD_TYPE ", word_type, "\n")
    log("CANON ", canon, "\n")

    # Expand unambiguous flags fully
    if canon:
        log("*** GEN CANON ", canon, "\n")
        output("-", canon[0], "\n")
        sys.exit(0)

    next_required = None
    for arg in arglist:
        if arg[2][0] == "r":
            if arg[0] in argnames:
                next_required = arg
                break

    # Insert a required flag now if there is one and there is no mandatory
    # argument to the previous flag
    if (word_type == None or word == "-" and additional_arg == True) and next_required:
        log("*** GEN REQFLAG ", next_required[0], "\n")
        output("-", next_required[0], "\n")
        sys.exit(0)
            
    # Work out what type this argument will be if it's not a flag and instruct
    # the parent to run compgen
    special = ""
    if word_type != None:
        if word_type[1] == get_cell:
           special = "@CELL@"
        elif (word_type[1] == get_bosserver or
              word_type[1] == get_fileserver or
              word_type[1] == get_volserver or
              word_type[1] == get_vlservers or
              word_type[1] == get_machine_name or
              word_type[1] == get_machine_names):
            special = "@HOSTNAME@"
        elif word_type[1] == get_volume_name or word_type[1] == get_volume_names:
            special = "@VOLNAME@"
        elif word_type[1] == get_partition_id:
            special = "@PARTID@"
        elif (word_type[1] == get_path_name or word_type[1] == get_path_names or
              word_type[1] == get_file_name or word_type[1] == get_file_names):
            special = "@FILE@"
        else:
            special = "@OTHER@"
    log("SPECIAL ", special, "\n")
            
    # Expand an argument that can't be a flag
    if word_type != None and additional_arg == False:
        log("*** GEN NONFLAG ", word_type[0], "\n")
        if special == "@CELL@":
            space = ""
            for i in expand_cell_list(word):
                output(space, i)
                space = " "
            output("\n")
        else:
            output(special, "\n")
        sys.exit(0)

    # Work out a list of what options could go next
    next_opts = ""
    if len(word) == 0 or word.startswith("-"):
        next_opts = next_required
        if next_opts == None:
            next_opts = ""
            for i in argnames:
                if i.startswith(word[1:]):
                    if next_opts == "":
                        next_opts = "-"
                    else:
                        next_opts += " -"
                    next_opts += i
    log("NEXT OPTS ", next_opts, "\n")

    if next_opts != "":
        # If the next word has to be a flag of some sort, display a list thereof
        if word_type == None or additional_arg == True and word.startswith("-"):
            log("*** GEN OPTIONS ", next_opts, "\n")
            output(next_opts)
            output("\n")
            sys.exit(0)

    # The next word can be a flag or an additional argument
    if additional_arg == True:
        log("*** GEN ADDARG ", special, "\n")
        if special == "@CELL@":
            space = ""
            for i in expand_cell_list(word):
                output(space, i)
                space = " "
            output("\n")
        else:
            output(special, "\n")
        sys.exit(0)
            
    # Nothing left
    log("*** GEN NOTHING\n")
    output("\n")
    sys.exit(0)

main()
