#
# AFS Server management toolkit: Create groups
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

help = "Create an (empty) Protection Database group entry"

command_arguments = [
    [ "name",           get_strings,            "rm",         "<group name>+" ],
    [ "owner",          get_string,             "os"          "<owner of the group>" ],
    [ "id",             get_gids,               "om",         "<id (negated) for the group>+" ],
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

argument_size_limits = {
    "name"              : kafs.PR_MAXNAMELEN,
}

description = r"""
Create an (empty) Protection Database group entry
"""

def main(params):
    exitcode = 0
    cell = params["cell"]
    prcache = cell.get_prcache(params)

    oid = 0
    if "owner" in params:
        oid = prcache.name_or_id_to_id(params["owner"])

    names = params["name"]
    if "id" in params:
        ids = params["id"]
    else:
        ids = []

    for i in range(0, len(names)):
        name = names[i]
        try:
            verbose("Adding group ", name, "\n")
            if i < len(ids):
                new_id = int(ids[i])
                ret = cell.call_pt_server(params, kafs.PR_INewEntry, name, new_id, oid)
            else:
                ret = cell.call_pt_server(params, kafs.PR_NewEntry, name, kafs.PRGRP, oid)
                new_id = ret.id
            output("Group ", name, " has id ", new_id, "\n")
            prcache.evict_name(name)
            prcache.evict_id(new_id)
        except kafs.AbortPREXIST:
            error("Entry for name already exists ; unable to create group ", name, "\n")
            if "force" not in params:
                break
        except kafs.AbortPRIDEXIST:
            error("Entry for id already exists ; unable to create group ", name, " with id ", new_id, "\n")
            if "force" not in params:
                break
    return exitcode
