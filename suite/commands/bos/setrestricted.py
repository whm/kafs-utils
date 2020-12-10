#
# AFS Server management toolkit: Put server into restricted mode
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

help = "Place a server into restricted mode"

command_arguments = [
    [ "server",         get_bosserver,          "rs",         "<machine name>" ],
    [ "mode",           get_string,             "rs",         "1"],
    [ "cell",           get_cell,               "os",         "<cell name>" ],
    [ "noauth",         get_auth,               "fn" ],
    [ "localauth",      get_auth,               "fn" ],
    [ "verbose",        get_dummy,              "fn" ],
    [ "encrypt",        get_dummy,              "fn" ],
]

cant_combine_arguments = [
    ( "cell",           "localauth" ),
    ( "noauth",         "localauth" ),
]

description = r"""
Place a server into restricted mode
"""

def main(params):
    cell = params["cell"]
    bos_conn = cell.open_bos_server(params["server"], params)

    if not params["mode"].isnumeric():
        raise AFSArgumentError("The -mode argument takes a numeric value")

    try:
        ret = kafs.BOZO_SetRestricted(bos_conn, int(params["mode"]))
    except kafs.AbortBZACCESS:
        error("failed to set restricted mode (you are not authorized for this operation)\n")
