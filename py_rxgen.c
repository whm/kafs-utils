/* rxgen Python wrapping support
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
#include "afs_py.h"
#include "rxgen.h"

#define debug(fmt, ...) do { if (0) printf(fmt, ## __VA_ARGS__); } while (0)

struct py_dec_index {
	unsigned long val;
	void *ptr;
};

struct py_dec_manager {
	Py_buffer view;
	struct py_dec_index top;
	struct py_dec_index indices[];
};

PyObject *py_rxgen_get_struct(const void *p, PyObject **cache,
			      PyObject *(*data_to_type)(const void *elem))
{
	PyObject *obj;

	if (*cache) {
		Py_INCREF(*cache);
		return *cache;
	}

	obj = data_to_type(p);
	if (!obj)
		return NULL;

	Py_INCREF(obj);
	*cache = obj;
	return obj;
}

int py_rxgen_set_struct(PyObject **cache, PyTypeObject *type, PyObject *val)
{
	if (!PyObject_TypeCheck(val, type)) {
		PyErr_Format(PyExc_TypeError, "Unexpected type");
		return -1;
	}
	Py_XDECREF(*cache);
	Py_INCREF(val);
	*cache = val;
	return 0;
}

int py_rxgen_premarshal_struct(void *array, size_t size, size_t offs,
			       PyObject *cache,
			       int (*premarshal)(PyObject *object))
{
	if (!cache)
		return 0;

	if (premarshal(cache) < 0)
		return -1;
	memcpy(array, (void *)cache + offs, size);
	return 0;
}

PyObject *py_rxgen_get_string(const void *_array, size_t n)
{
	const char *array = _array;
	return PyUnicode_FromStringAndSize(array, strnlen(array, n - 1));
}

int py_rxgen_set_string(void *_array, size_t n, PyObject *val)
{
	Py_ssize_t len;
	char *array = _array;
	char *new_name;

	if (!PyUnicode_Check(val))
		return -1;

	new_name = PyUnicode_AsUTF8AndSize(val, &len);
	if (!new_name)
		return -1;

	if (len < 0 || len > n - 1)
		return -1;

	memcpy(array, new_name, len);
	memset(array + len, 0, n - len);
	return 0;
}

PyObject *py_rxgen_get_uint8(const void *_array, size_t n, PyObject **cache)
{
	PyObject *list;
	const uint8_t *array = _array;
	int i;

	if (*cache) {
		Py_INCREF(*cache);
		return *cache;
	}

	list = PyList_New(n);
	if (!list)
		return NULL;

	for (i = 0; i < n; i++) {
		PyObject *num = PyLong_FromUnsignedLong(array[i]);
		if (!num)
			goto error;

		if (PyList_SetItem(list, i, num) != 0) {
			Py_DECREF(num);
			goto error;
		}
	}

	Py_INCREF(list);
	*cache = list;
	return list;

error:
	Py_DECREF(list);
	return NULL;
}

PyObject *py_rxgen_get_int8(const void *_array, size_t n, PyObject **cache)
{
	PyObject *list;
	const int8_t *array = _array;
	int i;

	if (*cache) {
		Py_INCREF(*cache);
		return *cache;
	}

	list = PyList_New(n);
	if (!list)
		return NULL;

	for (i = 0; i < n; i++) {
		PyObject *num = PyLong_FromLong(array[i]);
		if (!num)
			goto error;

		if (PyList_SetItem(list, i, num) != 0) {
			Py_DECREF(num);
			goto error;
		}
	}

	Py_INCREF(list);
	*cache = list;
	return list;

error:
	Py_DECREF(list);
	return NULL;
}

PyObject *py_rxgen_get_uint16(const void *_array, size_t n, PyObject **cache)
{
	PyObject *list;
	const uint16_t *array = _array;
	int i;

	if (*cache) {
		Py_INCREF(*cache);
		return *cache;
	}

	list = PyList_New(n);
	if (!list)
		return NULL;

	for (i = 0; i < n; i++) {
		PyObject *num = PyLong_FromUnsignedLong(array[i]);
		if (!num)
			goto error;

		if (PyList_SetItem(list, i, num) != 0) {
			Py_DECREF(num);
			goto error;
		}
	}

	Py_INCREF(list);
	*cache = list;
	return list;

error:
	Py_DECREF(list);
	return NULL;
}

PyObject *py_rxgen_get_int16(const void *_array, size_t n, PyObject **cache)
{
	PyObject *list;
	const int16_t *array = _array;
	int i;

	if (*cache) {
		Py_INCREF(*cache);
		return *cache;
	}

	list = PyList_New(n);
	if (!list)
		return NULL;

	for (i = 0; i < n; i++) {
		PyObject *num = PyLong_FromLong(array[i]);
		if (!num)
			goto error;

		if (PyList_SetItem(list, i, num) != 0) {
			Py_DECREF(num);
			goto error;
		}
	}

	Py_INCREF(list);
	*cache = list;
	return list;

error:
	Py_DECREF(list);
	return NULL;
}

PyObject *py_rxgen_get_uint32(const void *_array, size_t n, PyObject **cache)
{
	PyObject *list;
	const uint32_t *array = _array;
	int i;

	if (*cache) {
		Py_INCREF(*cache);
		return *cache;
	}

	list = PyList_New(n);
	if (!list)
		return NULL;

	for (i = 0; i < n; i++) {
		PyObject *num = PyLong_FromUnsignedLong(array[i]);
		if (!num)
			goto error;

		if (PyList_SetItem(list, i, num) != 0) {
			Py_DECREF(num);
			goto error;
		}
	}

	Py_INCREF(list);
	*cache = list;
	return list;

error:
	Py_DECREF(list);
	return NULL;
}

PyObject *py_rxgen_get_int32(const void *_array, size_t n, PyObject **cache)
{
	PyObject *list;
	const int32_t *array = _array;
	int i;

	if (*cache) {
		Py_INCREF(*cache);
		return *cache;
	}

	list = PyList_New(n);
	if (!list)
		return NULL;

	for (i = 0; i < n; i++) {
		PyObject *num = PyLong_FromLong(array[i]);
		if (!num)
			goto error;

		if (PyList_SetItem(list, i, num) != 0) {
			Py_DECREF(num);
			goto error;
		}
	}

	Py_INCREF(list);
	*cache = list;
	return list;

error:
	Py_DECREF(list);
	return NULL;
}

int py_rxgen_set_array(size_t n, PyObject **cache, PyObject *list)
{
	if (!PySequence_Check(list) ||
	    PySequence_Size(list) > n) {
		PyErr_Format(PyExc_ValueError,
			     "Expected a sequence of up to %zu size", n);
		return -1;
	}
	Py_XDECREF(*cache);
	Py_INCREF(list);
	*cache = list;
	return 0;
}

int py_rxgen_premarshal_uint8(void *_array, size_t n, PyObject *cache)
{
	PyObject *list;
	uint8_t *array = _array;
	Py_ssize_t i, c;

	if (!cache)
		return 0;

	list = PySequence_Fast(cache, "Expecting list or tuple of integers");
	if (!list)
		return -1;
	c = PySequence_Fast_GET_SIZE(list);
	if (c > n) {
		PyErr_Format(PyExc_ValueError,
			     "Expected a sequence of up to %zu size", n);
		goto error;
	}

	PyErr_Clear();
	for (i = 0; i < c; i++) {
		PyObject *p = PySequence_Fast_GET_ITEM(list, i);
		unsigned long val = PyLong_AsUnsignedLong(p);

		if (PyErr_Occurred())
			goto error;
		array[i] = val;
	}
	for (; i < n; i++)
		array[i] = 0;

	Py_DECREF(list);
	return 0;

error:
	Py_DECREF(list);
	return -1;
}

int py_rxgen_premarshal_uint16(void *_array, size_t n, PyObject *cache)
{
	PyObject *list;
	uint16_t *array = _array;
	Py_ssize_t i, c;

	if (!cache)
		return 0;

	list = PySequence_Fast(cache, "Expecting list or tuple of integers");
	if (!list)
		return -1;
	c = PySequence_Fast_GET_SIZE(list);
	if (c > n) {
		PyErr_Format(PyExc_ValueError,
			     "Expected a sequence of up to %zu size", n);
		goto error;
	}

	PyErr_Clear();
	for (i = 0; i < c; i++) {
		PyObject *p = PySequence_Fast_GET_ITEM(list, i);
		unsigned long val = PyLong_AsUnsignedLong(p);

		if (PyErr_Occurred())
			goto error;
		array[i] = val;
	}
	for (; i < n; i++)
		array[i] = 0;

	Py_DECREF(list);
	return 0;

error:
	Py_DECREF(list);
	return -1;
}

int py_rxgen_premarshal_uint32(void *_array, size_t n, PyObject *cache)
{
	PyObject *list;
	uint32_t *array = _array;
	Py_ssize_t i, c;

	if (!cache)
		return 0;

	list = PySequence_Fast(cache, "Expecting list or tuple of integers");
	if (!list)
		return -1;
	c = PySequence_Fast_GET_SIZE(list);
	if (c > n) {
		PyErr_Format(PyExc_ValueError,
			     "Expected a sequence of up to %zu size", n);
		goto error;
	}

	PyErr_Clear();
	for (i = 0; i < c; i++) {
		PyObject *p = PySequence_Fast_GET_ITEM(list, i);
		unsigned long val = PyLong_AsUnsignedLong(p);

		if (PyErr_Occurred())
			goto error;
		array[i] = val;
	}
	for (; i < n; i++)
		array[i] = 0;

	Py_DECREF(list);
	return 0;

error:
	Py_DECREF(list);
	return -1;
}

int py_rxgen_premarshal_int8(void *_array, size_t n, PyObject *cache)
{
	PyObject *list;
	int8_t *array = _array;
	Py_ssize_t i, c;

	if (!cache)
		return 0;

	list = PySequence_Fast(cache, "Expecting list or tuple of integers");
	if (!list)
		return -1;
	c = PySequence_Fast_GET_SIZE(list);
	if (c > n) {
		PyErr_Format(PyExc_ValueError,
			     "Expected a sequence of up to %zu size", n);
		goto error;
	}

	PyErr_Clear();
	for (i = 0; i < c; i++) {
		PyObject *p = PySequence_Fast_GET_ITEM(list, i);
		unsigned long val = PyLong_AsLong(p);

		if (PyErr_Occurred())
			goto error;
		array[i] = val;
	}
	for (; i < n; i++)
		array[i] = 0;

	Py_DECREF(list);
	return 0;

error:
	Py_DECREF(list);
	return -1;
}

int py_rxgen_premarshal_int16(void *_array, size_t n, PyObject *cache)
{
	PyObject *list;
	int16_t *array = _array;
	Py_ssize_t i, c;

	if (!cache)
		return 0;

	list = PySequence_Fast(cache, "Expecting list or tuple of integers");
	if (!list)
		return -1;
	c = PySequence_Fast_GET_SIZE(list);
	if (c > n) {
		PyErr_Format(PyExc_ValueError,
			     "Expected a sequence of up to %zu size", n);
		goto error;
	}

	PyErr_Clear();
	for (i = 0; i < c; i++) {
		PyObject *p = PySequence_Fast_GET_ITEM(list, i);
		unsigned long val = PyLong_AsLong(p);

		if (PyErr_Occurred())
			goto error;
		array[i] = val;
	}
	for (; i < n; i++)
		array[i] = 0;

	Py_DECREF(list);
	return 0;

error:
	Py_DECREF(list);
	return -1;
}

int py_rxgen_premarshal_int32(void *_array, size_t n, PyObject *cache)
{
	PyObject *list;
	int32_t *array = _array;
	Py_ssize_t i, c;

	if (!cache)
		return 0;

	list = PySequence_Fast(cache, "Expecting list or tuple of integers");
	if (!list)
		return -1;
	c = PySequence_Fast_GET_SIZE(list);
	if (c > n) {
		PyErr_Format(PyExc_ValueError,
			     "Expected a sequence of up to %zu size", n);
		goto error;
	}

	PyErr_Clear();
	for (i = 0; i < c; i++) {
		PyObject *p = PySequence_Fast_GET_ITEM(list, i);
		unsigned long val = PyLong_AsLong(p);

		if (PyErr_Occurred())
			goto error;
		array[i] = val;
	}
	for (; i < n; i++)
		array[i] = 0;

	Py_DECREF(list);
	return 0;

error:
	Py_DECREF(list);
	return -1;
}

PyObject *py_rxgen_get_structs(const void *data, size_t num, size_t size,
			       PyObject **cache,
			       PyObject *(*data_to_type)(const void *elem))
{
	PyObject *list, *obj;
	int i;

	if (*cache) {
		Py_INCREF(*cache);
		return *cache;
	}

	list = PyList_New(num);
	if (!list)
		return NULL;

	for (i = 0; i < num; i++) {
		obj = data_to_type(data + num * size);
		if (!obj) {
			Py_DECREF(list);
			return NULL;
		}
		PyList_SetItem(list, i, obj);
	}

	Py_INCREF(list);
	*cache = list;
	return list;
}

int py_rxgen_premarshal_structs(void *array,
				size_t n, size_t size, size_t offs,
				PyObject *cache,
				int (*premarshal)(PyObject *object))
{
	PyObject *list;
	Py_ssize_t i, c;

	list = PySequence_Fast(cache, "Expecting list or tuple of structs");
	if (!list)
		return -1;
	c = PySequence_Fast_GET_SIZE(list);
	if (c > n) {
		PyErr_Format(PyExc_ValueError,
			     "Expected a sequence of up to %zu size", n);
		goto error;
	}

	for (i = 0; i < c; i++) {
		PyObject *p = PySequence_Fast_GET_ITEM(list, i);
		if (premarshal(p) < 0)
			goto error;
		memcpy(array + i * size, (void *)p + offs, size);
	}

	if (i < n)
		memset(array + i * size, 0, (n - i) * size);

	Py_DECREF(list);
	return 0;

error:
	Py_DECREF(list);
	return -1;
}

/*
 * Assign to a python object's members from its new op's keyword list.
 */
