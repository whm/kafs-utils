#
# AFS Server management toolkit: Delete a protection db record
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

help = "Delete a Protection Database entry"

command_arguments = [
    [ "nameorid",       get_strings,            "rm",         "<user name>+" ],
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
    "nameorid"          : kafs.PR_MAXNAMELEN,
}

description = r"""
Delete a Protection Database entry
"""

def main(params):
    cell = params["cell"]
    prcache = cell.get_prcache(params)

    for name in params["nameorid"]:
        prcache.precache_name_or_id(name)

    for name in params["nameorid"]:
        uid = prcache.name_or_id_to_id(name)
        if uid == None:
            error("User or group doesn't exist so couldn't look up id for " + name + "\n")
            if "force" not in params:
                break
            continue

        try:
            verbose("Deleting user ", uid, " (", prcache.id_to_name(uid), ")\n")
            ret = cell.call_pt_server(params, kafs.PR_Delete, uid)
            prcache.evict_id(uid)
            prcache.evict_groups()
        except kafs.AbortPRNOENT:
            error("User or group doesn't exist deleting ", name, " (id ", uid, ")\n")
            if "force" not in params:
                break
        except kafs.AbortPRPERM:
            error("Permission denied deleting ", name, " (id: ", uid, ")\n")
            if "force" not in params:
                break
