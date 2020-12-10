#
# AFS Volume management toolkit: File server record
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
from afs.lib.server import server

class fileserver(server):
    """Represents an AFS File server.  We hold the server address here."""
    def __init__(self, name):
        verbose("New FileServer ", name, "\n")
        server.__init__(self, name)

    def __repr__(self):
        return "<" + "AFSFS:" + server.__str_(self) + ">"