int py_rxgen_initialise_members(PyObject *obj, PyObject *kw)
{
	const PyMemberDef *member;
	PyTypeObject *type = (PyTypeObject *)PyObject_Type(obj);
	PyObject *key, *value;
	Py_ssize_t pos = 0;

	if (!kw || PyDict_Size(kw) <= 0)
		return 0;
	if (!PyArg_ValidateKeywordArguments(kw))
		return -1;
	if (!type->tp_members || !type->tp_members[0].name) {
		PyErr_Format(PyExc_AttributeError,
			     "Calls of %s take no parameters", type->tp_name);
		return -1;
	}

	while (PyDict_Next(kw, &pos, &key, &value)) {
		for (member = type->tp_members; member->name; member++) {
			void *p = (void *)obj + member->offset;
			if (PyUnicode_CompareWithASCIIString(key, member->name) != 0)
				continue;

			switch (member->type) {
			case T_CHAR:
			case T_BYTE:
				*(uint8_t *)p = PyLong_AsLong(value);
				goto found;
			case T_SHORT:
				*(uint16_t *)p = PyLong_AsLong(value);
				goto found;
			case T_INT:
				*(uint32_t *)p = PyLong_AsLong(value);
				goto found;
			case T_LONGLONG:
				*(uint64_t *)p = PyLong_AsLongLong(value);
				goto found;
			case T_UBYTE:
				*(uint8_t *)p = PyLong_AsUnsignedLong(value);
				goto found;
			case T_USHORT:
				*(uint16_t *)p = PyLong_AsUnsignedLong(value);
				goto found;
			case T_UINT:
				*(uint32_t *)p = PyLong_AsUnsignedLong(value);
				goto found;
			case T_ULONGLONG:
				*(uint64_t *)p = PyLong_AsUnsignedLongLong(value);
				goto found;
			case T_OBJECT_EX:
				Py_INCREF(value);
				*(PyObject **)p = value;
				goto found;
			default:
				abort();
			}
		}

		PyErr_Format(PyExc_AttributeError,
			     "Calls of %s don't have parameter %S", type->tp_name, key);
		return -1;
	found:
		;
	}

	return 0;
}

