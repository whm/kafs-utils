#
# AFS Server management toolkit: Server log fetcher
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

from afs.exception import AFSException
from afs.argparse import *
from afs.lib.output import *
import kafs
import os

help = "Print a server process's log file"

command_arguments = [
    [ "server",         get_bosserver,          "rs",         "<machine name>" ],
    [ "file",           get_file_name,          "rs",         "<log file to examine>" ],
    [ "cell",           get_cell,               "os",         "<cell name>" ],
    [ "noauth",         get_auth,               "fn" ],
    [ "localauth",      get_auth,               "fn" ],
    [ "verbose",        get_verbose,            "fn" ],
    [ "encrypt",        get_dummy,              "fn" ],
]

cant_combine_arguments = [
    ( "cell",           "localauth" ),
    ( "noauth",         "localauth" ),
]

argument_size_limits = {
    "file"              : kafs.BOZO_BSSIZE,
}

description = r"""
Print a server process's log file
"""

class split_handler:
    def __init__(self):
        pass

    def transmit(self, split_info):
        return None

    # Receive state machine.  Returns True if more data is required to be read
    # or another state must be transited to and False if the operation is now
    # complete.
    #
    def receive(self, split_info):
        # We want to receive everything we can - the entire response phase
        # belongs to the split handler
        if split_info.state == 0:
            split_info.will_recv_all()
            split_info.state = 1
            return True

        if split_info.state == 1:
            avail = split_info.data_available()
            if avail == None:
                # Last byte read
                return False
            if avail == 0:
                split_info.will_recv_all()
                return True

            if avail > 4096:
                avail = 4096
            buf = bytearray(avail)
            split_info.target = buf
            split_info.state = 2

            # Request reception start.  This function will be reentered with
            # phase incremented when it's done.  receive_failed() will be
            # called instead upon failure.
            return split_info.begin_recv(buf, False)

        if split_info.state == 3:
            buf = split_info.target
            split_info.target = None

            # Strip any terminal NUL chars
            buf = buf.rstrip(b"\0")
            output_raw(buf)
            del buf

            split_info.state = 1
            return True

        raise AFSException("Unexpected receive phase ", split_info.phase,
                           " in getlog() split.receive()")

    def receive_failed(self, split_info):
        print("Receive failed in phase", split_info.phase)
        split_info.target = None

def main(params):
    cell = params["cell"]
    bos_conn = cell.open_bos_server(params["server"], params)

    split = split_handler()

    output("Fetching log file '", params["file"], "'...\n")
    output_flush()
    ret = kafs.BOZO_GetLog(bos_conn, params["file"], split)
