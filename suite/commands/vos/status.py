#
# AFS Volume management toolkit: Report server status
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
from afs.lib.time import *
import kafs

help = "Report a volume server's status"

command_arguments = [
    [ "server",         get_volserver,          "rs",         "<machine name>" ],
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
Report a volume server's status
"""

def main(params):
    cell = params["cell"]
    vol_conn = cell.open_volume_server(params["server"], params)

    ret = kafs.VOLSER_Monitor(vol_conn)
    results = ret.result
    if len(results) == 0:
        output("No active transactions on", params["server"].name(), "\n")
        return

    output("--------------------------------------------\n")
    for trans in results:
        outputf("transaction: {:d}  created: {:s}\n", trans.tid, time2str(trans.creationTime))
        output("lastActiveTime:", time2str(trans.time), "\n")
        if iflag & kafs.ITOffline:
            attach_mode = "offline"
        elif iflag & kafs.ITBusy:
            attach_mode = "busy"
        elif iflag & kafs.ITReadOnly:
            attach_mode = "readonly"
        elif iflag & kafs.ITCreate:
            attach_mode = "create"
        elif iflag & kafs.ITCreateVolID:
            attach_mode = "createvolid"
        else:  
            attach_mode = "{:d}".format(trans.iflags)
        output("attachFlags: ", attach_mode, "\n")
        ourputf("volume: {:d} partition {:s} procedure {:s}",
                trans.volid,
                partition.id2part(trans.partition),
                lastProcName)
        output("packetRead: ", trans.readNext,
               " lastReceiveTime: ", trans.lastReceiveTime,
               " packetSend: ", trans.transmitNext,
               "\n")
        output("    lastSendTime: ", trans.lastSendTime, "\n")
        output("--------------------------------------------\n")