/*
 * Recursively encode a standard C array.
 */
static int py_enc_c_array(struct rx_call *call,
			  const void *data, int dim,
			  const Py_ssize_t *dim_size,
			  Py_ssize_t itemsize)
{
	if (dim == 1) {
		/* Data subarray */
		rxrpc_enc_blob(call, data, *dim_size * itemsize);
		return rxrpc_post_enc(call);
	} else {
		/* Pointer subarray */
		const void *const *ptrs = data;
		Py_ssize_t i;
		for (i = 0; i < *dim_size; i++)
			if (py_enc_c_array(call, ptrs[i], dim - 1, dim_size + 1, itemsize) < 0)
				return -1;
		return 0;
	}
}

/*
 * Recursively encode a NumPy-style array.
 */
static int py_enc_numpy_array(struct rx_call *call,
			      const void *data, int dim,
			      const Py_ssize_t *dim_size,
			      const Py_ssize_t *dim_stride,
			      Py_ssize_t itemsize)
{
	int i;

	if (dim == 0)
		/* Single data item */
		return rxrpc_enc_blob(call, data, itemsize);

	for (i = 0; i < *dim_size; i++) {
		if (py_enc_numpy_array(call, data + i * *dim_stride,
				       dim - 1, dim_size + 1, dim_stride + 1, itemsize) < 0)
			return -1;
		if (dim == 1 && rxrpc_post_enc(call) < 0)
			return -1;
	}
	return 0;
}

