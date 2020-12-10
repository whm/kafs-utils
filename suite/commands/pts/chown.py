#
# AFS Server management toolkit: Change ownership of an entry
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

help = "Change the owner of a Protection Database entry"

command_arguments = [
    [ "name",           get_string,             "rs",         "<group name>" ],
    [ "owner",          get_string,             "rs",         "<new owner>" ],
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
    "oldname"           : kafs.PR_MAXNAMELEN,
    "owner"             : kafs.PR_MAXNAMELEN,
}

description = r"""
Change the owner of a Protection Database entry
"""

def main(params):
    exitcode = 0
    cell = params["cell"]
    prcache = cell.get_prcache(params)

    prcache.precache_name_or_id(params["name"])
    prcache.precache_name_or_id(params["owner"])

    gid = prcache.name_or_id_to_id(params["name"])
    owner = prcache.name_or_id_to_id(params["owner"])
    if gid == None or owner == None or owner == 0:
        error("User or group doesn't exist ; unable to change owner of ",
              params["name"], " to ", params["owner"], "\n")
        return
    group_name = prcache.id_to_name(gid)

    try:
        verbose("Chowning ", gid, " to ", owner, "\n")
        ret = cell.call_pt_server(params, kafs.PR_ChangeEntry, gid, "", owner, 0)
        # The name is changed by the act of chowning (group names are prefixed
        # by the owner user name and a colon, and the prefix gets changed)
        prcache.evict_id(gid)
        prcache.evict_groups()
    except kafs.AbortPRNOENT:
        error("User or group doesn't exist ; unable to change name of ",
              prcache.id_to_name(gid), " to ", params["owner"], "\n")
    except kafs.AbortPRPERM:
        error("Permission denied ; unable to change name of ",
              prcache.id_to_name(gid), " to ", prcache.id_to_name(owner), "\n")

