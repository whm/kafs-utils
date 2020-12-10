#
# AFS Volume management toolkit: Volume / Volume location display common pieces
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

from afs.lib.output import *
import afs.lib.addrcache as addrcache
import afs.lib.partition as partition
from afs.lib.time import *
import kafs

statistics_time_ranges = [
    "0-60 sec ",
    "1-10 min ",
    "10min-1hr",
    "1hr-1day ",
    "1day-1wk ",
    "> 1wk    "
]

def vol_type(vol):
    if vol.type == 0:
        return "RW"
    if vol.type == 1:
        return "RO"
    if vol.type == 2:
        return "BK"
    return "0x{:02x}".format(vol.type)

def vol_state(vol):
    if vol.inUse:
        s = "On-line"
    else:
        s = "Off-line"
    try:
        # This isn't available in struct xvolintInfo
        if vol.needsSalvaged:
            s += "**needs salvage**"
    except AttributeError:
        pass
    return s

def vol_status(vol):
    if vol.status == kafs.VOK:
        return "OK"
    if vol.status == kafs.VBUSY:
        return "BUSY"
    return "UNATTACHABLE"

def yes_or_no(n):
    if (n):
        return "Y"
    return "N"

###############################################################################
#
# Display the VLDB site list, looking something like:
#
#       number of sites -> 2
#          server fserver.abc.com partition /vicepa RW Site
#          server fserver.abc.com partition /vicepa RO Site
#
###############################################################################
def display_vldb_site_list(params, vldb, indent=""):
    output(indent, "number of sites -> ", vldb.nServers, "\n")
    for i in range(0, vldb.nServers):
        addr = addrcache.resolve(params, vldb.serverNumber[i])
        part = partition.id2part(vldb.serverPartition[i])

        flags = vldb.serverFlags[i]
        if flags & kafs.VLSF_ROVOL:
            ptype = "RO"
        elif flags & kafs.VLSF_RWVOL:
            ptype = "RW"
        else:
            ptype = "Back"

        outputf("{:s}   server {:s} partition {:s} {:s} Site\n",
                indent, addr, part, ptype)

    if vldb.flags & (kafs.VLOP_MOVE |
                     kafs.VLOP_RELEASE |
                     kafs.VLOP_BACKUP |
                     kafs.VLOP_DELETE |
                     kafs.VLOP_DUMP):
        output(indent, "Volume is currently LOCKED")
        if vldb.flags & kafs.VLOP_MOVE:
            output(indent, "Volume is locked for a move operation")
        if vldb.flags & kafs.VLOP_RELEASE:
            output(indent, "Volume is locked for a release operation")
        if vldb.flags & kafs.VLOP_BACKUP:
            output(indent, "Volume is locked for a backup operation")
        if vldb.flags & kafs.VLOP_DELETE:
            output(indent, "Volume is locked for a delete/misc operation")
        if vldb.flags & kafs.VLOP_DUMP:
            output(indent, "Volume is locked for a dump/restore operation")

###############################################################################
#
# Display a one-line volume summary
#
#       proj.foo                          536870957 RW   40475760 K On-line
#
###############################################################################
def display_vol_oneline_summary(params, vol):
    outputf("{:32s} {:10d} {:2s} {:10d} K {:s}\n",
            vol.name,
            vol.volid,
            vol_type(vol),
            vol.size,
            vol_state(vol))

