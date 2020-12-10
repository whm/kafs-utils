#
# AFS Server management toolkit: Restart server instances
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

help = "Restart a server process"

command_arguments = [
    [ "server",         get_bosserver,          "rs",         "<machine name>" ],
    [ "instance",       get_file_names,         "om",         "<server process name>+" ],
    [ "bosserver",      get_dummy,              "fn" ],
    [ "all",            get_dummy,              "fn" ],
    [ "cell",           get_cell,               "os",         "<cell name>" ],
    [ "noauth",         get_auth,               "fn" ],
    [ "localauth",      get_auth,               "fn" ],
    [ "verbose",        get_verbose,            "fn" ],
    [ "encrypt",        get_dummy,              "fn" ],
]

cant_combine_arguments = [
    ( "cell",           "localauth" ),
    ( "noauth",         "localauth" ),
    ( "all",            "bosserver" ),
    ( "bosserver",      "instance" ),
    ( "instance",       "all" ),
]

argument_size_limits = {
    "instance"          : kafs.BOZO_BSSIZE,
}

description = r"""
Restart a server process
"""

def main(params):
    cell = params["cell"]
    bos_conn = cell.open_bos_server(params["server"], params)

    if "all" in params:
        ret = kafs.BOZO_RestartAll(bos_conn)
    elif "bosserver" in params:
        ret = kafs.BOZO_ReBozo(bos_conn)
    elif "instance" in params:
        for i in params["instance"]:
            try:
                verbose("Restarting ", i, "\n")
                ret = kafs.BOZO_Restart(bos_conn, i)
            except kafs.AbortBZNOENT:
                error("failed to start instance '", i, "' (no such entity)\n")
    else:
        raise AFSArgumentError("One of -all, -bosserver or -instance must be supplied")
