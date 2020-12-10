#
# AFS Volume management toolkit: Protection DB ID<->Name cache
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

from afs import exception
from afs.lib.output import *
import kafs

class AFS_PR_Entry:
    """Protection Database Name/ID mapping entry"""
    def __init__(self, name, ugid):
        self.__name = name
        self.__id = ugid

    def name(self):
        return self.__name

    def ugid(self):
        return self.__id

class pr_group:
    """Protection Database group list"""
    def __init__(self, gid, members):
        self.__gid = gid
        self.__members = members
        self.__expanded_members = None

    def gid(self):
        return self.__gid

    def members(self):
        return self.__members

    def expand(self, prcache):
        if self.__expanded_members == None:
            self.__expanded_members = frozenset() # Prevent recursion loops

            expansion = set()
            xgroups = set()
            for uid in self.__members:
                expansion.add(uid)
                if uid < 0:
                    xgroups.add(uid)

            for gid in frozenset(xgroups):
                expansion |= prcache.id_to_group_object(gid).expand(prcache)

            self.__expanded_members = frozenset(expansion)
        verbose("Expanded ", self.__gid, " to ", self.__expanded_members, "\n")
        return self.__expanded_members

class prcache:
    """Protection Database Name/ID mapping cache for a cell"""
    def __init__(self, params, cell):
        self.__params = params
        self.__cell = cell
        self.__name2id = dict()
        self.__id2name = dict()
        self.__names_to_lookup = []
        self.__ids_to_lookup = []
        self.__groups = dict()
        self.__groups_to_lookup = []

    ###########################################################################
    #
    # Do the pending names lookups
    #
    ###########################################################################
    def do_look_up_pr_names(self):
        if not self.__names_to_lookup:
            return
        names_to_lookup = self.__names_to_lookup
        self.__names_to_lookup = []

        # Convert name strings to appropriate structs
        verbose("Do NameToID(")
        name_arg_list = []
        for i in names_to_lookup:
            verbose_cont(i, ",")
            prname = kafs.prname()
            prname.prname = i
            name_arg_list.append(prname)
        verbose_cont(")\n")

        ret = self.__cell.call_pt_server(self.__params, kafs.PR_NameToID, name_arg_list)
        for i in range(0, len(names_to_lookup)):
            name = names_to_lookup[i]
            ugid = ret.ilist[i]
            # Convert the name to an ID for message purposes - note that if the
            # entry does not exist, this will return the anonymous ID
            if ugid == kafs.PR_ANONYMOUSID and name != "anonymous":
                entry = AFS_PR_Entry(name, None)
            else:
                entry = AFS_PR_Entry(name, ugid)
                self.__id2name[ugid] = entry
                if ugid in self.__ids_to_lookup:
                    self.__ids_to_lookup.remove(ugid)
            self.__name2id[name] = entry

    ###########################################################################
    #
    # Do the pending ID lookups
    #
    ###########################################################################
    def do_look_up_pr_ids(self):
        if not self.__ids_to_lookup:
            return
        ids_to_lookup = self.__ids_to_lookup
        self.__ids_to_lookup = []

        verbose("Do IDToName(")
        for i in ids_to_lookup:
            verbose_cont(i, ",")
        verbose_cont(")\n")

        ret = self.__cell.call_pt_server(self.__params, kafs.PR_IDToName, ids_to_lookup)
        nlist = ret.nlist
        for i in range(0, len(ids_to_lookup)):
            ugid = ids_to_lookup[i]
            name = nlist[i].prname
            # Convert the id to a name for message purposes - note that if
            # the entry does not exist, this will just stringify the ID for
            # us.
            if name == str(ids_to_lookup[i]):
                entry = AFS_PR_Entry(None, ugid)
            else:
                entry = AFS_PR_Entry(name, ugid)
                self.__name2id[name] = entry
                if name in self.__names_to_lookup:
                    self.__names_to_lookup.remove(name)
            self.__id2name[ugid] = entry

    ###########################################################################
    #
    # Precache a name
    #
    ###########################################################################
    def precache_name(self, name):
        if name not in self.__names_to_lookup and name not in self.__name2id:
            self.__names_to_lookup.append(name)

    ###########################################################################
    #
    # Precache an ID or IDS
    #
    ###########################################################################
    def precache_id(self, ugid):
        if ugid not in self.__ids_to_lookup and ugid not in self.__id2name:
            self.__ids_to_lookup.append(ugid)

    def precache_ids(self, ugids):
        for ugid in ugids:
            self.precache_id(ugid)

    ###########################################################################
    #
    # Precache a name or a stringified ID
    #
    ###########################################################################
    def precache_name_or_id(self, name):
        if name.isnumeric() or name[0] == "-" and name[1:].isnumeric():
            self.precache_id(int(name))
        else:
            self.precache_name(name)

    ###########################################################################
    #
    # Look up an ID by name
    #
    ###########################################################################
    def name_to_id(self, name):
        if name not in self.__name2id:
            self.precache_name(name)
            self.do_look_up_pr_names()
        return self.__name2id[name].ugid()

    ###########################################################################
    #
    # Look up an ID by name or stringified ID
    #
    ###########################################################################
    def name_or_id_to_id(self, name):
        if name.isnumeric() or name[0] == "-" and name[1:].isnumeric():
            return int(name)
        return self.name_to_id(name)

    ###########################################################################
    #
    # Look up a name by ID
    #
    ###########################################################################
    def id_to_name(self, ugid):
        if ugid not in self.__id2name:
            self.precache_id(ugid)
            self.do_look_up_pr_ids()
        return self.__id2name[ugid].name()

    ###########################################################################
    #
    # Note that a name is unknown
    #
    ###########################################################################
    def name_is_unknown(self, name):
        if name in self.__names_to_lookup:
            self.__names_to_lookup.remove(name)
        if name not in self.__name2id:
            entry = AFS_PR_Entry(name, None)
            self.__name2id[name] = entry

    ###########################################################################
    #
    # Evict a name and the corresponding ID from the cache
    #
    ###########################################################################
    def evict_name(self, name):
        if name in self.__name2id:
            ugid = self.__name2id[name].ugid()
            del self.__name2id[name]
            if ugid != None:
                del self.__id2name[ugid]

    ###########################################################################
    #
    # Evict an id and the corresponding name from the cache
    #
    ###########################################################################
    def evict_id(self, ugid):
        if ugid in self.__id2name:
            name = self.__id2name[ugid].name()
            del self.__id2name[ugid]
            if name != None:
                del self.__name2id[name]

    ###########################################################################
    #
    # Note that an ID is unknown
    #
    ###########################################################################
    def id_is_unknown(self, ugid):
        if ugid in self.__ids_to_lookup:
            self.__ids_to_lookup.remove(ugid)
        if ugid not in self.__id2name:
            entry = AFS_PR_Entry(None, ugid)
            self.__id2name[ugid] = entry

    ###########################################################################
    #
    # Do the pending groups lookups
    #
    ###########################################################################
    def do_look_up_group(self, gid):
        verbose("Look up group ", gid, "\n")
        assert(gid < 0)
        ret = self.__cell.call_pt_server(self.__params, kafs.PR_ListElements, gid)
        entries = ret.elist
        self.__groups[gid] = pr_group(gid, entries)

    ###########################################################################
    #
    # Look up a group by ID
    #
    ###########################################################################
    def id_to_group_object(self, gid):
        assert(gid < 0)
        if gid not in self.__groups:
            self.do_look_up_group(gid)
        return self.__groups[gid]

    def id_to_group(self, gid):
        assert(gid < 0)
        return self.id_to_group_object(gid).members()

    ###########################################################################
    #
    # Query if we have a group yet
    #
    ###########################################################################
    def have_group(self, gid):
        assert(gid < 0)
        return gid in self.__groups

    ###########################################################################
    #
    # Get list of known groups
    #
    ###########################################################################
    def known_groups(self):
        return self.__groups.keys()

    ###########################################################################
    #
    # Return the membership of a group, expanded to recursively turn all
    # subgroups into their constituent members
    #
    ###########################################################################
    def id_to_expanded_group(self, gid):
        assert(gid < 0)
        group = self.__groups[gid]
        return group.expand(self)

    ###########################################################################
    #
    # Evict all group records from the group cache
    #
    ###########################################################################
    def evict_groups(self):
        self.__groups = dict()
