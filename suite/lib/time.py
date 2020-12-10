#
# AFS Volume management toolkit: Standard AFS date and time display format
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

import datetime

def time2str(time):
    t = datetime.datetime.fromtimestamp(time)
    return t.strftime("%a %b %d %H:%M:%S %Y")

def time2str_or_never(time):
    if time == 0:
        return "Never"
    t = datetime.datetime.fromtimestamp(time)
    return t.strftime("%a %b %d %H:%M:%S %Y")
