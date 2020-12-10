#
# AFS Server management toolkit: Create a server instance
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

from afs.exception import AFSException, AFSArgumentError
from afs.argparse import *
from afs.lib.output import *
import kafs

help = "Define a new process in the BosConfig file and start it"

command_arguments = [
    [ "server",         get_bosserver,          "rs",         "<machine name>" ],
    [ "instance",       get_file_name,          "rs",         "<server process name>" ],
    [ "type",           get_string,             "rs",         "<server type>" ],
    [ "cmd",            get_strings,            "rm",         "<command lines>+" ],
    [ "notifier",       get_string,             "os",         "<notifier program>" ],
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
    "type"              : kafs.BOZO_BSSIZE,
    "cmd"               : kafs.BOZO_BSSIZE,
    "notifier"          : kafs.BOZO_BSSIZE,
}

description = r"""
Define a new process in the BosConfig file and start it
"""

def main(params):
    instance = params["instance"]
    type = params["type"]
    cmd = params["cmd"]

    # We should be able to specify six commands, but the 6th slot has been
    # stolen for the notifier.
    if len(cmd) > 5:
        raise AFSArgumentError("Can't specify more than five commands");
    for i in range(len(cmd), 6):
        cmd.append("")

    if "notifier" in params:
        cmd[5] = params["notifier"]
    else:
        cmd[5] = "__NONOTIFIER__"

    cell = params["cell"]
    bos_conn = cell.open_bos_server(params["server"], params)

    try:
        ret = kafs.BOZO_CreateBnode(bos_conn, type, instance,
                                    cmd[0], cmd[1], cmd[2], cmd[3], cmd[4], cmd[5])
    except kafs.AbortBZEXISTS:
        error("failed to create new server instance ", instance,
              " of type '", type, "' (entity already exists)\n")
