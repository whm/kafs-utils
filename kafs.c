/* kAFS python module
 *
 * Copyright (C) 2014 Red Hat, Inc. All Rights Reserved.
 * Written by David Howells (dhowells@redhat.com)
 *
 * This program is free software; you can redistribute it and/or
 * modify it under the terms of the GNU General Public Licence
 * as published by the Free Software Foundation; either version
 * 2 of the Licence, or (at your option) any later version.
 */

#include <Python.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include "structmember.h"
#include "kafs.h"
#include "afs_py.h"

#if 0
/*
 * The static methods.
 */
static PyMethodDef module_methods[] = {
	{"new_vlocation", (PyCFunction)kafs_new_vlocation, METH_NOARGS,
	 "Create a new vlocation record."
	},
	{"VL_GetEntryByName", (PyCFunction)kafs_VL_GetEntryByName, METH_VARARGS,
	 "Look up an entry by name."
	},
	{NULL}  /* Sentinel */
};
#endif

/*
 * Initialise the module.
 */
#ifndef PyMODINIT_FUNC	/* declarations for DLL import/export */
#define PyMODINIT_FUNC void
#endif
PyMODINIT_FUNC
PyInit_kafs(void)
{
	PyObject *m;

	m = pykafs_load_wrappers();
	if (!m) {
#if PY_VERSION_HEX >= 0x03000000
		return NULL;
#else
		return;
#endif
	}

#if 0
	PyModule_AddIntConstant(m, "RWVOL",		AFSVL_RWVOL);
	PyModule_AddIntConstant(m, "ROVOL",		AFSVL_ROVOL);
	PyModule_AddIntConstant(m, "BACKVOL",		AFSVL_BACKVOL);

	PyModule_AddIntConstant(m, "RWVOL_EXISTS",	AFS_VLF_RWEXISTS);
	PyModule_AddIntConstant(m, "ROVOL_EXISTS",	AFS_VLF_ROEXISTS);
	PyModule_AddIntConstant(m, "BACKVOL_EXISTS",	AFS_VLF_BACKEXISTS);

	PyModule_AddIntConstant(m, "NEWREPSITE",	AFS_VLSF_NEWREPSITE);
	PyModule_AddIntConstant(m, "ROVOL_HERE",	AFS_VLSF_ROVOL);
	PyModule_AddIntConstant(m, "RWVOL_HERE",	AFS_VLSF_RWVOL);
	PyModule_AddIntConstant(m, "BACKVOL_HERE",	AFS_VLSF_BACKVOL);
#endif

#if PY_VERSION_HEX >= 0x03000000
	return m;
#else
	return;
#endif
}
