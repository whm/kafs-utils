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
from afs.exception import AFSException
from afs.lib.output import *
from afs.lib.voldisplay import *
from afs.lib.partition import id2part
from afs.lib.volserver import volserver
import kafs

help = "Show volume header and VLDB entry information for a volume"

command_arguments = [
    [ "id",             get_volume_name,        "rs",         "<volume name or ID>" ],
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
]

argument_size_limits = {
    "id"                : kafs.VLDB_MAXNAMELEN,
}

description = r"""
Show volume header and VLDB entry information for a volume
"""

def display_vldb(params, vldb):
    if vldb.volumeId[kafs.RWVOL] != 0:
        outputf("    RWrite: {:<10d}", vldb.volumeId[kafs.RWVOL])
    if vldb.volumeId[kafs.ROVOL] != 0:
        outputf("    ROnly: {:<10d}", vldb.volumeId[kafs.ROVOL])
    if vldb.volumeId[kafs.BACKVOL] != 0:
        outputf("    Backup: {:<10d}", vldb.volumeId[kafs.BACKVOL])
    output("\n")

    display_vldb_site_list(params, vldb, "    ")

def display_normal(params, vldb, vol):
    display_vol_information(params, vol)
    if "extended" in params:
        display_vol_statistics(params, vol)
    display_vldb(params, vldb)

def display_format(params, vldb, vol):
    display_vol_mp_information(params, vol)
    output("\n")
    display_vldb(params, vldb)

###############################################################################
#
#
#
###############################################################################
def main(params):
    cell = params["cell"]
    vl_conn = cell.open_vl_server(params)

    volname = params["id"]
    if volname.isnumeric():
        volid = int(volname)
        ret = kafs.VL_GetEntryByIDN(vl_conn, volid, 0xffffffff)
        vldb = ret.entry
        if volid == vldb.volumeId[kafs.RWVOL]:
            servflag = kafs.VLSF_RWVOL
        elif volid == vldb.volumeId[kafs.ROVOL]:
            servflag = kafs.VLSF_ROVOL
        elif volid == vldb.volumeId[kafs.BACKVOL]:
            servflag = kafs.VLSF_BACKVOL
        else:
            raise AFSException("Requested volume ID not in record for volume ID")
    else:
        ret = kafs.VL_GetEntryByNameN(vl_conn, volname)
        vldb = ret.entry
        servflag = 0
        for i in range(0, vldb.nServers):
            servflag |= vldb.serverFlags[i]
        if servflag & kafs.VLSF_RWVOL:
            servflag = kafs.VLSF_RWVOL
            volid = vldb.volumeId[kafs.RWVOL]
        elif servflag & kafs.VLSF_ROVOL:
            servflag = kafs.VLSF_ROVOL
            volid = vldb.volumeId[kafs.ROVOL]
        elif servflag & kafs.VLSF_BACKVOL:
            servflag = kafs.VLSF_BACKVOL
            volid = vldb.volumeId[kafs.BACKVOL]
        else:
            raise AFSException("Requested volume does not exist on any server")

    del vl_conn;

    for i in range(0, vldb.nServers):
        if vldb.serverFlags[i] & servflag == 0:
            continue

        vol_server = volserver(vldb.serverNumber[i])
        vol_conn = cell.open_volume_server(vol_server, params)
        if "extended" in params:
            ret = kafs.VOLSER_XListOneVolume(vol_conn, vldb.serverPartition[i], volid)
        else:
            ret = kafs.VOLSER_ListOneVolume(vol_conn, vldb.serverPartition[i], volid)
        params["server"] = vol_server
        params["_partname"] = id2part(vldb.serverPartition[i])
        vol = ret.resultEntries[0]
        del vol_conn
        break
    else:
        raise AFSException("Couldn't examine requested volume")

    if "format" in params and "extended" not in params:
        display_format(params, vldb, vol)
    else:
        display_normal(params, vldb, vol)
