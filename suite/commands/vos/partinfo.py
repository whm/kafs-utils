#
# AFS Volume management toolkit: Report information on partitions
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
import afs.lib.partition as partition
import kafs

help = "Report the available and total space on a partition"

command_arguments = [
    [ "server",         get_volserver,          "rs",         "<machine name>" ],
    [ "partition",      get_partition_id,       "os",         "<partition name>" ],
    [ "summary",        get_dummy,              "fn" ],
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
]

description = r"""
Report the available and total space on a partition
"""

def main(params):
    cell = params["cell"]
    vol_conn = cell.open_volume_server(params["server"], params)

    if "partition" not in params:
        ret = kafs.VOLSER_ListPartitions(vol_conn)
        partitions = ret.partIDs.partIds
    else:
        partitions = [ params["partition"] ]

    for i in partitions:
        if i != 0xffffffff:
            partname = partition.id2part(i)

            try:
                ret = kafs.VOLSER_PartitionInfo(vol_conn, partname)
                part = ret.partition

                output("Free space on partition ", part.name, ": ",
                       part.free, " K blocks out of total ", part.totalUsable, "\n")
            except kafs.AbortVOLSERILLEGAL_PARTITION:
                error("partition ", partname, " does not exist on the server\n")
