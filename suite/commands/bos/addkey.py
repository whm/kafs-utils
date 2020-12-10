#
# AFS Server management toolkit: Add server keys
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
from getpass import getpass

help = "Add a new server encryption key to the KeyFile file"

command_arguments = [
    [ "server",         get_bosserver,          "rs",         "<machine name>" ],
    [ "key",            get_string,             "os"          "<key>" ],
    [ "kvno",           get_string,             "rs"          "<key version number>" ],
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
Add a new server encryption key to the KeyFile file
"""

def main(params):
    cell = params["cell"]
    bos_conn = cell.open_bos_server(params["server"], params)

    if "key" in params:
        passwd = params["key"]
    else:
        passwd = getpass("Input key: ")
        passwd2 = getpass("Retype input key: ")
        if passwd != passwd2:
            raise RuntimeError("Input key mismatch")

    salted_passwd = kafs.afs_string_to_key(passwd, str(cell))
    key = kafs.bozo_key()
    key.data = salted_passwd

    a = ""
    for i in key.data:
        a += "{:02x}".format(i)
    verbose("Key: {:d}: ".format(len(key.data)), a, "\n")

    try:
        ret = kafs.BOZO_AddKey(bos_conn, int(params["kvno"]), key)
    except kafs.AbortBZKVNOINUSE:
        errorf("failed to set key {:s} (kvno already used - have to remove existing kvno's before reuse)\n", params["kvno"])
