#
# AFS Volume management toolkit: IP Address cache
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
from socket import gethostbyname_ex, gethostbyaddr, gaierror, herror
import sys
import ipaddress

cache_n2a = dict()
cache_a2n = dict()

def add(name, addr):
    global cache_n2a, cache_a2n
    name = name.lower().rstrip(".")
    if name not in cache_n2a:
        cache_n2a[name] = []
    if str(addr) not in cache_n2a[name]:
        cache_n2a[name].append(addr)
    cache_a2n[str(addr)] = name

def add_ghb(name, addr, result):
    hostname, aliaslist, ipaddrlist = result
    if addr and str(addr) not in ipaddrlist:
        print("Inconsistent lookup of '", str(addr), "'", file=sys.stderr)
    for i in ipaddrlist:
        if name:
            add(name, ipaddress.IPv4Address(i))
        add(hostname, ipaddress.IPv4Address(i))
        for j in aliaslist:
            add(j, ipaddress.IPv4Address(i))

###############################################################################
#
# Convert a name to an array of addresses in string form (eg. "1.2.3.4").
#
###############################################################################
def name2addrs(name):
    global cache_n2a

    try:
        addr = ipaddress.ip_address(name)
        if addr.version == 6:
            raise exception.AFSNetAddressError("IPv6 is not currently supported")
        return str(addr)
    except ValueError:
        pass

    name = name.lower().rstrip(".")
    if name in cache_n2a:
        return cache_n2a[name]

    try:
        result = gethostbyname_ex(name)
    except gaierror as e:
        raise exception.AFSNetAddressError("Couldn't resolve '" + name + "'")
    add_ghb(name, None, result)

    return cache_n2a[name]

###############################################################################
#
# Convert a string address to an address
#
###############################################################################
def addr2addr(name):
    try:
        addr = ipaddress.ip_address(name)
        if addr.version == 6:
            raise exception.AFSNetAddressError("IPv6 is not currently supported")
        return addr
    except ValueError:
        raise exception.AFSNetAddressError("Can't translate '" +  name + "' to integer")

###############################################################################
#
# Convert a name or string address to an address
#
###############################################################################
def name2addr(name):
    global cache_n2a

    # Try parsing as a numeric IPv4 address
    try:
        addr = ipaddress.ip_address(name)
        if addr.version == 6:
            raise exception.AFSNetAddressError("IPv6 is not currently supported")
        return addr
    except ValueError:
        pass

    if name not in cache_n2a:
        return None
    return cache_n2a[name][0]

###############################################################################
#
# Convert one of a set of presumably synonymous addresses to a name.  We assume
# that this will be an N:1 mapping.
#
###############################################################################
def addrs2name(addrs):
    global cache_a2n
    cooked_addrs = []
    for addr in addrs:
        if str(type(addr)) != "<class 'IPv4Address'>":
            addr = ipaddress.ip_address(addr)
            cooked_addrs.append(addr)
        else:
            cooked_addrs.append(addr)
        if str(addr) in cache_a2n:
            return cache_a2n[str(addr)]

    for addr in addrs:
        try:
            result = gethostbyaddr(str(addr))
            add_ghb(None, addr, result)
            return cache_a2n[str(addr)]
        except herror:
            pass

    return None

def addr2name(addr):
    return addrs2name([ addr ])

###############################################################################
#
# Resolve an integer or string address to a string address or a name,
# depending on whether "noresolve" is set.
#
###############################################################################
def resolve(params, addr):
    if str(type(addr)) != "<class 'IPv4Address'>" and str(type(addr)) != "<class 'IPv6Address'>":
        addr = ipaddress.ip_address(addr)
    if "noresolve" in params:
        return str(addr)
    name = addr2name(addr)
    if name == None:
        return str(addr)
    return name

###############################################################################
#
# Convert an integer or a string address to an address.
#
###############################################################################
def addr2addr(addr):
    if str(type(addr)) != "<class 'IPv4Address'>" and str(type(addr)) != "<class 'IPv6Address'>":
        addr = ipaddress.ip_address(addr)
    if addr.version == 6:
        raise exception.AFSNetAddressError("IPv6 is not currently supported")
    return addr