/*
 * Recursively encode a Python Imaging Library (PIL)-style array.
 */
static int py_enc_pil_array(struct rx_call *call,
			    const void *data, int dim,
			    const Py_ssize_t *dim_size,
			    const Py_ssize_t *dim_stride,
			    const Py_ssize_t *dim_suboffset,
			    Py_ssize_t itemsize)
{
	int i;

	if (dim == 0)
		/* Single data item */
		return rxrpc_enc_blob(call, data, itemsize);

	for (i = 0; i < *dim_size; i++) {
		const void *ptr = data + i * *dim_stride;
		if (*dim_suboffset >= 0) {
			ptr = *((const void *const *)ptr);
			ptr += *dim_suboffset;
		}
		if (py_enc_pil_array(call, ptr,
				     dim - 1, dim_size + 1, dim_stride + 1, dim_suboffset + 1,
				     itemsize) < 0)
			return -1;
		if (dim == 1 && rxrpc_post_enc(call) < 0)
			return -1;
	}
	return 0;
}

/*
 * Encode the just the contents of a python buffer view, without length or
 * realignment.
 */
int py_enc_buffer_raw(struct rx_call *call, Py_buffer *view, size_t dim)
{
	if (call->error_code)
		return -1;

	if (view->ndim == 0 || (view->ndim == 1 && !view->shape)) {
		/* Simple scalar array */
		if (rxrpc_enc_blob(call, view->buf, view->len) < 0)
			return -1;
		return rxrpc_post_enc(call);
	}

	if (!view->strides)
		/* Standard C array */
		return py_enc_c_array(call, view->buf, view->ndim, view->shape, view->itemsize);

	if (!view->suboffsets)
		return py_enc_numpy_array(call, view->buf, view->ndim, view->shape, view->strides,
					  view->itemsize);

	/* PIL-style Python array */
	return py_enc_pil_array(call, view->buf, view->ndim, view->shape, view->strides,
				view->suboffsets, view->itemsize);
}

