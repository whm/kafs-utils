#
# AFS Server management toolkit: Prune old remote files
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

help = "Remove obsolete files from /usr/afs/bin and /usr/afs/logs"

command_arguments = [
    [ "server",         get_bosserver,          "rs",         "<machine name>" ],
    [ "bak",            get_dummy,              "fn" ],
    [ "old",            get_dummy,              "fn" ],
    [ "core",           get_dummy,              "fn" ],
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
    ( "bak",            "all" ),
    ( "old",            "all" ),
    ( "core",           "all" ),
]

description = r"""
Remove obsolete files from /usr/afs/bin and /usr/afs/logs
"""

def main(params):
    cell = params["cell"]
    bos_conn = cell.open_bos_server(params["server"], params)

    if "all" in params:
        flags = 255
    else:
        flags = 0
        if "bak" in params:
            flags |= kafs.BOZO_PRUNEBAK
        if "old" in params:
            flags |= kafs.BOZO_PRUNEOLD
        if "core" in params:
            flags |= kafs.BOZO_PRUNECORE
    ret = kafs.BOZO_Prune(bos_conn, flags)
