#
# AFS Volume management toolkit: Command output, error message production and debugging
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

import sys

program_name = "<unset>"
verbosity = False
debugging_level = 0
exitcode = 0

def __init__():
    print("OUTPUT")

def set_program_name(name):
    global program_name
    program_name = name

def set_verbosity():
    global verbosity
    verbosity = True

def set_debugging_level(level):
    global verbosity
    global debugging_level
    if level > 0:
        verbosity = True
    debugging_level = level

def output(*args):
    for i in args:
        sys.stdout.write(str(i))

def output_raw(*args):
    for i in args:
        sys.stdout.buffer.write(i)

def output_flush():
    sys.stdout.flush()

def outputf(formatstr, *args):
    sys.stdout.write(formatstr.format(*args))

def error(*args):
    global exitcode
    sys.stderr.write(program_name + ": ")
    for i in args:
        sys.stderr.write(str(i))
    exitcode = 1

def errorf(formatstr, *args):
    error(formatstr.format(*args))

def get_exitcode():
    global exitcode
    return exitcode

def set_exitcode(n):
    global exitcode
    exitcode = n

def verbose(*args, **kwargs):
    global verbosity
    if verbosity:
        sys.stdout.write("** ")
        for i in args:
            sys.stdout.write(str(i))

def verbosef(formatstr, *args):
    global verbosity
    if verbosity:
        sys.stdout.write("** ")
        sys.stdout.write(formatstr.format(*args))

def verbose_cont(*args, **kwargs):
    global verbosity
    if verbosity:
        for i in args:
            sys.stdout.write(str(i))
