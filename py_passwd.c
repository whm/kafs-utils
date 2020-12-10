/* Password-to-key service
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
#include <krb5/krb5.h>
#include "py_rxgen.h"

/*
 * Convert a string to an AFS DES key.
 */
PyObject *kafs_py_string_to_key(PyObject *_self, PyObject *args)
{
	krb5_error_code kresult;
	krb5_context k5_ctx;
	krb5_enctype enctype = ENCTYPE_DES_CBC_CRC;
	krb5_data password;
	krb5_data cellname;
	krb5_data params;
	krb5_keyblock key;
	Py_buffer view;
	PyObject *result;
	char parambuf[1];

	if (!PyArg_ParseTuple(args, "s#s#",
			      &password.data, &password.length,
			      &cellname.data, &cellname.length))
		return NULL;

	kresult = krb5_init_context(&k5_ctx);
	if (kresult)
		return PyErr_Format(PyExc_RuntimeError,
				    "Krb5: Failed to init context: %s",
				    krb5_get_error_message(k5_ctx, kresult));

	password.magic = 0;
	cellname.magic = 0;

	/* Tell Kerberos to use the AFS-form DES */
	parambuf[0] = 1;
	params.data = parambuf;
	params.length = 1;
	params.magic = 0;

	kresult = krb5_c_string_to_key_with_params(k5_ctx,
						   enctype,
						   &password,
						   &cellname,
						   &params,
						   &key);
	if (kresult) {
		PyErr_Format(PyExc_RuntimeError,
			     "Krb5: Failed to convert string to key: %s",
			     krb5_get_error_message(k5_ctx, kresult));
		krb5_free_context(k5_ctx);
		return NULL;
	}

	result = PyByteArray_FromStringAndSize("", 0);
	if (!result)
		goto out;
	if (PyByteArray_Resize(result, key.length) == -1)
		goto out_free_result;
	if (PyObject_GetBuffer(result, &view, PyBUF_SIMPLE | PyBUF_WRITABLE) < 0)
		goto out_free_result;
	memcpy(view.buf, key.contents, key.length);
	PyBuffer_Release(&view);

out:
	krb5_free_keyblock_contents(k5_ctx, &key);
	krb5_free_context(k5_ctx);
	return result;

out_free_result:
	Py_DECREF(result);
	result = NULL;
	goto out;
}
