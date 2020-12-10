#
# AFS Volume management toolkit: Server record
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
import afs.lib.addrcache as addrcache
from afs.lib.output import *

class ServerError(exception.AFSException):
    """Error raised by L{volserver} objects."""

class server:
    """Represents the name and addresses of a server on the network."""
    def __init__(self, name, addr=None):
        self.__name = None
        self.__addrs4 = None
        self.__addrs6 = None

        try:
            self.__addrs4 = [ addrcache.addr2addr(name) ]
        except ValueError:
            self.__name = name

        if addr != None:
            self.__addrs4 = [ addrcache.addr2addr(addr) ]

    def __repr__(self):
        if self.__name != None:
            name = self.__name
        else:
            name = self.__addrs4[0]
        return "<" + "server:" + name + ">"

    def __str__(self):
        if self.__name != None:
            name = self.__name
        else:
            name = self.__addrs4[0]
        return name

    def look_up_name(self):
        if self.__name == None:
            self.__name = addrcache.addrs2name(self.__addrs4)
        if self.__name == None:
            self.__name = self.__addrs4[0]
        return self.__name

    def look_up_addresses(self):
        if self.__addrs4 == None:
            self.__addrs4 = addrcache.name2addrs(self.__name)
        if len(self.__addrs4) == 0:
            raise ServerError("No addresses available for '" + self.__name + "'")
        return self.__addrs4

    def name(self):
        return self.look_up_name()

    def addrs(self):
        return self.look_up_addresses()

    def addr(self):
        return self.look_up_addresses()[0]

    def integer_addr(self):
        if self.__inaddr == None:
            self.__inaddr = addrcache.addr2addr_int(self.look_up_addresses()[0])
        return self.__inaddr
