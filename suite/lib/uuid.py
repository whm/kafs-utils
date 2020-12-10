#
# AFS Volume management toolkit: UUID handling
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

def uuid2str(uuid):
    """Convert an afsUUID-class object into a UUID string"""
    s = "{:08x}-{:04x}-{:04x}-{:02x}-{:02x}-".format(uuid.time_low,
                                                     uuid.time_mid,
                                                     uuid.time_hi_and_version,
                                                     uuid.clock_seq_hi_and_reserved,
                                                     uuid.clock_seq_low)
    for i in range(0, 6):
        s += "{:02x}".format(uuid.node[i])
    return s

def str2uuid(s):
    """Convert a UUID string into an afsUUID-class object"""
    if (len(s) != 32 + 5 or
        s[ 8] != "-" or
        s[13] != "-" or
        s[18] != "-" or
        s[21] != "-" or
        s[24] != "-"):
        raise AFSArgumentError("Invalid UUID format")

    from kafs import afsUUID
    uuid = afsUUID()
    uuid.time_low                       = int(s[0:8], 16)
    uuid.time_mid                       = int(s[9:13], 16)
    uuid.time_hi_and_version            = int(s[14:18], 16)
    uuid.clock_seq_hi_and_reserved      = int(s[19:21], 16)
    uuid.clock_seq_low                  = int(s[22:24], 16)
    uuid.node[0]                        = int(s[25:27], 16)
    uuid.node[1]                        = int(s[27:29], 16)
    uuid.node[2]                        = int(s[29:31], 16)
    uuid.node[3]                        = int(s[31:33], 16)
    uuid.node[4]                        = int(s[33:35], 16)
    uuid.node[5]                        = int(s[35:37], 16)
    return uuid
