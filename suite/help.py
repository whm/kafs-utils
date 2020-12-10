#
# AFS Server management toolkit: Command line help
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

from afs.exception import AFSException
from afs.argparse import *
from afs.lib.output import *

help = "Get help on commands"

command_arguments = [
    [ "topic",          get_strings,            "om",         "<help string>+" ],
    [ "help",           get_dummy,              "fn" ],
]

description = r"""
Display the server encryption keys from the KeyFile file
"""

###############################################################################
#
# Basic command list
#
###############################################################################
def display_command_list(prog, cmdsetmod, commands):
    output(prog, ": Commands are:\n")
    for i in sorted(commands):
        if i == "help":
            desc = "Get help on commands"
        elif i == "apropos":
            desc = "Search by help text"
        else:
            command = cmdsetmod.get_command(i)
            if hasattr(command, "alias"):
                desc = "Alias for '" + command.alias + "'"
            elif not hasattr(command, "help"):
                desc = "** no help **"
            else:
                desc = command.help
        outputf("{:<15s} {:s}\n", i, desc)

###############################################################################
#
# Print a topic
#
###############################################################################
def display_command_arguments(args):
    for arg in args:
        if arg[2] == "fn" or arg[2][0] == "o":
            opt_o = "["
            opt_c = "]"
        else:
            opt_o = ""
            opt_c = ""
        output(" ", opt_o, "-", arg[0])
        if arg[2] != "fn":
            output(" ", arg[3])
        output(opt_c)
    output(" [-help]")

def display_aliases(prog, cmdsetmod, commands, topic):
    aliases = []
    for i in commands:
        if i == "help" or i == "apropos":
            continue
        command = cmdsetmod.get_command(i)
        if hasattr(command, "alias"):
            if command.alias == topic:
                aliases.append(i)
    if aliases:
        output("aliases: ", aliases[0])
        if len(aliases) > 1:
            for i in range(1, len(aliases)):
                output(", ", aliases[i])
        output("\n")

def display_help_on_topics(prog, cmdsetmod, commands, topics):
    for topic in topics:
        if topic == "help":
            output("bos help: ", help, "\n")
            display_command_arguments(command_arguments)
            continue

        if topic == "apropos":
            command = __import__("afs.apropos", globals(), locals(), ['*'])
            output("bos apropos: ", command.help, "\n")
            display_command_arguments(command.command_arguments)
            continue

        # See if the command is in the set
        try:
            found = False
            for i in commands:
                if i == topic:
                    found = topic
                    break
                if i.startswith(topic):
                    if found:
                         raise RuntimeError("Ambiguous topic '" + topic + "'; use 'apropos' to list\n")
                    found = i
            if not found:
                raise RuntimeError("Unknown topic '" + topic + "'\n")
            topic = found
        except RuntimeError as e:
            error(e)
            set_exitcode(5)
            continue

        # Load the command module
        command = cmdsetmod.get_command(topic)

        # If it's an alias, then switch to the real module
        if hasattr(command, "alias"):
            alias = " (alias for " + command.alias + ")"
            command = cmdsetmod.get_command(command.alias)
        else:
            alias = ""

        output(prog, " ", topic, ": ", command.help, alias, "\n")
        display_aliases(prog, cmdsetmod, commands, topic)
        output("Usage: ", prog, " ", topic)
        display_command_arguments(command.command_arguments)
        output("\n")
        desc = command.description
        if desc[0] == "\n":
            desc = desc[1:]
        output(desc)

###############################################################################
#
#
#
###############################################################################
def main(params):
    prog = params["_prog"]
    cmdsetmod = params["_cmdsetmod"]
    commands = params["_commands"]

    if "help" in params:
        display_help_on_topics(prog, cmdsetmod, commands, [ "help" ])
    elif "topic" in params:
        display_help_on_topics(prog, cmdsetmod, commands, params["topic"])
    else:
        display_command_list(prog, cmdsetmod, commands)

###############################################################################
#
# Handle the -help flag being applied to a command
#
###############################################################################
def helpflag(prog, cmdsetmod, topic, command):
    output("Usage: ", prog, " ", topic)
    display_command_arguments(command.command_arguments)
    output("\n")