/*
 * Encode the contents of a python buffer view.
 */
int py_enc_buffer(struct rx_call *call, Py_buffer *view, size_t dim)
{
	static unsigned zero;
	int i;

	if (call->error_code)
		return -1;

	if (0) {
		debug("PEBUF: l=%zu isz=%zd {", view->len, view->itemsize);
		if (view->shape)
			for (i = 0; i < view->ndim; i++)
				debug(" %zd", view->shape[i]);
		debug(" }\n");
	}

	if (view->len > dim) {
		PyErr_Format(PyExc_RuntimeError, "Marshalling Error: String or opaque value too long");
		return -1;
	}

	rxrpc_enc(call, view->len);
	if (py_enc_buffer_raw(call, view, dim) == -1)
		return -1;

	if (view->len & 3)
		rxrpc_enc_blob(call, &zero, 4 - (view->len & 3));
	return rxrpc_post_enc(call);
}

/*
 * Recursively decode into a standard C array.
 */
static int py_dec_c_array(struct rx_call *call, struct py_dec_manager *manager)
{
	unsigned long val;
	int i;

	/* First of all, we finish off the blob we're currently decoding
	 * into.
	 */
	if (call->blob_size < manager->view.itemsize) {
		rxrpc_dec_blob(call);
		if (rxrpc_post_dec(call) < 0)
			return -1;
		if (call->blob_size < manager->view.itemsize)
			goto need_more;
	}

	/* Now we increment the per-dimension counters, overflowing and
	 * wrapping when a counter reaches the limit.  When the outermost
	 * wraps, we are done.
	 */
	for (i = manager->view.ndim - 1; i >= 0; i--) {
		val = manager->indices[i].val;
		if (val + 1 < manager->view.shape[i]) {
			manager->indices[i].val = val + 1;
			goto incremented;
		}
		manager->indices[i].val = 0;
	}

	return 0; /* Complete */

incremented:
	/* Recalculate the cached pointers */
	for (; i <= manager->view.ndim - 1; i++) {
		void **ptrs = manager->indices[i - 1].ptr;
		void *ptr = ptrs[manager->indices[i].val];
		manager->indices[i].ptr = ptr;
	}

	call->blob_offset = 0;
	call->blob = manager->indices[manager->view.ndim - 1].ptr;
need_more:
	return 1;
}

