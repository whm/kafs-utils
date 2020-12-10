#
# AFS Volume management toolkit: Create a R/W volume and associated VLDB entry
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
from afs.exception import AFSException
from afs.lib.output import *
from afs.lib.partition import id2part
from afs.lib.time import *
import kafs

help = "Create a read/write volume and associated VLDB entry"

command_arguments = [
    [ "server",         get_volserver,          "rs",         "<machine name>" ],
    [ "partition",      get_partition_id,       "rs",         "<partition name>" ],
    [ "name",           get_volume_name,        "rs",         "<volume name>" ],
    [ "maxquota",       get_string,             "os",         "<initial quota (KB)>" ],
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
Create a read/write volume and associated VLDB entry
"""

def main(params):
    cell = params["cell"]
    vol_conn = cell.open_volume_server(params["server"], params)
    vldb_conn = cell.open_vl_server(params)

    ret = kafs.VOLSER_XListPartitions(vol_conn)
    partitions = ret.ent

    # The partition must exist on the server
    part = params["partition"]
    if part not in partitions:
        raise AFSException("partition " + id2part(part) + " does not exist on the server")

    # The volume mustn't exist in the VLDB
    try:
        ret = kafs.VL_GetEntryByNameN(vldb_conn, params["name"])
        raise AFSException("Volume " + params["name"] + " already exists")
    except kafs.AbortVL_NOENT:
        pass

    # We need three volume IDs for the R/W, R/O and backup volumes
    volume_ids = [ 0, 0, 0 ]
    ret = kafs.VL_GetNewVolumeId(vldb_conn, 1)
    volume_ids[kafs.RWVOL] = ret.newvolumid
    ret = kafs.VL_GetNewVolumeId(vldb_conn, 1)
    volume_ids[kafs.ROVOL] = ret.newvolumid
    ret = kafs.VL_GetNewVolumeId(vldb_conn, 1)
    volume_ids[kafs.BACKVOL] = ret.newvolumid

    # Begin a volume creation transaction and configure the volume
    ret = kafs.VOLSER_CreateVolume(vol_conn,
                                   part,
                                   params["name"],
                                   kafs.RWVOL,
                                   0,
                                   volume_ids[kafs.RWVOL])
    if ret.volid != volume_ids[kafs.RWVOL]:
        raise AFSException("Tried to create volume {:x} but got {:x}".format(
            ret.volid, volume_ids[kafs.RWVOL]))
    transaction = ret.trans

    try:
        # Set the maximum quota
        v = 0xffffffff
        info = kafs.volintInfo()
        info.creationDate = v
        info.accessDate = v
        info.updateDate = v
        info.dayUse = v
        info.flags = v
        info.spare0 = v
        info.spare1 = v
        info.spare2 = v
        info.spare3 = v

        if "maxquota" in params:
            info.maxquota = int(params["maxquota"])
        else:
            info.maxquota = 5000

        ret = kafs.VOLSER_SetInfo(vol_conn, transaction, info)

        # Set the flags
        ret = kafs.VOLSER_SetFlags(vol_conn, transaction, 0)

        # Create the VLDB entry
        vldb = kafs.nvldbentry()
        vldb.name = params["name"]
        vldb.nServers = 1
        vldb.serverNumber[0] = int(params["server"].addr())
        vldb.serverPartition[0] = part
        vldb.serverFlags[0] = kafs.VLSF_RWVOL
        vldb.volumeId = volume_ids
        vldb.cloneId = 0
        vldb.flags = kafs.VLF_RWEXISTS

        ret = kafs.VL_CreateEntryN(vldb_conn, vldb)

    except Exception as e:
        # If we can't create a VLDB entry, we should probably clean up the
        # volume we've just created, rather than leaving it lying around.
        error("VLDB entry or volume creation failed; attempting to delete the volume.");
        try:
            kafs.VOLSER_DeleteVolume(vol_conn, transaction)
        except:
            error("Volume deletion failed");
        try:
            ret = kafs.VOLSER_EndTrans(vol_conn, transaction)
        except:
            error("Couldn't end volume creation transaction on error\n")
        raise e

    # Polish off
    try:
        ret = kafs.VOLSER_EndTrans(vol_conn, transaction)
    except Exception as e:
        error("Couldn't end volume creation transaction on error\n")
        raise e
