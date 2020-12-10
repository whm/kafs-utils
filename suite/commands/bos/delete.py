#
# AFS Server management toolkit: Delete a server instance
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

help = "Delete a server process from the BosConfig file"

command_arguments = [
    [ "server",         get_bosserver,          "rs",         "<machine name>" ],
    [ "instance",       get_file_names,         "rs",         "<server process name>+" ],
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
Delete a server process from the BosConfig file
"""

def main(params):
    cell = params["cell"]
    bos_conn = cell.open_bos_server(params["server"], params)

    for i in params["instance"]:
        verbose("Deleting instance ", i, "\n")
        try:
            ret = kafs.BOZO_DeleteBnode(bos_conn, i)
        except kafs.AbortBZBUSY:
            error("can't delete running instance '", i, "'\n")