/*
 * Recursively decode into a NumPy-style array.
 */
static int py_dec_numpy_array(struct rx_call *call, struct py_dec_manager *manager)
{
	unsigned long val;
	int i;

	/* First of all, we finish off the blob we're currently decoding
	 * into.
	 */
	if (call->blob_size < manager->view.itemsize) {
		rxrpc_dec_blob(call);
		if (rxrpc_post_dec(call) < 0)
			return -1;
		if (call->blob_size < manager->view.itemsize)
			goto need_more;
	}

	/* Now we increment the per-dimension counters, overflowing and
	 * wrapping when a counter reaches the limit.  When the outermost
	 * wraps, we are done.
	 */
	for (i = manager->view.ndim - 1; i >= 0; i--) {
		val = manager->indices[i].val;
		if (val + 1 < manager->view.shape[i]) {
			manager->indices[i].val = val + 1;
			goto incremented;
		}
		manager->indices[i].val = 0;
	}

	return 0; /* Complete */

incremented:
	/* Recalculate the cached pointers */
	for (; i <= manager->view.ndim - 1; i++) {
		void *ptr = manager->indices[i - 1].ptr;
		ptr += manager->indices[i].val * manager->view.strides[i];
		manager->indices[i].ptr = ptr;
	}

	call->blob_offset = 0;
	call->blob = manager->indices[manager->view.ndim - 1].ptr;
need_more:
	return 1;
}

/*
 * Recursively decode into a Python Imaging Library (PIL)-style array.
 */
static int py_dec_pil_array(struct rx_call *call, struct py_dec_manager *manager)
{
	unsigned long val;
	int i;

	/* First of all, we finish off the blob we're currently decoding
	 * into.
	 */
	if (call->blob_size < manager->view.itemsize) {
		rxrpc_dec_blob(call);
		if (rxrpc_post_dec(call) < 0)
			return -1;
		if (call->blob_size < manager->view.itemsize)
			goto need_more;
	}

	/* Now we increment the per-dimension counters, overflowing and
	 * wrapping when a counter reaches the limit.  When the outermost
	 * wraps, we are done.
	 */
	for (i = manager->view.ndim - 1; i >= 0; i--) {
		val = manager->indices[i].val;
		if (val + 1 < manager->view.shape[i]) {
			manager->indices[i].val = val + 1;
			goto incremented;
		}
		manager->indices[i].val = 0;
	}

	return 0; /* Complete */

incremented:
	/* Recalculate the cached pointers */
	for (; i <= manager->view.ndim - 1; i++) {
		void *ptr = manager->indices[i - 1].ptr;
		ptr += manager->indices[i].val * manager->view.strides[i];
		if (manager->view.suboffsets[i] >= 0) {
			ptr = *((void *const *)ptr);
			ptr += manager->view.suboffsets[i];
		}
		manager->indices[i].ptr = ptr;
	}

	call->blob_offset = 0;
	call->blob = manager->indices[manager->view.ndim - 1].ptr;
need_more:
	return 1;
}

/*
 * Decode the contents of an opaque type
 */
