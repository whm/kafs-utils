#
# AFS Server management toolkit: Add a user to a group
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

help = "Add a user or machine to a Protection Database group"

command_arguments = [
    [ "user",           get_strings,            "rm",         "<user name>+" ],
    [ "group",          get_strings,            "rm",         "<group name>+" ],
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
Add a user or machine to a Protection Database group
"""

def main(params):
    cell = params["cell"]
    prcache = cell.get_prcache(params)

    ignored = ""
    if "force" in params:
        ignored = " (ignored)"

    for user in params["user"]:
        prcache.precache_name_or_id(user)

    for group in params["group"]:
        prcache.precache_name_or_id(group)

    for user in params["user"]:
        uid = prcache.name_or_id_to_id(user)

        for group in params["group"]:
            gid = prcache.name_or_id_to_id(group)

            if uid == None or gid == None:
                error("User or group doesn't exist ; unable to add user ", user, " to group ", group, ignored, "\n")
                if "force" not in params:
                    return
                else:
                    continue

            try:
                ret = cell.call_pt_server(params, kafs.PR_AddToGroup, uid, gid)
                prcache.evict_groups()
            except kafs.AbortPRIDEXIST:
                error("Entry for id already exists ; unable to add user ", user, " to group ", group, ignored, "\n")
                if "force" not in params:
                    return
