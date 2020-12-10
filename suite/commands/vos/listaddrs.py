#
# AFS Volume management toolkit: Volume location database list
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
from afs.lib.uuid import uuid2str
import afs.lib.addrcache as addrcache
import kafs

help = "Display all VLDB entries"

command_arguments = [
    [ "uuid",           get_uuid,               "os",         "<uuid of server>" ],
    [ "host",           get_fileserver,         "os",         "<address of host>" ],
    [ "printuuid",      get_dummy,              "fn" ],
    [ "cell",           get_cell,               "os",         "<cell name>" ],
    [ "noauth",         get_auth,               "fn" ],
    [ "localauth",      get_auth,               "fn" ],
    [ "verbose",        get_verbose,            "fn" ],
    [ "encrypt",        get_dummy,              "fn" ],
    [ "noresolve",      get_dummy,              "fn" ],
]

cant_combine_arguments = [
    ( "cell",           "localauth" ),
    ( "noauth",         "localauth" ),
    ( "uuid",           "host" ),
]

description = r"""
Display all VLDB entries
"""

def list_one(params, vl_conn, attributes):
    ret = kafs.VL_GetAddrsU(vl_conn, attributes)
    if "printuuid" in params:
        output("UUID: ", uuid2str(ret.uuidp1), "\n")

    addrs = ret.blkaddrs
    for a in addrs:
        output(addrcache.resolve(params, a), "\n")
    if "printuuid" in params:
        output("\n")

def list_all(params, vl_conn):
    ret = kafs.VL_GetAddrs(vl_conn, 0, 0)
    verbose("nentries ", ret.nentries, "\n")

    found = ret.nentries
    limit = ret.nentries * 2
    attributes = kafs.ListAddrByAttributes()
    attributes.Mask |= kafs.VLADDR_INDEX
    for index in range(1, 65536):
        verbose("Look up", index)

        attributes.index = index
        try:
            list_one(params, vl_conn, attributes)
            found -= 1
        except kafs.AbortVL_NOENT:
            continue
        except kafs.AbortVL_INDEXERANGE:
            break
        if found <= 0:
            break

def main(params):
    cell = params["cell"]
    vl_conn = cell.open_vl_server(params)

    if "uuid" not in params and "host" not in params:
        return list_all(params, vl_conn)

    attributes = kafs.ListAddrByAttributes()
    attributes.Mask = 0
    if "uuid" in params:
        attributes.Mask |= kafs.VLADDR_UUID
        attributes.uuid = params["uuid"]
    if "host" in params:
        attributes.Mask |= kafs.VLADDR_IPADDR
        attributes.ipaddr = params["host"].integer_addr()

    list_one(params, vl_conn, attributes)
