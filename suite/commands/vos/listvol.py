#
# AFS Volume management toolkit: Volume location database info
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
from afs.lib.partition import id2part
from afs.lib.voldisplay import *
import kafs
import sys

help = "Display information from a volume header"

command_arguments = [
    [ "server",         get_volserver,          "rs",         "<machine name>" ],
    [ "partition",      get_partition_id,       "os",         "<partition name>" ],
    [ "fast",           get_dummy,              "fn" ],
    [ "long",           get_dummy,              "fn" ],
    [ "quiet",          get_dummy,              "fn" ],
    [ "extended",       get_dummy,              "fn" ],
    [ "format",         get_dummy,              "fn" ],
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
    ( "fast",           "extended" ),
]

description = r"""
Display information from a volume header
"""

def display_fast(params, vol):
    output(vol.volid, "\n")

def display_extended(params, vol):
    display_vol_information(params, vol)
    display_vol_statistics(params, vol)

def display_format_normal(params, vol):
    display_vol_mp_information(params, vol)
    output("END_OF_ENTRY\n")

reads_labels = [ "reads_same_net", "reads_same_net_auth",
                 "reads_diff_net", "reads_diff_net_auth" ]

writes_labels = [ "writes_same_net", "writes_same_net_auth",
                  "writes_diff_net", "writes_diff_net_auth" ]

def display_format_extended(params, vol):
    if vol.status == kafs.VBUSY:
        output("VOLUME_BUSY\t{:d}\n", vol.volid)
        return
    elif vol.status != kafs.VOK:
        output("COULD_NOT_ATTACH_VOLUME\t{:d}\n", vol.volid)
        return

    display_vol_mp_basic_information(params, vol)

    for i in range(0, 4):
        outputf("{:s}\t{:8d}\n", reads_labels[i], vol.stat_reads[i])
    for i in range(0, 4):
        outputf("{:s}\t{:8d}\n", writes_labels[i], vol.stat_writes[i])
    for i in range(0, 6):
        outputf("file_same_author_idx_{:d}\t{:8d}\n", i, vol.stat_fileSameAuthor[i])
        outputf("file_diff_author_idx_{:d}\t{:8d}\n", i, vol.stat_fileDiffAuthor[i])
        outputf("dir_same_author_idx_{:d}\t{:8d}\n", i, vol.stat_dirSameAuthor[i])
        outputf("dir_dif_author_idx_{:d}\t{:8d}\n", i, vol.stat_dirDiffAuthor[i])

    output("END_OF_ENTRY")

###############################################################################
#
# Display the records for a single partition in the appropriate format
#
###############################################################################
def display_one_partition(params, vol_conn, partition):
    if "extended" in params:
        ret = kafs.VOLSER_XListVolumes(vol_conn, partition, 1)
    else:
        ret = kafs.VOLSER_ListVolumes(vol_conn, partition, 1)

    params["_partname"] = partname = id2part(partition)
    if "quiet" not in params:
        output("Total number of volumes on server ", params["server"], " partition ",
               partname, ": ", len(ret.resultEntries), "\n")

    display_func = display_vol_oneline_summary
    if "fast" in params:
        display_func = display_fast
    elif "format" in params and "extended" in params:
        display_func = display_format_extended
    elif "format" in params:
        display_func = display_format_normal
    elif "extended" in params:
        display_func = display_extended
    elif "long" in params:
        display_func = display_vol_information

    n_online = 0
    n_offline = 0
    n_busy = 0
    volumes = ret.resultEntries
    volumes.sort(key=lambda vol: vol.name)
    for vol in volumes:
        if vol.inUse:
            n_online += 1
        if vol.status == kafs.VBUSY:
            n_busy += 1
        display_func(params, vol)

    if "quiet" not in params:
        output()
        if "fast" not in params and "format" not in params:
            output("Total volumes onLine ", n_online, "; Total volumes offLine ", n_offline,
                   "; Total busy ", n_busy, "\n")
            output()
        elif "format" in params and "extended" in params:
            output("VOLUMES_ONLINE  ", n_online, "\n")
            output("VOLUMES_OFFLINE ", n_offline, "\n")
            output("VOLUMES_BUSY    ", n_busy, "\n")

###############################################################################
#
#
#
###############################################################################
def main(params):
    cell = params["cell"]
    vol_conn = cell.open_volume_server(params["server"], params)

    if "partition" in params:
        try:
            display_one_partition(params, vol_conn, params["partition"])
        except kafs.AbortVOLSERILLEGAL_PARTITION:
            error("vos : partition ", params["raw.partition"][0],
                  " does not exist on the server")
    else:
        ret = kafs.VOLSER_XListPartitions(vol_conn)
        for p in ret.ent:
            one_partition(params, vol_conn, p)
