#
# AFS Server management toolkit: Show server statuses
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
import sys
import signal

help = "Display the status of server processes"

command_arguments = [
    [ "server",         get_bosserver,          "rs",         "<machine name>" ],
    [ "instance",       get_file_names,         "om",         "<server process name>+" ],
    [ "long",           get_dummy,              "fn" ],
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
Display the status of server processes
"""

def display_instance_normal(params, bos_conn, name):
    info = kafs.BOZO_GetInstanceInfo(bos_conn, name)
    status = kafs.BOZO_GetStatus(bos_conn, name)

    if info.status.flags & kafs.BOZO_BADDIRACCESS:
        params["_baddiraccess"] = True

    s = "Instance " + name + ","

    if "long" in params:
        s += " (type is " + info.type + ")"

    # The instance's permanent state is shown by the goals returned by
    # GetInstanceInfo()
    if info.status.fileGoal == kafs.BSTAT_SHUTDOWN:
        if info.status.goal == kafs.BSTAT_SHUTDOWN:
            s += " disabled,"
        else:
            s += " temporarily enabled,"
    else:
        if info.status.goal == kafs.BSTAT_SHUTDOWN:
            s += " temporarily disabled,"
        else:
            pass

    # Supplementary data is found in the flags
    if info.status.flags & kafs.BOZO_HASCORE:
        s += " has core file,"
    if info.status.flags & kafs.BOZO_ERRORSTOP:
        s += " stopped for too many errors,"

    # The instance's actual state is returned by GetStatus()
    if status.inStat == kafs.BSTAT_SHUTDOWN:
        s += " currently shut down."
    elif status.inStat == kafs.BSTAT_NORMAL:
        s += " currently running normally."
    elif status.inStat == kafs.BSTAT_SHUTTINGDOWN:
        s += " currently shutting down."
    elif status.inStat == kafs.BSTAT_STARTINGUP:
        s += " currently starting up."
    output(s, "\n")
    if status.statdescr != "":
        output("    Auxiliary status is: ", status.statdescr, "\n")
    return (info, status)

###############################################################################
#
#
#
###############################################################################
def display_instance_long(params, bos_conn, name):
    info, status = display_instance_normal(params, bos_conn, name)

    outputf("    Process last started at {:s} ({:d} proc starts)",
            time2str(info.status.porcStartTime),
            info.status.procStarts)

    if info.status.lastAnyExit != 0:
        output("    Last exit at ", time2str(info.status.lastAnyExit), "\n")

    if info.status.lastErrorExit != 0:
        output("    Last error exit ", info.status.lastErrorExit, "\n")
        s = "    Last error exit at " + time2str(info.status.lastErrorExit) + ","
        istr = kafs.BOZO_GetInstanceStrings(bos_conn, name)
        if istr.errorname != "":
            s += " by " + istr.errorname + ","
        if info.status.errorSignal == signal.SIGTERM:
            s += " due to shutdown request."
        elif info.status.errorSignal != 0:
            s += " due to signal {:d}.".format(info.status.errorSignal)
        else:
            s += " due to exit {:d}.".format(info.status.errorCode)
        output(s, "\n")

    try:
        i = 0
        while True:
            ret = kafs.BOZO_GetInstanceParm(bos_conn, name, i)
            i += 1
            output("    Command ", i, " is '", ret.parm, "'\n")
    except kafs.AbortBZDOM:
        pass

    output("\n")

###############################################################################
#
#
#
###############################################################################
def main(params):
    cell = params["cell"]
    bos_conn = cell.open_bos_server(params["server"], params)

    if "instance" not in params:
        instances = []
        try:
            i = 0
            while True:
                verbose("Enum ", i, ": ")
                ret = kafs.BOZO_EnumerateInstance(bos_conn, i)
                i += 1
                verbose_cont(ret.iname, "\n")
                instances.append(ret.iname)
        except kafs.AbortBZDOM:
            verbose_cont("<empty slot>\n")
    else:
        instances = params["instance"]

    for i in instances:
        try:
            verbose("Displaying ", i, "\n")
            if "long" in params:
                display_instance_long(params, bos_conn, i)
            else:
                display_instance_normal(params, bos_conn, i)
        except kafs.AbortBZNOENT:
            error("failed to get instance info for '", i, "' (no such entity)\n")

    if "_baddiraccess" in params and "long" in params:
        output("Bosserver reports inappropriate access on server directories\n")
