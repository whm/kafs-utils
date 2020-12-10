/* rxgen split-mode RPC call Python support
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
#include <poll.h>
#include <arpa/inet.h>
#include <assert.h>
#include "py_rxgen.h"
#include "afs_py.h"
#include "rxgen.h"

#define debug(fmt, ...) do { if (0) printf(fmt, ## __VA_ARGS__); } while (0)

static int py_rx_split_do_recv(struct rx_call *call,
			       struct py_rx_split_info *split_info)
{
	struct pollfd fds[1];

	fds[0].fd = call->conn->fd;
	fds[0].events = POLLIN;
	fds[0].revents = 0;
	poll(fds, 1, 0);
	if (fds[0].revents & POLLIN)
		rxrpc_recv_data(call->conn, true);
	return 0;
}

static int py_rx_split_do_send_recv(struct rx_call *call,
				    struct py_rx_split_info *split_info,
				    bool more)
{
	if (!more) {
		call->more_send = 0;
		split_info->split_state = split_idle;
	}
	if (rxrpc_send_data(call) == -1)
		return -1;

	return py_rx_split_do_recv(call, split_info);
}

/*
 * Send an RPC call: split_info.send(data, more)
 */
static PyObject *py_rx_split_send(PyObject *_self, PyObject *args)
{
	struct py_rx_split_info *split_info = (struct py_rx_split_info *)_self;
	struct rx_call *call = split_info->call;
	Py_buffer data;
	int more = 0;

	if (!call)
		abort();

	if (split_info->split_state != split_transmitting)
		abort();

	if (!PyArg_ParseTuple(args, "y*p", &data, &more))
		return NULL;

	if (py_enc_buffer_raw(call, &data, UINT_MAX) == -1)
		return PyErr_SetFromErrno(PyExc_OSError);

	if (py_rx_split_do_send_recv(call, split_info, more) < 0)
		return PyErr_SetFromErrno(PyExc_OSError);

	Py_RETURN_NONE;
}

/*
 * Request reception of some data, where the amount of data is potentially
 * zero.  This can only be used if there is no non-split data to be received
 * after the split data as this commits the caller to handling all the
 * remaining data in this phase.
 *
 * The caller should use split_info.data_available() to work out how much data
 * is available, if any.
 */
static PyObject *py_rx_split_will_recv_all(PyObject *_self, PyObject *args)
{
	struct py_rx_split_info *split_info = (struct py_rx_split_info *)_self;
	struct rx_call *call = split_info->call;

	call->need_size = UINT_MAX;
	Py_RETURN_NONE;
}

/*
 * Receive a fixed-size object: ret = split_info.begin_recv(buffer)
 *
 * The object's intrinsic size is used to determine how much data we want for
 * it.  Potentially 0-length, variable sized data cannot be handled this way.
 *
 * Returns NULL on error; True on success (ie. may be more to receive).
 */
static PyObject *py_rx_split_begin_recv(PyObject *_self, PyObject *args)
{
	struct py_rx_split_info *split_info = (struct py_rx_split_info *)_self;
	struct rx_call *call = split_info->call;
	Py_buffer buffer;
	int ret, padded = 1;

	if (!call)
		abort();
	if (split_info->split_state != split_receiving)
		abort();

	if (!PyArg_ParseTuple(args, "w*|p", &buffer, &padded))
		return NULL;

	ret = py_dec_init_buffer(call, &buffer, padded);
	switch (ret) {
	case -1: return NULL;
	case  0: split_info->state++; Py_RETURN_TRUE;
	case  1: split_info->receiving_data = true; Py_RETURN_TRUE;
	default: abort();
	}
}

/*
 * Query how much data is in the Rx buffers of an RPC call: n = split_info.data_available()
 */
static PyObject *py_rx_split_data_available(PyObject *_self, PyObject *args)
{
	struct py_rx_split_info *split_info = (struct py_rx_split_info *)_self;
	struct rx_call *call = split_info->call;

	switch (call->state) {
	case rx_call_cl_decoding_response:
	case rx_call_sv_decoding_opcode:
	case rx_call_sv_decoding_params:
		break;
	default:
		/* Aborted or some other error */
		return NULL;
	}

	debug("DAVAIL: %u %d\n", call->data_count, call->more_recv);

	if (call->data_count > 0 || call->more_recv)
		return PyLong_FromUnsignedLong(call->data_count);
	else
		Py_RETURN_NONE;
}

/*
 * Methods applicable to split-call objects
 */
static PyMethodDef py_rx_split_info_methods[] = {
	{"send", (PyCFunction)py_rx_split_send, METH_VARARGS,
	 "" },
	{"will_recv_all", (PyCFunction)py_rx_split_will_recv_all, METH_NOARGS,
	 "" },
	{"begin_recv", (PyCFunction)py_rx_split_begin_recv, METH_VARARGS,
	 "" },
	{"data_available", (PyCFunction)py_rx_split_data_available, METH_NOARGS,
	 "" },
	{}
};