int py_dec_into_buffer(struct rx_call *call)
{
	struct py_dec_manager *manager = call->decoder_manager;
	int ret;

	if (call->error_code)
		return -1;

	if (call->blob == &rxgen_dec_padding_sink) {
		rxrpc_dec_blob(call);
		if (rxrpc_post_dec(call) == -1)
			return -1;
		return (call->blob_offset == call->blob_size) ? 0 : 1;
	}

	if (manager->view.ndim == 0 || (manager->view.ndim == 1 && !manager->view.shape)) {
		/* Single scalar */
		rxrpc_dec_blob(call);
		if (rxrpc_post_dec(call) == -1)
			return -1;
		ret = (call->blob_offset == call->blob_size) ? 0 : 1;
	} else if (!manager->view.strides)
		ret = py_dec_c_array(call, manager);
	else if (!manager->view.suboffsets)
		ret = py_dec_numpy_array(call, manager);
	else
		ret = py_dec_pil_array(call, manager);

	if (ret <= 0) {
		PyBuffer_Release(&manager->view);
		free(call->decoder_manager);
		call->decoder_manager = NULL;
	}

	if (ret == 0 && call->padding_size > 0) {
		/* Soak up the padding to a 32-bit boundary */
		call->blob = &rxgen_dec_padding_sink;
		call->blob_size = 4 - (call->blob_size & 3);
		call->blob_offset = 0;
		return 1;
	}

	return ret;
}

/*
 * Initialise buffer decode.
 *
 * Returns 0 if there's nothing to do, 1 if the decode is set up and -1 on error,
 */
int py_dec_init_buffer(struct rx_call *call, Py_buffer *view, bool padded)
{
	struct py_dec_manager *manager = NULL;
	size_t size;
	int i;

	if (call->decoder_manager) {
		manager = call->decoder_manager;
		PyBuffer_Release(&manager->view);
		free(manager);
		manager = NULL;
		call->decoder_manager = NULL;
	}

	debug("INIT_BUFFER: l=%zu isz=%zd nd=%d\n", view->len, view->itemsize, view->ndim);
	call->need_size = view->len;
	if (view->len == 0) {
		PyBuffer_Release(view);
		return 0;
	}

	call->padding_size = padded ? 4 - (view->len & 3) : 0;

	size = sizeof(struct py_dec_manager);
	size += view->ndim * sizeof(struct py_dec_index);
	manager = malloc(size);
	if (!manager) {
		PyBuffer_Release(view);
		PyErr_NoMemory();
		return -1;
	}

	memset(manager, 0, size);
	memcpy(&manager->view, view, sizeof(*view));
	manager->indices[-1].ptr = manager->view.buf;

	call->blob_size = manager->view.itemsize;

	if (manager->view.ndim == 0) {
		call->blob_size = manager->view.len;
	} else if (manager->view.ndim == 1 && !manager->view.shape) {
		manager->indices[0].ptr = manager->indices[-1].ptr;
		call->blob_size = manager->view.len;
	} else if (!manager->view.strides) {
		/* Standard C array */
		for (i = 0; i <= manager->view.ndim - 1; i++) {
			void **ptrs = manager->indices[i - 1].ptr;
			void *ptr = ptrs[manager->indices[i].val];
			manager->indices[i].ptr = ptr;
		}
	} else if (!manager->view.suboffsets) {
		/* NumPy-style Python array */
		for (i = 0; i <= manager->view.ndim - 1; i++) {
			void *ptr = manager->indices[i - 1].ptr;
			ptr += manager->indices[i].val * manager->view.strides[i];
			manager->indices[i].ptr = ptr;
		}
	} else {
		/* PIL-style Python array */
		for (i = 0; i <= manager->view.ndim - 1; i++) {
			void *ptr = manager->indices[i - 1].ptr;
			ptr += manager->indices[i].val * manager->view.strides[i];
			if (manager->view.suboffsets[i] >= 0) {
				ptr = *((void *const *)ptr);
				ptr += manager->view.suboffsets[i];
			}
			manager->indices[i].ptr = ptr;
		}
	}

	/* Set the first blob to be decoded */
	call->blob = manager->indices[manager->view.ndim - 1].ptr;
	call->blob_offset = 0;
	call->decoder_manager = manager;
	return 1;
}

