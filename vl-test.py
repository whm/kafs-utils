#!/usr/bin/python3
#
# Use VLDB record look-up-by-name to test the infrastructure.
#
# Copyright (C) 2014 Red Hat, Inc. All Rights Reserved.
# Written by David Howells (dhowells@redhat.com)
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public Licence
# as published by the Free Software Foundation; either version
# 2 of the Licence, or (at your option) any later version.
#

import sys;
import getopt;
import dns.resolver;
import kafs;

cell = "grand.central.org";
volumes = [ "root.cell" ];

# The user can specify the cell and provide a list of volume names
opts, args = getopt.getopt(sys.argv[1:], "c:", [ "cell=" ]);
for o, a in opts:
    if o == "-c":
        cell = a;

if args:
    volumes = args;

print("-- Find VL servers for cell:", cell, "--");

# Find a list of Volume Location servers to contact
vladdrs = set();
try:
    for SRV in dns.resolver.query("_afs3-vlserver._udp." + cell, "SRV"):
        for A in dns.resolver.query(SRV.target, 'A'):
            vladdrs.add(A.address);
        print("SRV:", SRV.target, ":", vladdrs);
except dns.resolver.NXDOMAIN:
    print("Couldn't find any SRV records");
except dns.resolver.NoAnswer:
    print("Couldn't find any SRV records");

try:
    for AFSDB in dns.resolver.query(cell, "AFSDB"):
        for A in dns.resolver.query(AFSDB.hostname, 'A'):
            vladdrs.add(A.address);
        print("AFSDB:", AFSDB.hostname, ":", vladdrs);
except dns.resolver.NoAnswer:
    print("Couldn't find any AFSDB records");

if not vladdrs:
    raise RuntimeError("Couldn't find any VL server addresses");

# Go through the list of VLDB servers until one answers a probe request
print("-- Probe for live VLDB servers --");
for vlserver in vladdrs:
    print("Trying", vlserver);

    z_conn = kafs.rx_new_connection(vlserver, kafs.VL_PORT, kafs.VL_SERVICE);

    try:
        ret = kafs.VL_Probe(z_conn);
        break;
    except ConnectionRefusedError:
        pass;
    del z_conn;

if not z_conn:
    raise RuntimeError("Couldn't connect to a server");

# Look up each of the volumes in the list
print("-- Look up the named volumes --");
for vol in volumes:
    ret = kafs.VL_GetEntryByName(z_conn, vol);
    vldb = ret.entry;

    servers = set();

    print("[", vldb.name, "]");
    print("\tnum\t", vldb.nServers);
    print("\ttype\t", vldb.volumeType);
    print("\tvid\t", vldb.volumeId);
    print("\tflags\t {:x}".format(vldb.flags));
    for j in vldb.serverNumber:
        if j:
            servers.add(j);

    # Pick an arbitrary server serving that volume and find out what volumes
    # that server serves
    attributes = kafs.VldbListByAttributes();
    attributes.Mask = kafs.VLLIST_SERVER;
    attributes.server = servers.pop();
    ret = kafs.VL_ListAttributes(z_conn, attributes)
    blkentries = ret.blkentries;

    for i in blkentries:
        print("->", i.name);
