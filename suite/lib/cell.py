#
# AFS Volume management toolkit: Cell record
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
from afs.lib.vlserver import vlserver
from afs.lib.server import ServerError
from afs.lib.prcache import prcache
from afs.lib.output import *
import dns.resolver
import linecache
import kafs

class CellError(exception.AFSException):
    """Error raised by L{cell} objects."""

class cell:
    """Represents an AFS cell.  We hold the cell name here and the list of
    VL servers once we've looked it up"""
    def __init__(self, name = None):
        if name == None:
            name = linecache.getline("/etc/afs/ThisCell", 1)
            name = name.strip()
            verbose("Default Cell: ", name, "\n")
            if name != "":
                verbose("Found ", name, "\n")
            else:
                raise CellError("Couldn't determine default cell")

        verbose("New Cell ", name, "\n")
        self.__name = name
        self.__looked_up = False
        self.__vlserver_names = dict()
        self.__vlservers = []
        self.__vlconn = None
        self.__ptserver_index = None
        self.__ptconn = None
        self.__prcache = None

    def __repr__(self):
        return "<" + "AFS:" + self.__name + ">"

    def __str__(self):
        return self.__name

    def add_server(self, dnstype, name, addr=None):
        n = str(name).lower().rstrip(".")
        if n not in self.__vlserver_names:
            s = vlserver(n, addr)
            self.__vlserver_names[n] = s
            self.__vlservers.append(s)

    # Look up the servers
    def look_up_vl_servers(self):
        verbose("-- Find VL servers for cell: ", self.__name, " --\n")

        # Start by looking for SRV records in the DNS
        try:
            for SRV in dns.resolver.query("_afs3-vlserver._udp." + self.__name, "SRV"):
                self.add_server("SRV", SRV.target)
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
            verbose("Couldn't find any SRV records\n")

        # Then we look for AFSDB records in the DNS
        try:
            for AFSDB in dns.resolver.query(self.__name, "AFSDB"):
                self.add_server("AFSDB", AFSDB.hostname)
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
            verbose("Couldn't find any AFSDB records\n")

        # Then parse the local afsdb file
        #
        # There is a problem here: the CellServDB file is liable to contain
        # accented characters that aren't UTF-8, so we *have* to be set an
        # appropriate encoding otherwise Python will raise an exception.
        # Unfortunately, the character set for this file has not been
        # standardised...
        #
        verbose("-- Searching CellServDB for cell: ", self.__name, " --\n")
        found_cell = False
        for line in open("/etc/openafs/CellServDB", "r", encoding="iso8859_1"):
            line = str(line.rstrip())
            if line == "":
                continue
            comment_ix = line.find("#")
            if comment_ix == 0:
                continue
            comment = ""
            if comment_ix > 0:
                comment = line[comment_ix + 1:].lstrip()
                line = line[:comment_ix].rstrip()
            if line[0] == ">":
                # New cell name
                if found_cell:
                    break
                if line[1:] == self.__name:
                    found_cell = True
                continue
            if found_cell:
                self.add_server("CellServDB", comment, line)

        self.__looked_up = True

    # Get the VLDB database server list for the cell
    def query_vl_servers(self):
        if not self.__looked_up:
            self.look_up_vl_servers()
        if not self.__vlservers:
            raise CellError("Couldn't find any VL servers")
        return self.__vlservers

    # Force a particular set of servers
    def override_vlserver_list(self, servers):
        self.__vlservers = servers
        for i in servers:
            self.__vlserver_names[str(i)] = i
        self.__looked_up = True

    # Get the VLDB database server addresses for the cell
    def query_vl_addrs(self):
        addrs = []
        for i in self.query_vl_servers():
            try:
                for j in i.addrs():
                    if j not in addrs:
                        addrs.append(j)
            except ServerError:
                pass

        if len(addrs) == 0:
            raise CellError("Couldn't find any VL servers in cell")

        return addrs

    # Determine the cell security
    def determine_security(self, params):
        key = None
        security = 0
        if params:
            key = "afs@" + self.__name.upper()
            if "localauth" in params:
                raise RuntimeError("Don't support -localauth yet")
            elif "noauth" in params:
                security = 0
                key = None
            elif "encrypt" in params:
                security = kafs.RXRPC_SECURITY_ENCRYPT
            else:
                security = kafs.RXRPC_SECURITY_PLAIN
        return (key, security)

    # Open a VL Server connection
    def open_vl_server(self, params=None):
        if self.__vlconn:
            return

        key, security = self.determine_security(params)

        for vladdr in self.query_vl_addrs():
            verbose("Trying vlserver ", vladdr, "\n")

            z_conn = kafs.rx_new_connection(str(vladdr), kafs.VL_PORT, kafs.VL_SERVICE,
                                            key, security)
            try:
                ret = kafs.VL_Probe(z_conn)
                self.__vlconn = z_conn
                break
            except ConnectionRefusedError:
                pass
            del z_conn
        else:
            raise CellError("Couldn't connect to a VL server")

        return self.__vlconn

    # Open a Volume Server connection
    def open_volume_server(self, server, params=None):
        key, security = self.determine_security(params)

        verbose("Trying volserver ", server.addr(), "\n")
        vol_conn = kafs.rx_new_connection(str(server.addr()),
                                          kafs.VOLSERVICE_PORT,
                                          kafs.VOLSERVICE_ID,
                                          key, security)
        return vol_conn

    # Open a BOS Server connection
    def open_bos_server(self, server, params=None):
        key, security = self.determine_security(params)

        verbose("Trying bosserver ", server.addr(), "\n")
        bos_conn = kafs.rx_new_connection(str(server.addr()),
                                          kafs.BOSSERVICE_PORT,
                                          kafs.BOSSERVICE_ID,
                                          key, security)
        return bos_conn

    # Open a Protection Server connection
    def open_pt_server(self, params=None):
        if self.__ptserver_index == None:
            self.__ptservers = self.query_vl_addrs()
            self.__ptserver_index = 0

        if self.__ptserver_index >= len(self.__ptservers):
            raise CellError("Couldn't connect to a PT server")
        server = self.__ptservers[self.__ptserver_index]

        key, security = self.determine_security(params)

        verbose("Trying ptserver ", server, "\n")

        pt_conn = kafs.rx_new_connection(str(server),
                                         kafs.PR_PORT,
                                         kafs.PR_SERVICE,
                                         key, security)
        return pt_conn

    # Find and call out to a working protection server
    def call_pt_server(self, params, rpc, *args):
        while True:
            if not self.__ptconn:
                self.__ptconn = self.open_pt_server(params)
            try:
                return rpc(self.__ptconn, *args)
            except ConnectionRefusedError:
                # Move on to the next server
                verbose("Connection refused\n");
            except kafs.AbortUNOTSYNC:
                verbose("Server is not synchronised\n");
            except OSError as e:
                verbose(e, "\n");
            self.__ptconn = None
            self.__ptserver_index += 1

    # Get the prcache for this cell
    def get_prcache(self, params):
        if self.__prcache == None:
            self.__prcache = prcache(params, self)
        return self.__prcache