static PyMemberDef py_rx_split_info_members[] = {
	{ "state", T_UINT, offsetof(struct py_rx_split_info, state), 0, ""},
	{ "target",  T_OBJECT, offsetof(struct py_rx_split_info, target), 0, ""},
	{}
};

/*
 * RxRPC split container.
 */
static int
py_rx_split_init(PyObject *_self, PyObject *args, PyObject *kwds)
{
	struct py_rx_split_info *self = (struct py_rx_split_info *)_self;
	self->call = NULL;
	self->target = NULL;
	self->split_state = split_idle;
	self->state = 0;
	self->receiving_data = false;
	return 0;
}

static void
py_rx_split_dealloc(struct py_rx_split_info *self)
{
	assert(self->split_state != split_dead);
	self->split_state = split_dead;
	self->call = NULL;
	Py_XDECREF(self->target);
	Py_TYPE(self)->tp_free((PyObject *)self);
}

PyTypeObject py_rx_split_infoType = {
	PyVarObject_HEAD_INIT(NULL, 0)
	"kafs.rx_split_info",		/*tp_name*/
	sizeof(struct py_rx_split_info), /*tp_basicsize*/
	0,				/*tp_itemsize*/
	(destructor)py_rx_split_dealloc, /*tp_dealloc*/
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
	"RxRPC split container",	/* tp_doc */
	0,				/* tp_traverse */
	0,				/* tp_clear */
	0,				/* tp_richcompare */
	0,				/* tp_weaklistoffset */
	0,				/* tp_iter */
	0,				/* tp_iternext */
	py_rx_split_info_methods,	/* tp_methods */
	py_rx_split_info_members,	/* tp_members */
	0,				/* tp_getset */
	0,				/* tp_base */
	0,				/* tp_dict */
	0,				/* tp_descr_get */
	0,				/* tp_descr_set */
	0,				/* tp_dictoffset */
	py_rx_split_init,		/* tp_init */
	0,				/* tp_alloc */
	0,				/* tp_new */
};

/*
 * Allocate an information object.
 */
PyObject *py_rxgen_split_client_prepare(void)
{
	struct py_rx_split_info *obj;

	obj = (struct py_rx_split_info *)_PyObject_New(&py_rx_split_infoType);
	if (!obj)
		return PyErr_NoMemory();
	py_rx_split_init((PyObject *)obj, NULL, NULL);
	return (PyObject *)obj;
}

/*
 * Perform split-RPC transmission.
 */
int py_rxgen_split_transmit(struct rx_call *call)
{
	struct py_rx_split_info *split_info = call->decoder_split_info;
	PyObject *callback = call->decoder_split_callback;
	PyObject *result;
	int ret;

	assert(split_info->split_state == split_idle);

	split_info->split_state = split_transmitting;
	result = PyObject_CallMethod(callback, "transmit",
				     "O", call->decoder_split_info);
	if (result == Py_None) {
		ret = py_rx_split_do_send_recv(call, split_info, false);
	} else if (result) {
		ret = PyObject_IsTrue(result) ? 0 : -1;
		Py_DECREF(result);
	} else {
		ret = -1;
	}
	if (ret == 0 && split_info->split_state != split_idle)
		abort();
	return ret;
}

/*
 * Perform split-RPC reception.
 */
int py_rxgen_split_receive(struct rx_call *call, bool init)
{
	struct py_rx_split_info *split_info = call->decoder_split_info;
	PyObject *callback = call->decoder_split_callback;
	PyObject *result;
	int ret;

	assert(split_info->split_state == split_idle);

	debug("-->%s(%u,%u,%u)\n", __func__, init, split_info->state, split_info->receiving_data);

	if (init)
		split_info->state = 0;

again:
	if (split_info->receiving_data) {
		switch (py_dec_into_buffer(call)) {
		case -1:
			result = PyObject_CallMethod(callback, "receive_failed",
						     "O", call->decoder_split_info);
			Py_XDECREF(result);
			return -1;
		case  1: /* More data needed */
			return 1;
		case  0:
			split_info->receiving_data = false;
			split_info->state++;
			break;
		}
	}

	split_info->split_state = split_receiving;
	result = PyObject_CallMethod(callback, "receive",
				     "O", call->decoder_split_info);
	split_info->split_state = split_idle;

	if (!result)
		return -1;

	if (result == Py_None) {
		/* Split receive phase not used */
		call->need_size = 0;
		ret = 0;
	} else if (result == Py_False) {
		/* Split receive phase complete */
		ret = 0;
	} else if (result == Py_True) {
		/* Wanting to receive data or reenter in a new state */
		if (split_info->receiving_data)
			goto again;
		ret = 1;
	} else {
		PyErr_Format(PyExc_TypeError,
			     "Expected True, False or None return from split receive function");
		ret = -1;
	}
	Py_DECREF(result);
	return ret;
}
