#
# AFS Server management toolkit: Configure a protection DB entry
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
from afs.exception import AFSArgumentError
from afs.lib.output import *
import kafs
import sys

help = "Set privacy flags or quota for a Protection Database entry"

def get_privacy_flags(switch, params):
    s = params[0]
    if len(s) != 5:
        raise AFSArgumentError("Privacy flag string must be exactly 5 characters")
    flags = 0

    # Indicate who can use "pts examine"
    if s[0] == "S":
        flags |= kafs.PRP_STATUS_ANY    # Anyone
    elif s[0] == "s":
        flags |= kafs.PRP_STATUS_MEM    # Members only
    else:
        raise AFSArgumentError("Status-read privacy flags must be [Ss]")

    # Indicate who can use "pts listowned"
    if s[1] == "O":
        flags |= kafs.PRP_OWNED_ANY     # Anyone
    elif s[1] == "-":
        pass                            # Sysadmin & Group owner only
    else:
        raise AFSArgumentError("Ownership-read privacy flags must be [O-]")

    # Indicate who can use "pts membership"
    if s[2] == "M":
        flags |= kafs.PRP_MEMBER_ANY    # Anyone
    elif s[2] == "m":
        flags |= kafs.PRP_MEMBER_MEM  # Members only
    elif s[2] == "-":
        pass                            # Sysadmin & User can list which groups they belong to
    else:
        raise AFSArgumentError("Membership-read privacy flags must be [Mm-]")

    # Indicate who can use "pts adduser"
    if s[3] == "A":
        flags |= kafs.PRP_ADD_ANY       # Anyone
    elif s[3] == "a":
        elflags |= kafs.PRP_ADD_MEM     # Members only
    elif s[3] == "-":
        pass                            # Sysadmin & Group owner only
    else:
        raise AFSArgumentError("Add-user privacy flags must be [Aa-]")

    # Indicate who can use "pts removeuser"
    if s[4] == "r":
        flags |= kafs.PRP_REMOVE_MEM    # Members can remove other members
    elif s[4] == "-":
        pass                            # Sysadmin |= Group owner only
    else:
        raise AFSArgumentError("Remove-user privacy flags must be [r-]")

    return flags >> 16

command_arguments = [
    [ "nameorid",       get_strings,            "rm",         "<user name>+" ],
    [ "access",         get_privacy_flags,      "os",         "<set privacy flags>" ],
    [ "groupquota",     get_string,             "os",         "<set limit on group creation>" ],
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
Set privacy flags or quota for a Protection Database entry
"""

def main(params):
    cell = params["cell"]
    prcache = cell.get_prcache(params)

    for name in params["nameorid"]:
        prcache.precache_name_or_id(name)
    del name

    mask = 0
    flags = 0
    ngroups = 0

    if "access" in params:
        flags = params["access"]
        mask |= kafs.PR_SF_ALLBITS

    if "groupquota" in params:
        ngroups = params["groupquota"]
        if not ngroups.isnumeric():
            raise AFSArgumentError("Group quota must be positive integer or zero")
        ngroups = int(ngroups)
        mask |= kafs.PR_SF_NGROUPS

    for name in params["nameorid"]:
        uid = prcache.name_or_id_to_id(name)

        try:
            verbose("Altering entry for ", uid, " (", name, ")\n")
            ret = cell.call_pt_server(params,  kafs.PR_SetFieldsEntry,
                                      uid, mask, flags, ngroups, 0, 0, 0)
        except kafs.AbortPRNOENT:
            error("User or group doesn't exist examining ", name, " (id ", uid, ")\n")
            prcache.id_is_unknown(uid)
        except kafs.AbortPRPERM:
            error("Permission denied examining ", name, " (id: ", uid, ")\n")
