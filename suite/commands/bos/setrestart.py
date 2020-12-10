#
# AFS Server management toolkit: Set server restart times
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

from exception import AFSArgumentError
from afs.argparse import *
from afs.lib.output import *
from afs.lib.parse_setrestart_time import *
import kafs

help = "Set when the BOS Server restarts processes"

command_arguments = [
    [ "server",         get_bosserver,          "rs",         "<machine name>" ],
    [ "time",           parse_restart_time,     "rs",         "<time to restart server>" ],
    [ "general",        get_dummy,              "fn" ],
    [ "newbinary",      get_dummy,              "fn" ],
    [ "cell",           get_cell,               "os",         "<cell name>" ],
    [ "noauth",         get_auth,               "fn" ],
    [ "localauth",      get_auth,               "fn" ],
    [ "verbose",        get_verbose,            "fn" ],
    [ "encrypt",        get_dummy,              "fn" ],
]

cant_combine_arguments = [
    ( "general",        "newbinary" ),
    ( "cell",           "localauth" ),
    ( "noauth",         "localauth" ),
]

description = r"""
Set when the BOS Server restarts processes
"""

def main(params):
    cell = params["cell"]
    bos_conn = cell.open_bos_server(params["server"], params)

    time = params["time"]

    t = kafs.BOZO_RESTARTTIME_GENERAL
    if "newbinary" in params:
        t = kafs.BOZO_RESTARTTIME_NEWBIN

    ret = kafs.BOZO_SetRestartTime(bos_conn, t, time)
