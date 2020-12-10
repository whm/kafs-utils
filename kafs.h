/* kAFS interface
 *
 * Copyright (C) 2014 Red Hat, Inc. All Rights Reserved.
 * Written by David Howells (dhowells@redhat.com)
 *
 * This program is free software; you can redistribute it and/or
 * modify it under the terms of the GNU General Public Licence
 * as published by the Free Software Foundation; either version
 * 2 of the Licence, or (at your option) any later version.
 */

#ifndef _KAFS_H
#define _KAFS_H

/*
 * type_vlocation.c
 */
extern PyTypeObject vlocationType;
extern PyObject *kafs_new_vlocation(PyObject *_self, PyObject *args);
extern PyObject *kafs_VL_GetEntryByName(PyObject *_self, PyObject *args);


#endif /* _KAFS_H */
