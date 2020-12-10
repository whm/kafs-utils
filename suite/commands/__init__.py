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
import stat

def get_command_sets():
    sets = []
    for p in __path__:
        for fn in os.listdir(p):
            if fn[0] == "_" or fn[-1] == "~" or not stat.S_ISDIR(os.stat(p + "/" + fn).st_mode):
                continue
            sets.append(fn)
    return sets

def import_command_set(cmdset):
    return __import__(__name__ + '.' + cmdset, globals(), locals(), ['*'])