###############################################################################
#
# Display volume information
#
#       proj.foo                          536870957 RW   40475760 K On-line
#           204.29.154.47 /vicepa
#           RWrite  536870957 ROnly  536870958 Backup          0
#           MaxQuota          0 K
#           Creation    Sat Aug 22 06:22:27 2009
#           Copy        Tue Oct 26 00:40:32 2010
#           Backup      Never
#           Last Access Tue Jan 28 23:20:37 2014
#           Last Update Mon Aug 05 21:15:32 2013
#           0 accesses in the past day (i.e., vnode references)
#       <blank>
#
###############################################################################
def display_vol_information(params, vol):
    display_vol_oneline_summary(params, vol)
    output ("    ", params["server"].addr(), " ", params["_partname"], "\n")
    outputf("    RWrite {:10d} ROnly {:10d} Backup {:10d}\n",
            vol.parentID, vol.cloneID, vol.backupID)
    outputf("    MaxQuota {:10d} K\n", vol.maxquota)
    output ("    Creation    ", time2str_or_never(vol.creationDate), "\n")
    output ("    Copy        ", time2str_or_never(vol.copyDate), "\n")
    output ("    Backup      ", time2str_or_never(vol.backupDate), "\n")
    output ("    Last Access ", time2str_or_never(vol.accessDate), "\n")
    output ("    Last Update ", time2str_or_never(vol.updateDate), "\n")
    outputf("    {:d} accesses in the past day (i.e., vnode references)\n", vol.dayUse)
    output ("\n")

###############################################################################
#
# Display volume access statistics
#
#                             Raw Read/Write Stats
#                 |-------------------------------------------|
#                 |    Same Network     |    Diff Network     |
#                 |----------|----------|----------|----------|
#                 |  Total   |   Auth   |   Total  |   Auth   |
#                 |----------|----------|----------|----------|
#       Reads     |        0 |        0 |        0 |        0 |
#       Writes    |        0 |        0 |        0 |        0 |
#                 |-------------------------------------------|
#       <blank>
#                          Writes Affecting Authorship
#                 |-------------------------------------------|
#                 |   File Authorship   | Directory Authorship|
#                 |----------|----------|----------|----------|
#                 |   Same   |   Diff   |    Same  |   Diff   |
#                 |----------|----------|----------|----------|
#       0-60 sec  |        0 |        0 |        0 |        0 |
#       1-10 min  |        0 |        0 |        0 |        0 |
#       10min-1hr |        0 |        0 |        0 |        0 |
#       1hr-1day  |        0 |        0 |        0 |        0 |
#       1day-1wk  |        0 |        0 |        0 |        0 |
#       > 1wk     |        0 |        0 |        0 |        0 |
#                 |-------------------------------------------|
#
###############################################################################
def display_vol_statistics(params, vol):
    output ("                      Raw Read/Write Stats\n")
    output ("          |-------------------------------------------|\n")
    output ("          |    Same Network     |    Diff Network     |\n")
    output ("          |----------|----------|----------|----------|\n")
    output ("          |  Total   |   Auth   |   Total  |   Auth   |\n")
    output ("          |----------|----------|----------|----------|\n")
    outputf("Reads     |{:9d} |{:9d} |{:9d} |{:9d} |\n",
            vol.stat_reads[0],
            vol.stat_reads[1],
            vol.stat_reads[2],
            vol.stat_reads[3])
    outputf("Writes    |{:9d} |{:9d} |{:9d} |{:9d} |\n",
            vol.stat_writes[0],
            vol.stat_writes[1],
            vol.stat_writes[2],
            vol.stat_writes[3])
    output ("          |-------------------------------------------|\n")

    output ("\n")
    output ("                   Writes Affecting Authorship\n")
    output ("          |-------------------------------------------|\n")
    output ("          |   File Authorship   | Directory Authorship|\n")
    output ("          |----------|----------|----------|----------|\n")
    output ("          |   Same   |   Diff   |    Same  |   Diff   |\n")
    output ("          |----------|----------|----------|----------|\n")

    for i in range(0, 5):
        outputf("{:s} |{:9d} |{:9d} |{:9d} |{:9d} |\n",
                statistics_time_ranges[i],
                vol.stat_fileSameAuthor[i],
                vol.stat_fileDiffAuthor[i],
                vol.stat_dirSameAuthor[i],
                vol.stat_dirDiffAuthor[i])
    output ("          |-------------------------------------------|\n")
    output ("\n")

