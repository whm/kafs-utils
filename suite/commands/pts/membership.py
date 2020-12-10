#
# AFS Server management toolkit: Find ownership of entry
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

help = "Show the Protection Database groups owned by a user or group"

command_arguments = [
    [ "nameorid",       get_strings,            "rm",         "<user name>+" ],
    [ "supergroups",    get_dummy,              "fn" ],
    [ "expandgroups",   get_dummy,              "fn" ],
    [ "cell",           get_cell,               "os",         "<cell name>" ],
    [ "noauth",         get_auth,               "fn" ],
    [ "localauth",      get_auth,               "fn" ],
    [ "verbose",        get_verbose,            "fn" ],
    [ "encrypt",        get_dummy,              "fn" ],
    [ "force",          get_dummy,              "fn" ],
]

cant_combine_arguments = [
    ( "cell",           "localauth" ),
    ( "noauth",         "localauth" ),
]

argument_size_limits = {
    "nameorid"          : kafs.PR_MAXNAMELEN,
}

description = r"""
Show the Protection Database groups owned by a user or group
"""

def main(params):
    cell = params["cell"]
    prcache = cell.get_prcache(params)

    for name in params["nameorid"]:
        prcache.precache_name_or_id(name)

    requests = []
    memberships = dict()

    for name in params["nameorid"]:
        gid = prcache.name_or_id_to_id(name)
        if gid == None:
            error("User or group doesn't exist so couldn't look up id for " + name + "\n")
            if "force" not in params:
                break
            continue

        if gid not in requests:
            try:
                if gid < 0:
                    # Group
                    verbose("Listing membership of ", gid, " (", name, ")\n")
                    group = prcache.id_to_group(gid)
                    prcache.precache_ids(group)
                else:
                    # User - ListElements returns the ancestry of a non-group
                    ret = cell.call_pt_server(params, kafs.PR_ListElements, gid)
                    elist = ret.elist
                    memberships[gid] = elist
                    prcache.precache_ids(elist)
                    for i in elist:
                        if i < 0:
                            prcache.id_to_group(i)
                requests.append(gid)

            except kafs.AbortPRNOENT:
                error("User or group doesn't exist ", name, " (id ", gid, ")\n")
                prcache.id_is_unknown(gid)
                if "force" not in params:
                    break
            except kafs.AbortPRPERM:
                error("Permission denied on ID ", name, " (id: ", gid, ")\n")
                prcache.id_is_unknown(gid)
                if "force" not in params:
                    break

    if "expandgroups" in params:
        groups_needing_expansion = set(prcache.known_groups())
        verbose("Expand groups ", groups_needing_expansion, "\n")
        while groups_needing_expansion:
            gid = groups_needing_expansion.pop()
            members = prcache.id_to_group(gid)
            for m in members:
                prcache.precache_id(m)
                if m < 0 and not prcache.have_group(m) and m not in groups_needing_expansion:
                    groups_needing_expansion.add(m)

    if "supergroups" in params:
        for r in requests:
            if r < 0:
                ret = cell.call_pt_server(params, kafs.PR_ListGroupsMemberOf, r)
                glist = ret.glist
                memberships[r] = glist

    for r in requests:
        # Display members of a group
        if r < 0:
            if "expandgroups" in params:
                output("Expanded Members of ", prcache.id_to_name(r), " (id: ", r, ") are:\n")
                for m in prcache.id_to_expanded_group(r):
                    if m > 0:
                        output("  ", prcache.id_to_name(m), "\n")
            else:
                output("Members of ", prcache.id_to_name(r), " (id: ", r, ") are:\n")
                for m in prcache.id_to_group(r):
                    output("  ", prcache.id_to_name(m), "\n")

        # Display membership of a user or a group
        if r > 0 and "expandgroups" in params:
            output("Expanded Groups ", prcache.id_to_name(r), " (id: ", r, ") is a member of:\n")
            member_of = memberships[r]
            expanded = set(member_of)
            for gid in member_of:
                expanded |= prcache.id_to_expanded_group(gid)
            for m in expanded:
                if m < 0:
                    output("  ", prcache.id_to_name(m), "\n")
        elif r > 0 or "supergroups" in params:
            output("Groups ", prcache.id_to_name(r), " (id: ", r, ") is a member of:\n")
            for gid in memberships[r]:
                output("  ", prcache.id_to_name(gid), "\n")
