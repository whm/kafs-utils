#
# AFS Server management toolkit: Determine server restart times
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

help = "Display the automatic restart times for server processes"

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
Display the automatic restart times for server processes
"""

restart_days = [ "sun", "mon", "tue", "wed", "thu", "fri", "sat" ]

def display_restart_time(params, desc, time):
    if time.mask & kafs.KTIME_NEVER:
        t = "never"
    elif time.mask & kafs.KTIME_NOW:
        t = "never"
    elif time.mask & (kafs.KTIME_DAY | kafs.KTIME_TIME) == 0:
        t = "[unspecified time]"
    else:
        t = "[unspecified time]"
        if time.mask & kafs.KTIME_DAY:
            t = restart_days[time.day] + " ";
        else:
            t = ""
        if time.mask & kafs.KTIME_TIME:
            if not (time.mask & kafs.KTIME_MIN):
                time.min = 0
            if time.mask & kafs.KTIME_HOUR:
                h = time.hour
                if h > 12:
                    h -= 12
                if h == 0:
                    h = 12
                t += "{:d}:{:02d}".format(h, time.min)
            else:
                t += "xx:{:02d}".format(time.min)
            if time.mask & kafs.KTIME_SEC:
                t += ":{:02d}".format(time.sec)
            if time.mask & kafs.KTIME_HOUR:
                if time.hour < 12:
                    t += " am"
                else:
                    t += " pm"
        else:
            pass

    output(desc, t, "\n")

def main(params):
    cell = params["cell"]
    bos_conn = cell.open_bos_server(params["server"], params)

    gen = kafs.BOZO_GetRestartTime(bos_conn, kafs.BOZO_RESTARTTIME_GENERAL)
    newbin = kafs.BOZO_GetRestartTime(bos_conn, kafs.BOZO_RESTARTTIME_NEWBIN)

    s = "Server " + params["server"].name() + " restarts "
    display_restart_time(params, s + "at ", gen.restartTime)
    display_restart_time(params, s + "for new binaries at ", newbin.restartTime)
