#
# AFS Server management toolkit: List protection DB entries
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

help = "Display all users or groups in the Protection Database"

command_arguments = [
    [ "users",          get_dummy,              "fn" ],
    [ "groups",         get_dummy,              "fn" ],
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
Display all users or groups in the Protection Database
"""

def main(params):
    cell = params["cell"]

    if "users" in params and "groups" in params:
        flags = kafs.PRWANTUSERS | kafs.PRWANTGROUPS
    elif "groups" in params:
        flags = kafs.PRWANTGROUPS
    else:
        flags = kafs.PRWANTUSERS

    ret = cell.call_pt_server(params,  kafs.PR_ListEntries, flags, 0)

    output("Name                          ID   Owner Creator\n")
    for i in ret.entries:
        outputf("{:24s} {:7d} {:7d} {:7d}\n", i.name, i.id, i.owner, i.creator)
