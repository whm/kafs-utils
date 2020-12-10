#
# AFS Server management toolkit: Examine a protection DB entry
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
import sys

help = "Display a Protection Database entry"

command_arguments = [
    [ "nameorid",       get_strings,            "rm",         "<user name>+" ],
    [ "cell",           get_cell,               "os",         "<cell name>" ],
    [ "noauth",         get_auth,               "fn" ],
    [ "localauth",      get_auth,               "fn" ],
    [ "verbose",        get_verbose,            "fn" ],
    [ "encrypt",        get_dummy,              "fn" ],
    [ "force",          get_dummy,              "fn" ],
    [ "auth",           get_dummy,              "fn" ],
]

cant_combine_arguments = [
    ( "cell",           "localauth" ),
    ( "noauth",         "localauth" ),
]

argument_size_limits = {
    "nameorid"          : kafs.PR_MAXNAMELEN,
}

description = r"""
Display a Protection Database entry
"""

def main(params):
    cell = params["cell"]
    prcache = cell.get_prcache(params)

    for name in params["nameorid"]:
        prcache.precache_name_or_id(name)
    del name

    # Look up the names
    requests = []
    results = dict()
    for name in params["nameorid"]:
        uid = prcache.name_or_id_to_id(name)

        if uid not in results:
            try:
                verbose("Listing entry for ", uid, " (", name, ")\n")
                ret = cell.call_pt_server(params,  kafs.PR_ListEntry, uid)
                entry = ret.entry
                results[uid] = entry
                requests.append(uid)
                prcache.precache_id(entry.owner)
                prcache.precache_id(entry.creator)
            except kafs.AbortPRNOENT:
                error("User or group doesn't exist examining ", name, " (id ", uid, ")\n")
                prcache.id_is_unknown(uid)
            except kafs.AbortPRPERM:
                error("Permission denied examining ", name, " (id: ", uid, ")\n")

    # Display the results
    for req in requests:
        entry = results[req]
        eflags = entry.flags << 16
        flags = ""
        # Indicate who can use "pts examine"
        if eflags & kafs.PRP_STATUS_ANY:
            flags += "S" # Anyone
        elif eflags & kafs.PRP_STATUS_MEM:
            flags += "s" # Members only
        else:
            flags += "-" # Should not exist

        # Indicate who can use "pts listowned"
        if eflags & kafs.PRP_OWNED_ANY:
            flags += "O" # Anyone
        else:
            flags += "-" # Sysadmin & Group owner only

        # Indicate who can use "pts membership"
        if eflags & kafs.PRP_MEMBER_ANY:
            flags += "M" # Anyone
        elif eflags & kafs.PRP_MEMBER_MEM:
            flags += "m" # Members only
        else:
            flags += "-" # Sysadmin & User can list which groups they belong to

        # Indicate who can use "pts adduser"
        if eflags & kafs.PRP_ADD_ANY:
            flags += "A" # Anyone
        elif eflags & kafs.PRP_ADD_MEM:
            flags += "a" # Members only
        else:
            flags += "-" # Sysadmin & Group owner only

        # Indicate who can use "pts removeuser"
        if eflags & kafs.PRP_REMOVE_MEM:
            flags += "r" # Members can remove other members
        else:
            flags += "-" # Sysadmin & Group owner only

        # The group quota being 'unlimited' seems to depend on being a member
        # of the system:administrators group and/or having zero ngroups (or
        # possibly something else)
        verbose("Is ", entry.id, " a member of ", kafs.PR_SYSADMINID, "?\n")
        ret = cell.call_pt_server(params, kafs.PR_IsAMemberOf, entry.id, kafs.PR_SYSADMINID)
        group_quota = entry.ngroups
        if ret.flag or entry.ngroups == 0:
            group_quota = "unlimited"

        output("Name: ", entry.name, ", id: ", entry.id,
               ", owner: ", prcache.id_to_name(entry.owner),
               ", creator: ", prcache.id_to_name(entry.creator), ",\n")
        output("  membership: ", entry.count, ", flags: ", flags,
               ", group quota: ", group_quota, ".\n");

        verbosef("    flags={:x} ngroups={:d} nusers={:d} count={:d}\n",
                 entry.flags, entry.ngroups, entry.nusers, entry.count)
        verbosef("     reserved={:x},{:x},{:x},{:x},{:x}\n",
                 entry.reserved[0], entry.reserved[1], entry.reserved[2],
                 entry.reserved[3], entry.reserved[4])
