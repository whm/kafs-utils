#!/usr/bin/python3

import dns.resolver;

vladdrs = [];
answers = dns.resolver.query('grand.central.org', 'AFSDB');
for record in answers:
    print("--", record.hostname, "--");
    A_recs = dns.resolver.query(record.hostname, 'A');
    for addr in A_recs:
        vladdrs.append(addr.address);
    print(vladdrs);
