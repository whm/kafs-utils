#
# AFS Toolset command switcher 
# -*- coding: utf-8 -*-
#

__copyright__ = """
Copyright (C) 2014 Red Hat, Inc. All Rights Reserved.
Written by David Howells (dhowells@redhat.com)

Derived from StGIT:

Copyright (C) 2005, Catalin Marinas <catalin.marinas@gmail.com>

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

import sys, os, traceback

import afs.commands
from afs.lib.output import *
from exception import AFSArgumentError, AFSHelpFlag

###############################################################################
#
# The main function (command dispatcher)
#
###############################################################################
def _main():
    """The main function
    """
    global prog

    prog = os.path.basename(sys.argv[0])
    set_program_name(prog)

    cmdsets = afs.commands.get_command_sets()
    #print("CMDSETS:", cmdsets)

    if prog == "afs":
        if len(sys.argv) < 3:
            print('usage: {:s} <cmdset> <command>'.format(prog), file=sys.stderr)
            print('  Try "{:s} help" for a list of supported command sets'.format(prog), file=sys.stderr)
            sys.exit(2)
        cmdset = sys.argv[1]
        cmd = sys.argv[2]
        del sys.argv[1:3]
    else:
        if len(sys.argv) < 2:
            print('usage: {:s} <command>'.format(prog), file=sys.stderr)
            print('  Try "{:s} help" for a list of supported commands'.format(prog), file=sys.stderr)
            sys.exit(2)
        cmdset = prog
        cmd = sys.argv[1]
        del sys.argv[1:2]

    if cmdset not in cmdsets:
        raise RuntimeError("Unsupported command set '" + cmdset + "'")

    if cmd in ['-v', '--version', 'version']:
        from afs.version import version
        print('AFS Toolkit %s' % version)
        print('Python version %s' % sys.version)
        sys.exit(0)

    if cmd in ['copyright']:
        print(__copyright__)
        sys.exit(0)

    # Import the command set
    cmdsetmod = afs.commands.import_command_set(cmdset)
    commands = cmdsetmod.get_command_list()
    commands.append("help")
    commands.append("apropos")

    # See if the command is in the set
    found = False
    for i in commands:
        if i == cmd:
            found = cmd
            break
        if i.startswith(cmd):
            if found:
                raise RuntimeError("Command '" + cmd + "' is ambiguous")
            found = i
    if not found:
        raise RuntimeError("Command '" + cmd + "' is unknown")
    cmd = found

    # Rebuild the command line arguments
    if prog == "afs":
        sys.argv[0] += ' {:s} {:s}'.format(cmdset, cmd)
    else:
        sys.argv[0] += ' {:s}'.format(cmd)

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

    if hasattr(command, "cant_combine_arguments"):
        cant_combine_arguments = command.cant_combine_arguments
    else:
        cant_combine_arguments = {}

    if hasattr(command, "argument_size_limits"):
        argument_size_limits = command.argument_size_limits
    else:
        argument_size_limits = {}

    # Parse the parameters
    try:
        params = afs.argparse.parse_arguments(sys.argv[1:],
                                              command.command_arguments,
                                              argument_size_limits,
                                              cant_combine_arguments)
    except AFSArgumentError as e:
        print(prog + ":", e, file=sys.stderr)
        sys.exit(2)
    except AFSHelpFlag:
        helper = __import__("afs.help", globals(), locals(), ['*'])
        helper.helpflag(prog, cmdsetmod, cmd, command)
        sys.exit(0)

    # Stick in the default cell if there isn't one
    if "cell" not in params:
        from afs.lib.cell import cell
        params["cell"] = cell()

    params["_prog"] = prog
    params["_cmdsetmod"] = cmdsetmod
    params["_commands"] = commands

    # These modules are only used from this point onwards and do not
    # need to be imported earlier
    from afs.exception import AFSException

    try:
        set_debugging_level(int(os.environ.get('AFS_DEBUG_LEVEL', 0)))
    except ValueError:
        print('Invalid AFS_DEBUG_LEVEL environment variable', file=sys.stderr)
        sys.exit(2)

    try:
        command.main(params)
        ret = get_exitcode()
    except (AFSException, IOError) as err:
        print(prog + ":", str(err), file=sys.stderr)
        if debugging_level > 0:
            traceback.print_exc()
        ret = 1
    except AFSArgumentError as e:
        print(prog + ":", e, file=sys.stderr)
        ret = 2
    except KeyboardInterrupt:
        ret = 1
    except SystemExit:
        ret = 0
    except:
        print('Unhandled exception:', file=sys.stderr)
        traceback.print_exc()
        ret = 3

    sys.exit(ret or 0)

def main():
    try:
        _main()
    finally:
        pass
