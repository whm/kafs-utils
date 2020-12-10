#
# AFS Server management toolkit: Report file data
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
from afs.lib.time import *
import kafs

help = "Display the time stamps on an AFS binary file"

command_arguments = [
    [ "server",         get_bosserver,          "rs",         "<machine name>" ],
    [ "file",           get_file_names,         "rm",         "<files to check>+" ],
    [ "dir",            get_path_name,          "os",         "<destination dir>" ],
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
    "file"              : kafs.BOZO_BSSIZE,
    "dir"               : kafs.BOZO_BSSIZE,
}

description = r"""
Display the time stamps on an AFS binary file installed on the server.
"""

def main(params):
    cell = params["cell"]
    bos_conn = cell.open_bos_server(params["server"], params)

    if "dir" in params:
        d = params["dir"]
    else:
        d = "/usr/afs/bin"

    for f in params["file"]:
        i = f.rfind('/')
        if i > -1:
            f = f[i + 1:]
        f = d + "/" + f

        verbose("Asking about ", f, "\n")
        ret = kafs.BOZO_GetDates(bos_conn, f)

        if ret.newtime == 0:
            s = "File " + f + "does not exist, "
        else:
            s = "File {:s} dated {:s}, ".format(f, time2str(ret.newtime))
        if ret.baktime == 0:
            s += "no .BAK file, "
        else:
            s += ".BAK file dated " + time2str(ret.baktime) + ", "
        if ret.oldtime == 0:
            s += "no .OLD file."
        else:
            s += ".OLD file dated " + time2str(ret.oldtime) + "."

        output(s, "\n")
