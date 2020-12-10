#
# AFS Volume management toolkit: Partition name handling
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

from exception import AFSArgumentError

def part2id(name):
    """Convert a partition name or number string into a numeric ID"""
    if name.isnumeric():
        n = int(name)
    else:
        if name.startswith("/vicep"):
            a = name[6:]
        elif name.startswith("vicep"):
            a = name[5:]
        else:
            a = name

        if len(a) == 1 and a >= "a" and a <= "z":
            n = int(a, 36) - 10
        elif (len(a) == 2 and
              a[0] >= "a" and a[0] <= "z" and
              a[1] >= "a" and a[1] <= "z"):
            n = (int(a[0], 36) - 10) * 26 + (int(a[1], 36) - 10)
            n += 26
        else:
            raise AFSArgumentError("Unparseable partition ID '" + name + "'")

    if n < 0 or n > 255:
        raise AFSArgumentError("Partition ID '" + name + "' out of range")
    return n

def id2part(n):
    """Convert a numeric ID into a partition name string"""
    if n < 26:
        return "/vicep{:c}".format(n + 97)
    else:
        n -= 26
        return "/vicep{:c}{:c}".format(n / 26 + 97, n % 26 + 97)
