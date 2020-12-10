#
# AFS Server management toolkit: Remotely execute command
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

from afs.exception import AFSArgumentError
from afs.argparse import *
from afs.lib.output import *
import kafs

help = "Execute a command on a remote server machine"

command_arguments = [
    [ "server",         get_bosserver,          "rs",         "<machine name>" ],
    [ "cmd",            get_string,             "rs",         "<command to execute>" ],
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
    "cmd"               : kafs.BOZO_BSSIZE,
}

description = r"""
Execute a command on a remote server machine
"""

def main(params):
    cell = params["cell"]
    bos_conn = cell.open_bos_server(params["server"], params)

    try:
        ret = kafs.BOZO_Exec(bos_conn, params["cmd"])
    except kafs.RemoteAbort as e:
        # If the command terminates with anything other than exit(0), the
        # server aborts with the wait() status.
        status = int(str(e)[8:])
        if status & 0xff:
            errorf("The remote process aborted on signal {:d}\n", status & 0xff)
        else:
            errorf("The remote process exited abnormally with code {:d}\n", (status & 0xff00) >> 8)
