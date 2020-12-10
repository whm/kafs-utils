/* Python RxRPC connection container object
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
#include "structmember.h"
#include <arpa/inet.h>
#include "py_rxgen.h"
#include "rxgen.h"

#if 0
/*
 * Send an RPC call.
 */
static PyObject *py_rx_conn_send(PyObject *_self, PyObject *args)
{
	struct py_rx_connection *self = (struct py_rx_connection *)_self;
	self->x = NULL;
	return 0;
}

/*
 * Methods applicable to RxRPC connections
 */
static PyMethodDef py_rx_connection_methods[] = {
	{"send", (PyCFunction)py_rx_conn_send, METH_VARARGS,
	"" },
	{}
};
#endif

/*
 * RxRPC connection container.
 */
static int
py_rx_connection_init(PyObject *_self, PyObject *args, PyObject *kwds)
{
	struct py_rx_connection *self = (struct py_rx_connection *)_self;
	self->x = NULL;
	return 0;
}

static void
py_rx_connection_dealloc(struct py_rx_connection *self)
{
	if (self->x) {
		rx_close_connection(self->x);
		self->x = NULL;
	}
	Py_TYPE(self)->tp_free((PyObject *)self);
}

PyTypeObject py_rx_connectionType = {
	PyVarObject_HEAD_INIT(NULL, 0)
	"kafs.rx_connection",		/*tp_name*/
	sizeof(struct py_rx_connection),	/*tp_basicsize*/
	0,				/*tp_itemsize*/
	(destructor)py_rx_connection_dealloc, /*tp_dealloc*/
	0,				/*tp_print*/
	0,				/*tp_getattr*/
	0,				/*tp_setattr*/
	0,				/*tp_compare*/
	0,				/*tp_repr*/
	0,				/*tp_as_number*/
	0,				/*tp_as_sequence*/
	0,				/*tp_as_mapping*/
	0,				/*tp_hash */
	0,				/*tp_call*/
	0,				/*tp_str*/
	0,				/*tp_getattro*/
	0,				/*tp_setattro*/
	0,				/*tp_as_buffer*/
	Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE, /*tp_flags*/
	"RxRPC connection container",	/* tp_doc */
	0,				/* tp_traverse */
	0,				/* tp_clear */
	0,				/* tp_richcompare */
	0,				/* tp_weaklistoffset */
	0,				/* tp_iter */
	0,				/* tp_iternext */
	0,				/* tp_methods */
	0,				/* tp_members */
	0,				/* tp_getset */
	0,				/* tp_base */
	0,				/* tp_dict */
	0,				/* tp_descr_get */
	0,				/* tp_descr_set */
	0,				/* tp_dictoffset */
	py_rx_connection_init,		/* tp_init */
	0,				/* tp_alloc */
	0,				/* tp_new */
};

/*
 * Set up an RxRPC connection.
 */
PyObject *
kafs_py_rx_new_connection(PyObject *_self, PyObject *args)
{
	struct py_rx_connection *obj;
	struct rx_connection *z_conn;
	union {
		struct sockaddr sa;
		struct sockaddr_in sin;
		struct sockaddr_in6 sin6;
	} sa;
	const char *address = NULL, *key = NULL;
	socklen_t salen;
	uint16_t port, service, local_port = 0, local_service = 0;
	int exclusive = 0, security = 0;

	if (!PyArg_ParseTuple(args, "sHHzi|HHp",
			      &address, &port, &service, &key, &security,
			      &local_port, &local_service, &exclusive))
		return NULL;

	memset(&sa, 0, sizeof(sa));
	if (inet_pton(AF_INET, address, &sa.sin.sin_addr)) {
		sa.sin.sin_family = AF_INET;
		sa.sin.sin_port = htons(port);
		salen = sizeof(sa.sin);
	} else if (inet_pton(AF_INET6, address, &sa.sin.sin_addr)) {
		sa.sin6.sin6_family = AF_INET6;
		sa.sin6.sin6_port = htons(port);
		salen = sizeof(sa.sin6);
	} else {
		return PyErr_Format(PyExc_RuntimeError,
				    "Unsupported network address '%s'", address);
	}

	obj = (struct py_rx_connection *)_PyObject_New(&py_rx_connectionType);
	if (!obj)
		return PyExc_MemoryError;
	py_rx_connection_init((PyObject *)obj, NULL, NULL);
	assert(obj->x == NULL);

	z_conn = rx_new_connection(&sa.sa, salen, service,
				   local_port, local_service, exclusive,
				   key, security);
	if (!z_conn) {
		Py_DECREF(obj);
		return errno == ENOMEM ? PyExc_MemoryError :
			PyErr_SetFromErrno(PyExc_IOError);
	}
	obj->x = z_conn;
	return (PyObject *)obj;
}
