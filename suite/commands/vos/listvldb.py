#
# AFS Volume management toolkit: Volume location database query
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
from afs.lib.voldisplay import *
import kafs

help = "Query the VLDB"

command_arguments = [
    [ "name",           get_volume_name,        "os",         "<volume name or ID>" ],
    [ "server",         get_fileserver,         "os",         "<machine name>" ],
    [ "partition",      get_partition_id,       "os",         "<partition name>" ],
    [ "locked",         get_dummy,              "fn" ],
    [ "quiet",          get_dummy,              "fn" ],
    [ "nosort",         get_dummy,              "fn" ],
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
    ( "name",           "server" ),
    ( "name",           "partition" ),
    ( "name",           "locked" ),
]

argument_size_limits = {
    "name"              : kafs.VLDB_MAXNAMELEN,
}

description = r"""
Displays a volume's VLDB entry
"""

def print_record(params, vldb):
    """Display a single VLDB record"""
    output(vldb.name, "\n")
    output("   ");
    flags = vldb.serverFlags[0]
    if flags & kafs.VLSF_RWVOL:
        outputf(" RWrite: {:<12d}", vldb.volumeId[0])
    if flags & kafs.VLSF_ROVOL:
        outputf(" ROnly: {:<12d}", vldb.volumeId[1])
    if flags & kafs.VLSF_BACKVOL:
        outputf(" Backup: {:<12d}",vldb.volumeId[2])
    output("\n")
    display_vldb_site_list(params, vldb, "    ")
    output("\n")

def main(params):
    # Get a list of VLDB servers to query
    cell = params["cell"]
    z_conn = cell.open_vl_server(params)
    quiet = "quiet" in params

    if "name" in params:
        ret = kafs.VL_GetEntryByName(z_conn, params["name"])
        vldb = ret.entry
        print_record(params, vldb)
        return

    attributes = kafs.VldbListByAttributes()
    attributes.Mask = 0

    if "server" in params:
        attributes.Mask |= kafs.VLLIST_SERVER
        attributes.server = params["server"].integer_addr()
    if "partition" in params:
        attributes.Mask |= kafs.VLLIST_PARTITION
        attributes.partition = params["partition"]
    if "locked" in params:
        attributes.Mask |= kafs.VLLIST_FLAG
        attributes.flag = kafs.VLOP_MOVE | kafs.VLOP_RELEASE | kafs.VLOP_BACKUP | kafs.VLOP_DELETE | kafs.VLOP_DUMP

    ret = kafs.VL_ListAttributes(z_conn, attributes)
    blkentries = ret.blkentries

    if not quiet and "server" in params:
        output("VLDB entries for server ", params["server"], "\n")

    if "nosort" not in params:
        blkentries.sort(key=lambda vldb: vldb.name)

    for vldb in blkentries:
        print_record(params, vldb)

    if not quiet:
        output("Total entries: ", len(blkentries), "\n")
