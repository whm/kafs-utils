/* RxRPC autogen defs
 *
 * Copyright (C) 2014 Red Hat, Inc. All Rights Reserved.
 * Written by David Howells (dhowells@redhat.com)
 *
 * This program is free software; you can redistribute it and/or
 * modify it under the terms of the GNU General Public Licence
 * as published by the Free Software Foundation; either version
 * 2 of the Licence, or (at your option) any later version.
 */

#ifndef _RXGEN_H
#define _RXGEN_H

#include "af_rxrpc.h"
#include <stdbool.h>
#include <errno.h>
#include <stdlib.h>

typedef uint32_t net_xdr_t;

struct rx_connection {
	struct sockaddr_rxrpc peer;
	uint32_t	last_abort_code;
	int fd;
};

#define RXGEN_BUFFER_SIZE	1024

struct rx_buf {
	uint32_t	magic;
	unsigned short	io_cursor;
	//unsigned short	enc_cursor;
	uint8_t		*buf;
	struct rx_buf	*next;
};

enum rx_call_state {
	rx_call_cl_not_started,
	rx_call_cl_encoding_params,
	rx_call_cl_waiting_for_response,
	rx_call_cl_decoding_response,
	rx_call_cl_wait_for_no_MSG_MORE,
	rx_call_cl_complete,
	rx_call_sv_not_started,
	rx_call_sv_waiting_for_opcode,
	rx_call_sv_decoding_opcode,
	rx_call_sv_decoding_params,
	rx_call_sv_wait_for_no_MSG_MORE,
	rx_call_sv_processing,
	rx_call_sv_encoding_response,
	rx_call_sv_response_encoded,
	rx_call_sv_waiting_for_final_ack,
	rx_call_sv_complete,
	rx_call_remotely_aborted,
	rx_call_locally_aborted,
	rx_call_net_error,
	rx_call_local_error,
	rx_call_rejected_busy,
};

struct rx_call {
	uint32_t	magic;
	struct rx_connection *conn;
	enum rx_call_state state;
	unsigned	known_to_kernel : 1;
	unsigned	secured : 1;
	unsigned	more_send : 1;
	unsigned	more_recv : 1;
	int		error_code;
	uint32_t	abort_code;
	unsigned	need_size;

	unsigned long long bytes_sent, bytes_received, blob_decoded;

	/* Service routines */
	void (*processor)(struct rx_call *call);
	void (*failed)(struct rx_call *call);

	/* String of buffers holding data */
	uint8_t		*data_start;
	uint8_t		*data_cursor;
	uint8_t		*data_stop;
	struct rx_buf	*buffer_head;	
	struct rx_buf	*buffer_tail;
	unsigned	data_count;
	unsigned	buffer_space;
	unsigned	padding_size;

	/* Decoding support */
	unsigned	phase;		/* Encode/decode phase */
	unsigned	blob_size;	/* Size of blob being encoded/decoded */
	unsigned	blob_offset;	/* Offset into blob */
	unsigned	bulk_count;	/* Number of items in bulk array */
	unsigned	bulk_index;	/* Index of item being processed */
	void		*blob;		/* Blob being encoded/decoded */
	union {
		void		*bulk_item;	/* Pointer to string/bytes/struct being processed */
		uint32_t	bulk_u32;	/* 8/16/32-bit integer being processed */
		uint64_t	bulk_u64;	/* 64-bit unsigned integer being processed */
		int64_t		bulk_s64;	/* 64-bit signed integer being processed */
	};
	int (*decoder)(struct rx_call *call);
	void		*decoder_private;
	void		*decoder_manager;
	void		*decoder_split_callback;
	void		*decoder_split_info;
	void (*decoder_cleanup)(struct rx_call *call);
};

extern uint32_t rxgen_dec_padding_sink;

extern int rxrpc_enc_blob(struct rx_call *call, const void *data, size_t size);
extern void rxrpc_enc_slow(struct rx_call *call, net_xdr_t data);
static inline void rxrpc_enc(struct rx_call *call, uint32_t data)
{
	uint32_t xdr_data = htonl(data);
	if (__builtin_expect(((unsigned long)call->data_cursor & 3) == 0 &&
			     call->data_cursor < call->data_stop, 1)) {
		*(net_xdr_t *)call->data_cursor = xdr_data;
		call->data_cursor += 4;
	} else {
		rxrpc_enc_slow(call, xdr_data);
	}
}

static inline void rxrpc_enc_align(struct rx_call *call)
{
	abort(); // Can't assume data_cursor is 4-byte aligned
	while ((unsigned long)call->data_cursor & 3)
		*(call->data_cursor++) = 0;
}

static inline int rxrpc_post_enc(struct rx_call *call)
{
	if (__builtin_expect(!call->error_code, 1)) {
		size_t n = call->data_cursor - call->data_start;
		call->data_start = call->data_cursor;
		call->buffer_space -= n;
		call->data_count += n;
		return 0;
	} else {
		errno = call->error_code;
		return -1;
	}
}

extern void rxrpc_dec_blob(struct rx_call *call);
extern uint32_t rxrpc_dec_slow(struct rx_call *call);
static inline uint32_t rxrpc_dec(struct rx_call *call)
{
	if (__builtin_expect(((unsigned long)call->data_cursor & 3) == 0 &&
			     call->data_cursor < call->data_stop, 1)) {
		net_xdr_t x = *(net_xdr_t *)call->data_cursor;
		call->data_cursor += sizeof(x);
		return ntohl(x);
	} else {
		return rxrpc_dec_slow(call);
	}
}

static inline void rxrpc_dec_align(struct rx_call *call)
{
	unsigned long cursor = (unsigned long)call->data_cursor;
	abort(); // Can't assume data_cursor is 4-byte aligned
	cursor = (cursor + 3) & ~3UL;
	call->data_cursor = (uint8_t*)cursor;
}

static inline int rxrpc_post_dec(struct rx_call *call)
{
	if (__builtin_expect(!call->error_code, 1)) {
		size_t n = call->data_cursor - call->data_start;
		call->data_start = call->data_cursor;
		call->data_count -= n;
		call->need_size -= n;
		return 0;
	} else {
		errno = call->error_code;
		return -1;
	}
}

extern void rxrpc_dec_advance_buffer(struct rx_call *call);
extern int rxgen_dec_discard_excess(struct rx_call *call);

extern struct rx_connection *rx_new_connection(const struct sockaddr *sa,
					       socklen_t salen,
					       uint16_t service,
					       uint16_t local_port,
					       uint16_t local_service,
					       int exclusive,
					       const char *key,
					       int security);

extern void rx_close_connection(struct rx_connection *z_conn);

extern struct rx_call *rxrpc_alloc_call(struct rx_connection *z_conn, int incoming_call);
extern void rxrpc_abort_call(struct rx_call *call, uint32_t abort_code);
extern void rxrpc_terminate_call(struct rx_call *call, uint32_t abort_code);

extern int rxrpc_send_data(struct rx_call *call);
extern int rxrpc_recv_data(struct rx_connection *z_conn, bool nowait);
extern int rxrpc_run_sync_call(struct rx_call *call);

#endif /* _RXGEN_H */
