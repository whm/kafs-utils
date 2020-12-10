#
# AFS Server management toolkit: List server keys
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
from afs.lib.time import *
import kafs

help = "Display the server encryption keys from the KeyFile file"

command_arguments = [
    [ "server",         get_bosserver,          "rs",         "<machine name>" ],
    [ "showkey",        get_dummy,              "fn" ],
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
Display the server encryption keys from the KeyFile file
"""

def main(params):
    cell = params["cell"]
    bos_conn = cell.open_bos_server(params["server"], params)

    mod_sec = 0
    try:
        i = 0
        while True:
            ret = kafs.BOZO_ListKeys(bos_conn, i)
            i += 1
            if mod_sec < ret.keinfo.mod_sec:
                mod_sec = ret.keinfo.mod_sec

            output("Key ", ret.kvno)
            if "showkey" in params:
                output(" is '")
                for b in ret.key.data:
                    outputf("\\{:03o}", b)
                output("'\n")
            else:
                output(" has cksum ", ret.keinfo.keyCheckSum, "\n")

    except kafs.AbortBZDOM:
        pass

    output("Keys last changed on ", time2str(mod_sec), ".\n")
    output("All done.\n")
