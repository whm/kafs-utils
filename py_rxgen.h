/* rxgen Python wrapping support declarations
 *
 * Copyright (C) 2014 Red Hat, Inc. All Rights Reserved.
 * Written by David Howells (dhowells@redhat.com)
 *
 * This program is free software; you can redistribute it and/or
 * modify it under the terms of the GNU General Public Licence
 * as published by the Free Software Foundation; either version
 * 2 of the Licence, or (at your option) any later version.
 */

#ifndef _PY_RXGEN_H
#define _PY_RXGEN_H

#include "rxgen.h"

struct py_rx_connection {
	PyObject_HEAD
	struct rx_connection *x;
};

struct py_rx_call {
	PyObject_HEAD
	struct rx_call *x;
	struct py_rx_request *req;
	struct py_rx_response *resp;
};

struct py_rx_request {
	PyObject_HEAD
};

struct py_rx_response {
	PyObject_HEAD
};

enum py_rx_split_state {
	split_idle,
	split_transmitting,
	split_receiving,
	split_dead
};

struct py_rx_split_info {
	PyObject_HEAD
	struct rx_call *call;
	PyObject *target;
	enum py_rx_split_state split_state;
	unsigned state;
	bool receiving_data;
};

extern PyTypeObject py_rx_connectionType;

extern PyObject *kafs_py_rx_new_connection(PyObject *, PyObject *);
extern PyObject *kafs_py_string_to_key(PyObject *, PyObject *);

extern int py_rxgen_initialise_members(PyObject *obj, PyObject *kw);
extern void py_rxgen_decoder_cleanup(struct rx_call *call);

/*
 * Single embedded struct handling
 */
extern PyObject *py_rxgen_get_struct(const void *p, PyObject **cache,
				     PyObject *(*data_to_type)(const void *elem));
extern int py_rxgen_set_struct(PyObject **cache, PyTypeObject *type, PyObject *val);
extern int py_rxgen_premarshal_struct(void *p, size_t size, size_t offs,
				      PyObject *cache,
				      int (*premarshal)(PyObject *object));

/*
 * String and opaque type handling
 */
extern PyObject *py_rxgen_get_string(const void *_p, size_t n);
extern int py_rxgen_set_string(void *_p, size_t n, PyObject *val);
extern int py_enc_buffer_raw(struct rx_call *call, Py_buffer *view, size_t dim);
extern int py_enc_buffer(struct rx_call *call, Py_buffer *view, size_t dim);
extern int py_dec_into_buffer(struct rx_call *call);
extern int py_dec_init_buffer(struct rx_call *call, Py_buffer *view, bool padded);
extern int py_dec_init_opaque(struct rx_call *call, PyObject *obj);
extern int py_dec_into_string(struct rx_call *call);
extern int py_dec_init_string(struct rx_call *call, PyObject **_str);

/*
 * Embedded general array handling
 */
extern int py_rxgen_set_array(size_t n, PyObject **cache, PyObject *val);

/*
 * Embedded integer array handling
 */
extern PyObject *py_rxgen_get_int8(const void *_array , size_t n, PyObject **cache);
extern PyObject *py_rxgen_get_int16(const void *_array, size_t n, PyObject **cache);
extern PyObject *py_rxgen_get_int32(const void *_array, size_t n, PyObject **cache);
extern PyObject *py_rxgen_get_uint8(const void *_array , size_t n, PyObject **cache);
extern PyObject *py_rxgen_get_uint16(const void *_array, size_t n, PyObject **cache);
extern PyObject *py_rxgen_get_uint32(const void *_array, size_t n, PyObject **cache);

extern int py_rxgen_premarshal_uint8(void *_array, size_t n, PyObject *cache);
extern int py_rxgen_premarshal_uint16(void *_array, size_t n, PyObject *cache);
extern int py_rxgen_premarshal_uint32(void *_array, size_t n, PyObject *cache);
extern int py_rxgen_premarshal_int8(void *_array, size_t n, PyObject *cache);
extern int py_rxgen_premarshal_int16(void *_array, size_t n, PyObject *cache);
extern int py_rxgen_premarshal_int32(void *_array, size_t n, PyObject *cache);

/*
 * Embedded struct array handling
 */
extern PyObject *py_rxgen_get_structs(const void *data, size_t num, size_t size,
				      PyObject **cache,
				      PyObject *(*data_to_type)(const void *elem));
extern int py_rxgen_premarshal_structs(void *array, size_t n, size_t size, size_t offs,
				       PyObject *cache,
				       int (*premarshal)(PyObject *object));

/*
 * Abort mapping
 */
struct kafs_abort_list {
	uint32_t	id;
	const char	*msg;
	PyObject	*obj;
};

extern PyObject *py_rxgen_received_abort(struct rx_call *call);

/*
 * Split-mode RPC call handling
 */
extern PyTypeObject py_rx_split_infoType;
extern PyObject *py_rxgen_split_client_prepare(void);
extern int py_rxgen_split_transmit(struct rx_call *call);
extern int py_rxgen_split_receive(struct rx_call *call, bool init);

static inline void py_rxgen_split_client_set(struct rx_call *call,
					     PyObject *split_callback,
					     PyObject *_split_info)
{
	struct py_rx_split_info *split_info = (struct py_rx_split_info *)_split_info;

	split_info->call = call;
	Py_INCREF(split_callback);
	call->decoder_split_callback = split_callback;
	call->decoder_split_info = _split_info;
}

#endif /* _PY_RXGEN_H */
