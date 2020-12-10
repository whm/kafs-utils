#
# AFS Server management toolkit: Command line help search
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

help = "Search by help text"

command_arguments = [
    [ "topic",          get_string,             "rs",         "<help string>" ],
]

description = r"""
Search by help text
"""

def search_help(prog, cmdsetmod, commands, topic):
    matches = dict()
    for i in commands:
        if i == "help":
            command = __import__("afs.help", globals(), locals(), ['*'])
            if topic in command.help.casefold():
                matches["help"] = command.help
            continue

        if i == "apropos":
            if topic in help.casefold():
                matches["apropos"] = help
            continue

        command = cmdsetmod.get_command(i)
        if hasattr(command, "help"):
            if topic in command.help.casefold():
                matches[i] = command.help
    return matches

###############################################################################
#
#
#
###############################################################################
def main(params):
    matches = search_help(params["_prog"], params["_cmdsetmod"], params["_commands"],
                          params["topic"].casefold())

    if not matches:
        output("Sorry, no commands found\n")
    else:
        for i in sorted(matches.keys()):
            output(i, ": ", matches[i], "\n")
