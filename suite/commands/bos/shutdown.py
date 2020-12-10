#
# AFS Server management toolkit: Stop server instances
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

help = "Stop a process without changing its status flag"

command_arguments = [
    [ "server",         get_bosserver,          "rs",         "<machine name>" ],
    [ "instance",       get_file_names,         "om",         "<server process name>+" ],
    [ "wait",           get_auth,               "fn" ],
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
    "instance"          : kafs.BOZO_BSSIZE,
}

description = r"""
Stop a process without changing its status flag
"""

def main(params):
    cell = params["cell"]
    bos_conn = cell.open_bos_server(params["server"], params)
    error_occurred = False

    if "instance" in params:
        for i in params["instance"]:
            try:
                verbose("Shutting down ", i, "\n");
                ret = kafs.BOZO_SetTStatus(bos_conn, i, kafs.BSTAT_SHUTDOWN)
            except kafs.AbortBZNOENT:
                error("failed to shutdown instance '", i, "' (no such entity)\n")
                error_occurred = True
    else:
        ret = kafs.BOZO_ShutdownAll(bos_conn)

    if not error_occurred and "wait" in params:
        verbose("Waiting\n")
        ret = kafs.BOZO_WaitAll(bos_conn)
