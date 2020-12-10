# -*- coding: utf-8 -*-

__copyright__ = """
Copyright (C) 2014 Red Hat, Inc. All Rights Reserved.
Written by David Howells (dhowells@redhat.com)

Derived from StGIT:

Copyright (C) 2005, Catalin Marinas <catalin.marinas@gmail.com>
Copyright (C) 2008, Karl Hasselström <kha@treskal.com>

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

import os

def get_command(mod):
    """Import and return the given command module."""
    return __import__(__name__ + '.' + mod, globals(), locals(), ['*'])

def get_command_list():
    commands = []
    for p in __path__:
        for fn in os.listdir(p):
            if not fn.startswith("_") and fn.endswith('.py'):
                commands.append(fn[:-3])
    return commands

def py_commands(commands, f):
    f.write('command_list = {\n')
    for key, val in sorted(commands.iteritems()):
        f.write('    %r: %r,\n' % (key, val))
    f.write('    }\n')

#def _command_list(commands):
#    for cmd, (mod, help) in commands.iteritems():

def pretty_command_list(commands, f):
    cmd_len = max(len(cmd) for cmd in commands.iterkeys())
    for cmd, help in cmds:
        f.write('  %*s  %s\n' % (-cmd_len, cmd, help))

def _write_underlined(s, u, f):
    f.write(s + '\n')
    f.write(u*len(s) + '\n')

def asciidoc_command_list(commands, f):
    for cmd, help in commands:
        f.write('linkstgsub:%s[]::\n' % cmd)
        f.write('    %s\n' % help)
    f.write('\n')
