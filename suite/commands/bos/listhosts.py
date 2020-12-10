#
# AFS Server management toolkit: Report server status
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
import kafs

help = "Display the contents of the CellServDB file"

command_arguments = [
    [ "server",         get_bosserver,          "rs",         "<machine name>" ],
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

description = r"""
Display the contents of the CellServDB file
"""

def main(params):
    cell = params["cell"]
    bos_conn = cell.open_bos_server(params["server"], params)

    ret = kafs.BOZO_GetCellName(bos_conn)
    cellname = ret.name
    output("Cell name is ", cellname, "\n")

    try:
        i = 0
        while True:
            ret = kafs.BOZO_GetCellHost(bos_conn, i)
            i += 1
            output("Host ", i, " is ", ret.name, "\n")
    except kafs.AbortBZDOM:
        pass
