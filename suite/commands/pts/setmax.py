#
# AFS Server management toolkit: Set maximum user and group IDs
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

from afs.argparse import *
from afs.lib.output import *
import kafs
import sys

help = "Set the value of the max group id or max user id counter"

command_arguments = [
    [ "group",          get_gid,                "os",         "<group max>" ],
    [ "user",           get_uid,                "os",         "<user max>" ],
    [ "cell",           get_cell,               "os",         "<cell name>" ],
    [ "noauth",         get_auth,               "fn" ],
    [ "localauth",      get_auth,               "fn" ],
    [ "verbose",        get_verbose,            "fn" ],
    [ "encrypt",        get_dummy,              "fn" ],
    [ "force",          get_dummy,              "fn" ],
]

cant_combine_arguments = [
    ( "cell",           "localauth" ),
    ( "noauth",         "localauth" ),
]

description = r"""
Set the value of the max group id or max user id counter
"""

def main(params):
    cell = params["cell"]

    if "user" in params:
        try:
            uid = params["user"]
            verbose("Set max UID to ", uid, "\n")
            ret = cell.call_pt_server(params, kafs.PR_SetMax, uid, kafs.PRUSER)
        except kafs.AbortPRPERM:
            error("Permission denied ; unable to change max user id\n")
            if "force" not in params:
                return

    if "group" in params:
        try:
            gid = params["group"]
            verbose("Set max GID to ", gid, "\n")
            ret = cell.call_pt_server(params, kafs.PR_SetMax, gid, kafs.PRGRP)
        except kafs.AbortPRPERM:
            error("Permission denied ; unable to change max group id\n")
            