###############################################################################
#
# Display machine parseable form of volume record, but excluding certain info
#
#       name            proj.foo
#       id              536870957
#       serv            111.22.33.44   foo.abc.com
#       part            /vicepa
#       status          OK
#       backupID        0
#       parentID        536870957
#       cloneID         536870958
#       inUse           Y
#       needsSalvaged   N
#       destroyMe       N
#       type            RW
#       creationDate    1250918547      Sat Aug 22 06:22:27 2009
#       accessDate      1390951237      Tue Jan 28 23:20:37 2014
#       updateDate      1375733732      Mon Aug  5 21:15:32 2013
#       backupDate      0               Thu Jan  1 01:00:00 1970
#       copyDate        1288050032      Tue Oct 26 00:40:32 2010
#       flags           0       (Optional)
#       diskused        40475760
#       maxquota        0
#       minquota        0       (Optional)
#       filecount       327
#       dayUse          0
#
###############################################################################
def display_vol_mp_basic_information(params, vol):
    server = params["server"]
    output ("BEGIN_OF_ENTRY\n")
    outputf("name\t\t{:s}\n", vol.name)
    outputf("id\t\t{:d}\n", vol.volid)
    outputf("serv\t\t{:<15s}\t{:s}\n", str(server), server.addr())
    outputf("part\t\t{:s}\n", params["_partname"])
    outputf("status\t\t{:s}\n", vol_status(vol))
    outputf("backupID\t{:d}\n", vol.backupID)
    outputf("parentID\t{:d}\n", vol.parentID)
    outputf("cloneID\t\t{:d}\n", vol.cloneID)
    outputf("inUse\t\t{:s}\n", yes_or_no(vol.inUse))
    try:
        outputf("needsSalvaged\t{:s}\n", yes_or_no(vol.needsSalvaged))
        outputf("destroyMe\t{:s}\n", yes_or_no(vol.destroyMe))
    except AttributeError:
        pass
    outputf("type\t\t{:s}\n", vol_type(vol))
    outputf("creationDate\t{:<10d}\t{:s}\n", vol.creationDate, time2str(vol.creationDate))
    outputf("accessDate\t{:<10d}\t{:s}\n", vol.accessDate, time2str(vol.accessDate))
    outputf("updateDate\t{:<10d}\t{:s}\n", vol.updateDate, time2str(vol.updateDate))
    outputf("backupData\t{:<10d}\t{:s}\n", vol.backupDate, time2str(vol.backupDate))
    outputf("copyDate\t{:<10d}\t{:s}\n", vol.copyDate, time2str(vol.copyDate))
    try:
        outputf("flags\t\t{:<7d}\t(Optional)\n", vol.flags)
    except AttributeError:
        pass
    outputf("diskused\t{:d}\n", vol.size)
    outputf("maxquota\t{:d}\n", vol.maxquota)
    try:
        outputf("minquota\t{:<7d}\t(Optional)\n", vol.spare0)
    except AttributeError:
        pass
    outputf("filecount\t{:d}\n", vol.filecount)
    outputf("dayUse\t\t{:d}\n", vol.dayUse)

###############################################################################
#
# Display machine parseable form of volume record
#
#       name            proj.foo
#       id              536870957
#       serv            111.22.33.44   foo.abc.com
#       part            /vicepa
#       status          OK
#       backupID        0
#       parentID        536870957
#       cloneID         536870958
#       inUse           Y
#       needsSalvaged   N
#       destroyMe       N
#       type            RW
#       creationDate    1250918547      Sat Aug 22 06:22:27 2009
#       accessDate      1390951237      Tue Jan 28 23:20:37 2014
#       updateDate      1375733732      Mon Aug  5 21:15:32 2013
#       backupDate      0               Thu Jan  1 01:00:00 1970
#       copyDate        1288050032      Tue Oct 26 00:40:32 2010
#       flags           0       (Optional)
#       diskused        40475760
#       maxquota        0
#       minquota        0       (Optional)
#       filecount       327
#       dayUse          0
#       weekUse         0       (Optional)
#       spare2          21775   (Optional)
#       spare3          0       (Optional)
#
###############################################################################
def display_vol_mp_information(params, vol):
    display_vol_mp_basic_information(params, vol)
    outputf("weekUse\t\t{:<7d}\t(Optional)\n", vol.spare1)
    outputf("spare2\t\t{:<7d}\t(Optional)\n", vol.spare2)
    outputf("spare3\t\t{:<7d}\t(Optional)\n", vol.spare3)