/*
 * Initialise the decoding of the contents of an opaque type
 */
int py_dec_init_opaque(struct rx_call *call, PyObject *obj)
{
	Py_buffer view;
	int ret;

	if (call->error_code)
		return -1;

	if (PyObject_GetBuffer(obj, &view, PyBUF_FULL) < 0) {
		debug("*** GET BUFFER FAILED\n");
		return -1;
	}

	ret = py_dec_init_buffer(call, &view, true);
	if (ret == -1)
		return -1;

	return (ret < 0 || call->error_code) ? -1 : 0;
}

/*
 * Decode a string of bytes into a preallocated unicode string python object.
 */
int py_dec_into_string(struct rx_call *call)
{
	PyObject *str = call->blob;
	unsigned needed, segment, i;

	rxrpc_post_dec(call);

	needed = call->blob_size - call->blob_offset;
	segment = call->data_stop - call->data_cursor;
	debug("DEC STR dc=%u bsize=%u seg=%u\n", call->data_count, needed, segment);

	if (segment > 0) {
		if (segment > needed)
			segment = needed;
		if (call->blob != &rxgen_dec_padding_sink) {
			for (i = 0; i < segment; i++)
				PyUnicode_WRITE(PyUnicode_KIND(str), PyUnicode_DATA(str),
						call->blob_offset + i, call->data_cursor[i]);
		}
		call->blob_decoded += segment;
		call->blob_offset += segment;
		call->data_cursor += segment;
		if (call->blob_size <= call->blob_offset) {
			if (call->blob != &rxgen_dec_padding_sink && call->padding_size > 0) {
				/* Soak up the padding to a 32-bit boundary */
				call->blob = &rxgen_dec_padding_sink;
				call->blob_size = call->padding_size;
				call->blob_offset = 0;
				return 1;
			}
			return 0;
		}
	}

	rxrpc_dec_advance_buffer(call);
	return 1;
}

/*
 * Decode a string of bytes into a preallocated unicode string python object.
 */
int py_dec_init_string(struct rx_call *call, PyObject **_str)
{
	PyObject *str;

	debug("INIT STRING %u\n", call->blob_size);

	str = PyUnicode_New(call->blob_size, 255);
	if (!str)
		return -1;
	*_str = str;
	if (call->blob_size == 0)
 		return 0;

	if (PyUnicode_READY(str) < 0) {
		debug("*** STRING NON-CANONICAL\n");
		abort();
	}

	call->blob = str;
	call->blob_offset = 0;
	call->padding_size = 4 - (call->blob_size & 3);
	return 1;
}

/*
 * Comparator for binary searching the abort code table
 */
static int py_rxgen_received_abort_cmp(const void *key, const void *_entry)
{
	const struct kafs_abort_list *entry = _entry;
	int ret;

	if ((uint32_t)(unsigned long)key > entry->id)
		ret = 1;
	else if ((uint32_t)(unsigned long)key < entry->id)
		ret = -1;
	else
		ret = 0;
	return ret;
}

/*
 * Turn a received abort into a Python exception
 */
PyObject *py_rxgen_received_abort(struct rx_call *call)
{
	const struct kafs_abort_list *entry;
	const char *msg;
	PyObject *ex;

	entry = bsearch((void *)(unsigned long)call->abort_code,
			kafs_abort_map,
			sizeof(kafs_abort_map) / sizeof(kafs_abort_map[0]),
			sizeof(kafs_abort_map[0]),
			py_rxgen_received_abort_cmp);

	if (entry) {
		ex = entry->obj;
		msg = entry->msg;
	} else {
		ex = kafs_remote_abort;
		msg = NULL;
	}

	if (msg)
		return PyErr_Format(ex, "Aborted %u: %s", call->abort_code, msg);
	else
		return PyErr_Format(ex, "Aborted %u", call->abort_code);
}

/*
 * Clean up a call after decoding
 */
void py_rxgen_decoder_cleanup(struct rx_call *call)
{
	if (call->decoder_manager) {
		struct py_dec_manager *manager = call->decoder_manager;
		PyBuffer_Release(&manager->view);
		free(manager);
	}
	Py_XDECREF(call->decoder_split_callback);
	Py_XDECREF(call->decoder_split_info);
}
