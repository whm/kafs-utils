/* AF_RXRPC driver
 *
 * Copyright (C) 2014 Red Hat, Inc. All Rights Reserved.
 * Written by David Howells (dhowells@redhat.com)
 *
 * This program is free software; you can redistribute it and/or
 * modify it under the terms of the GNU General Public Licence
 * as published by the Free Software Foundation; either version
 * 2 of the Licence, or (at your option) any later version.
 */

#define _XOPEN_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <poll.h>
#include <errno.h>
#include <limits.h>
#include <sys/socket.h>
#include "af_rxrpc.h"
#include "rxgen.h"

#define RXGEN_CALL_MAGIC	0x52584745U
#define RXGEN_BUF_MAGIC		(0x52420000U | __LINE__)
#define RXGEN_BUF_DEAD		(0x6b6bU | __LINE__)

#define debug(fmt, ...) do { if (0) printf(fmt, ## __VA_ARGS__); } while (0)

uint32_t rxgen_dec_padding_sink;

/*
 * dump the control messages
 */
static __attribute__((unused))
void dump_cmsg(struct msghdr *msg)
{
	struct cmsghdr *cmsg;
	unsigned long user_id;
	unsigned char *p;
	int abort_code;
	int n;

	for (cmsg = CMSG_FIRSTHDR(msg); cmsg; cmsg = CMSG_NXTHDR(msg, cmsg)) {
		n = cmsg->cmsg_len - CMSG_ALIGN(sizeof(*cmsg));
		p = CMSG_DATA(cmsg);

		printf("CMSG: %zu: ", cmsg->cmsg_len);

		if (cmsg->cmsg_level == SOL_RXRPC) {
			switch (cmsg->cmsg_type) {
			case RXRPC_USER_CALL_ID:
				printf("RXRPC_USER_CALL_ID: ");
				if (n != sizeof(user_id))
					goto dump_data;
				memcpy(&user_id, p, sizeof(user_id));
				printf("%lx\n", user_id);
				continue;

			case RXRPC_ABORT:
				printf("RXRPC_ABORT: ");
				if (n != sizeof(abort_code))
					goto dump_data;
				memcpy(&abort_code, p, sizeof(abort_code));
				printf("%d\n", abort_code);
				continue;

			case RXRPC_ACK:
				printf("RXRPC_ACK");
				if (n != 0)
					goto dump_data_colon;
				goto print_nl;

			case RXRPC_RESPONSE:
				printf("RXRPC_RESPONSE");
				if (n != 0)
					goto dump_data_colon;
				goto print_nl;

			case RXRPC_NET_ERROR:
				printf("RXRPC_NET_ERROR: ");
				if (n != sizeof(abort_code))
					goto dump_data;
				memcpy(&abort_code, p, sizeof(abort_code));
				printf("%s\n", strerror(abort_code));
				continue;

			case RXRPC_BUSY:
				printf("RXRPC_BUSY");
				if (n != 0)
					goto dump_data_colon;
				goto print_nl;

			case RXRPC_LOCAL_ERROR:
				printf("RXRPC_LOCAL_ERROR: ");
				if (n != sizeof(abort_code))
					goto dump_data;
				memcpy(&abort_code, p, sizeof(abort_code));
				printf("%s\n", strerror(abort_code));
				continue;

			default:
				break;
			}
		}

		printf("l=%d t=%d", cmsg->cmsg_level, cmsg->cmsg_type);

	dump_data_colon:
		printf(": ");
	dump_data:
		printf("{");
		for (; n > 0; n--, p++)
			printf("%02x", *p);

	print_nl:
		printf("}\n");
	}
}

/*
 * Set up a new connection
 */
struct rx_connection *rx_new_connection(const struct sockaddr *sa,
					socklen_t salen,
					uint16_t service,
					uint16_t local_port,
					uint16_t local_service,
					int exclusive,
					const char *key,
					int security)
{
	struct sockaddr_rxrpc srx;
	struct rx_connection *z_conn;
	int ret;

	z_conn = calloc(1, sizeof(*z_conn));
	if (!z_conn)
		return NULL;

	z_conn->peer.srx_family = AF_RXRPC;
	z_conn->peer.srx_service = service;
	z_conn->peer.transport_type = SOCK_DGRAM;
	z_conn->peer.transport_len = sizeof(srx.transport.sin);

	switch (sa->sa_family) {
	case 0:
		errno = EDESTADDRREQ;
		goto error_conn;
	case AF_INET:
		if (salen != sizeof(struct sockaddr_in))
			goto inval;
		break;
	case AF_INET6:
		if (salen != sizeof(struct sockaddr_in6))
			goto inval;
		break;
	default:
		errno = EPROTOTYPE;
		goto error_conn;
	}

	if (security < RXRPC_SECURITY_PLAIN ||
	    security > RXRPC_SECURITY_ENCRYPT)
		goto inval;

	memcpy(&z_conn->peer.transport, sa, salen);
	switch (sa->sa_family) {
	case AF_INET:
		if (!z_conn->peer.transport.sin.sin_port) {
			errno = EDESTADDRREQ;
			goto error_conn;
		}
		break;
	case AF_INET6:
		if (!z_conn->peer.transport.sin6.sin6_port) {
			errno = EDESTADDRREQ;
			goto error_conn;
		}
		break;
	}

	/* Open up a socket for talking to the AF_RXRPC module */
	z_conn->fd = socket(AF_RXRPC, SOCK_DGRAM, PF_INET);
	if (z_conn->fd < 0)
			goto error_conn;

	if (exclusive) {
		ret = setsockopt(z_conn->fd,
				 SOL_RXRPC, RXRPC_EXCLUSIVE_CONNECTION,
				 NULL, 0);
		if (ret == -1)
			goto error_conn;
	}

	if (key) {
		ret = setsockopt(z_conn->fd, SOL_RXRPC, RXRPC_MIN_SECURITY_LEVEL,
				 &security, sizeof(security));
		if (ret == -1)
			goto error_conn;

		ret = setsockopt(z_conn->fd, SOL_RXRPC, RXRPC_SECURITY_KEY,
				 key, strlen(key));
		if (ret == -1)
			goto error_conn;
	}

	/* Bind an address to the local endpoint */
	memset(&srx, 0, sizeof(srx));
	srx.srx_family = AF_RXRPC;
	srx.srx_service = local_service;
	srx.transport_type = SOCK_DGRAM;
	srx.transport_len = salen;
	srx.transport.sin.sin_family = sa->sa_family;
	switch (sa->sa_family) {
	case AF_INET:
		srx.transport.sin.sin_port = htons(local_port);
		break;
	case AF_INET6:
		srx.transport.sin6.sin6_port = htons(local_port);
		break;
	}

	ret = bind(z_conn->fd, (struct sockaddr *)&srx, sizeof(srx));
	if (ret < 0)
		goto error_fd;

	return z_conn;

inval:
	errno = EINVAL;
	goto error_conn;
error_fd:
	close(z_conn->fd);
error_conn:
	free(z_conn);
	return NULL;
}

/*
 * Close an RxRPC client connection.  This will cause all outstanding
 * operations to be aborted by the kernel..
 */
void rx_close_connection(struct rx_connection *z_conn)
{
	close(z_conn->fd);
	free(z_conn);
}

/*
 * Allocate a call structure.  It is given one buffer ready to go.
 */
struct rx_call *rxrpc_alloc_call(struct rx_connection *z_conn,
				 int incoming_call)
{
	struct rx_call *call;
	struct rx_buf *buf;
	uint8_t *data;

	call = calloc(1, sizeof(struct rx_call));
	if (!call)
		return NULL;

	buf = calloc(1, sizeof(struct rx_buf));
	if (!buf) {
		free(call);
		return NULL;
	}

	data = malloc(RXGEN_BUFFER_SIZE);
	if (!data) {
		free(buf);
		free(call);
		return NULL;
	}

	debug("Alloc: buf=%p data=%p\n", buf, data);

	buf->magic = RXGEN_BUF_MAGIC;
	buf->buf = data;

	if (incoming_call)
		call->state = rx_call_sv_not_started;
	else
		call->state = rx_call_cl_not_started;

	call->magic = RXGEN_CALL_MAGIC;
	call->conn = z_conn;
	call->more_send = true;
	call->more_recv = true;
	call->buffer_head = buf;
	call->buffer_tail = buf;
	call->data_start = data;
	call->data_cursor = data;
	call->data_stop = incoming_call ? data : data + RXGEN_BUFFER_SIZE;
	call->buffer_space = RXGEN_BUFFER_SIZE;
	return call;
}

static void rxrpc_check_buf(const struct rx_buf *buf)
{
	if (0) {
		if ((buf->magic ^ RXGEN_BUF_MAGIC) & 0xffff0000U)
			abort();
		if (buf->io_cursor > RXGEN_BUFFER_SIZE)
			abort();
	}
}

static void rxrpc_check_call(const struct rx_call *call)
{
	if (0) {
		const struct rx_buf *cursor;

		if (call->magic != RXGEN_CALL_MAGIC)
			abort();

		for (cursor = call->buffer_head; cursor != call->buffer_tail; cursor = cursor->next)
			rxrpc_check_buf(cursor);
		rxrpc_check_buf(cursor);
		if (cursor->next)
			abort();
	}
}

/*
 * Send buffered data.
 */
int rxrpc_send_data(struct rx_call *call)
{
	struct rx_buf *cursor;
	struct msghdr msg;
	size_t ctrllen;
	unsigned char control[128];
	struct iovec iov[16];
	unsigned more;
	int ioc, ret, i;

	debug("-->rxrpc_send_data(%u,0x%x)\n", call->state, call->data_count);

	rxrpc_check_call(call);

	/* Switch into encode state */
	switch (call->state) {
	case rx_call_cl_not_started:
	case rx_call_sv_processing:
		call->state++;
	case rx_call_cl_encoding_params:
	case rx_call_sv_encoding_response:
		break;
	default:
		fprintf(stderr, "RxRPC: Send in bad call state (%d)\n", call->state);
		abort();
	}

more_to_send:
	/* Request an operation */
	ctrllen = 0;
	RXRPC_ADD_CALLID(control, ctrllen, (unsigned long)call);

	msg.msg_name		= &call->conn->peer;
	msg.msg_namelen		= sizeof(call->conn->peer);
	msg.msg_iov		= iov;
	msg.msg_control		= control;
	msg.msg_controllen	= ctrllen;
	msg.msg_flags		= 0;

	/* We may have a completely sent buffer on the front of the queue if
	 * this was the last buffer on the last send.  The buffer queue isn't
	 * allowed to be empty at any point.
	 */
	cursor = call->buffer_head;
	if (cursor->io_cursor == RXGEN_BUFFER_SIZE) {
		struct rx_buf *sent = cursor;
		if (sent == call->buffer_tail)
			abort();
		call->buffer_head = cursor = sent->next;
		sent->magic = RXGEN_BUF_DEAD;
		free(sent->buf);
		free(sent);
	}

	more = MSG_MORE;
	for (ioc = 0; ioc < 16; ioc++) {
		rxrpc_check_buf(cursor);

		unsigned io_cursor = cursor->io_cursor;
		unsigned end = RXGEN_BUFFER_SIZE;

		if (io_cursor == RXGEN_BUFFER_SIZE)
			abort();
		if (cursor == call->buffer_tail)
			end = call->data_cursor - cursor->buf;

		debug("BUF[%02u] %04x %04x\n", ioc, io_cursor, end);

		iov[ioc].iov_base = cursor->buf + io_cursor;
		iov[ioc].iov_len = end - io_cursor;
		if (cursor == call->buffer_tail) {
			if (!call->more_send)
				more = 0;
			ioc++;
			break;
		}
		cursor = cursor->next;
	}
	msg.msg_iovlen = ioc;

	/* Send the data */
	//dump_cmsg(&msg);

	for (i = 0; i < msg.msg_iovlen; i++)
		debug("IOV[%02u] %04zu %p\n",
		      i, msg.msg_iov[i].iov_len, msg.msg_iov[i].iov_base);

	ret = sendmsg(call->conn->fd, &msg, more);
	debug("SENDMSG: %d%s\n", ret, more ? " [more]" : "");
	if (ret == -1)
		return -1;

	call->bytes_sent += ret;
	call->data_count -= ret;
	call->known_to_kernel = 1;

	/* Free up any completely sent buffers, without completely emptying the
	 * queue.
	 */
	cursor = call->buffer_head;
	do {
		struct rx_buf *sent = cursor;
		unsigned count = RXGEN_BUFFER_SIZE - cursor->io_cursor;

		if (count > ret)
			count = ret;
		cursor->io_cursor += count;
		ret -= count;
		if (cursor == call->buffer_tail)
			break;
		sent = cursor;
		cursor = cursor->next;
		call->buffer_head = cursor;
		rxrpc_check_buf(sent);
		sent->magic = RXGEN_BUF_DEAD;
		free(sent->buf);
		free(sent);
	} while (ret > 0);

	rxrpc_check_call(call);

	if (call->data_count > 0)
		goto more_to_send;
	if (call->data_count == 0 && !call->more_send)
		call->state++;

	if (!call->more_send) {
		if (call->state == rx_call_cl_encoding_params ||
		    call->state == rx_call_sv_encoding_response)
			call->state++;
	}

	if (call->state == rx_call_cl_waiting_for_response) {
		/* Prepare to decode the response */
		debug("Prep to decode\n");
		call->data_stop = call->data_cursor = call->data_start = call->buffer_head->buf;
		call->buffer_head->io_cursor = 0;
		call->data_count = 0;
	}

	return 0;
}

/*
 * Receive data from a socket.
 */
int rxrpc_recv_data(struct rx_connection *z_conn, bool nowait)
{
	struct rx_call *call;
	struct rx_buf *bufs[4] = { NULL }, *cursor;
	struct sockaddr_rxrpc srx;
	struct cmsghdr *cmsg;
	struct msghdr msg;
	struct iovec iov[4];
	unsigned char control[128];
	uint32_t tmpbuf[1];
	int ioc, ret;

	/* Peek at the next message */
	iov[0].iov_base = &tmpbuf;
	iov[0].iov_len = sizeof(tmpbuf);

	memset(&msg, 0, sizeof(msg));
	msg.msg_iov	= iov;
	msg.msg_iovlen	= 1;
	msg.msg_name	= &srx;
	msg.msg_namelen	= sizeof(srx);
	msg.msg_control	= control;
	msg.msg_controllen = sizeof(control);
	msg.msg_flags	= 0;

	ret = recvmsg(z_conn->fd, &msg, MSG_PEEK | (nowait ? MSG_DONTWAIT : 0));
	debug("RECVMSG PEEK: %d\n", ret);
	if (ret == -1)
		return -1;

	/* Find the call ID. */
	call = NULL;
	for (cmsg = CMSG_FIRSTHDR(&msg); cmsg; cmsg = CMSG_NXTHDR(&msg, cmsg)) {
		unsigned char *p;

		if (cmsg->cmsg_level != SOL_RXRPC ||
		    cmsg->cmsg_type != RXRPC_USER_CALL_ID)
			continue;

		p = CMSG_DATA(cmsg);
		call = *(struct rx_call **)p;
		break;
	}
	if (!call)
		abort();

	/* Now actually retrieve that message */
	memset(&msg, 0, sizeof(msg));
	msg.msg_iov	= iov;
	msg.msg_iovlen	= 0;
	msg.msg_name	= &srx;
	msg.msg_namelen	= sizeof(srx);
	msg.msg_control	= control;
	msg.msg_controllen = sizeof(control);
	msg.msg_flags	= 0;

	debug("Recv: buf[0]=%p data[0]=%p (io=%u)\n",
	      call->buffer_tail, call->buffer_tail->buf, call->buffer_tail->io_cursor);

	rxrpc_check_call(call);

	/* Set up some buffers */
	if (call->buffer_tail->io_cursor < RXGEN_BUFFER_SIZE) {
		bufs[0] = call->buffer_tail;
		iov[0].iov_base = bufs[0]->buf + bufs[0]->io_cursor;
		iov[0].iov_len = RXGEN_BUFFER_SIZE - bufs[0]->io_cursor;
		msg.msg_iovlen = 1;
	} else {
		msg.msg_iovlen = 0;
	}

	for (ioc = msg.msg_iovlen; ioc < 4; ioc++) {
		bufs[ioc] = calloc(1, sizeof(struct rx_buf));
		bufs[ioc]->magic = RXGEN_BUF_MAGIC;
		if (!bufs[ioc]) {
			while (--ioc >= msg.msg_iovlen) {
				bufs[ioc]->magic = RXGEN_BUF_DEAD;
				free(bufs[ioc]->buf);
				free(bufs[ioc]);
			}
			return -1;
		}
		bufs[ioc]->buf = malloc(RXGEN_BUFFER_SIZE);
		if (!bufs[ioc]->buf) {
			bufs[ioc]->magic = RXGEN_BUF_DEAD;
			free(bufs[ioc]);
			while (--ioc >= msg.msg_iovlen) {
				bufs[ioc]->magic = RXGEN_BUF_DEAD;
				free(bufs[ioc]->buf);
				free(bufs[ioc]);
			}
			return -1;
		}
		iov[ioc].iov_base = bufs[ioc]->buf;
		iov[ioc].iov_len = RXGEN_BUFFER_SIZE;
	}
	msg.msg_iovlen = 4;

	ret = recvmsg(z_conn->fd, &msg, 0);
	debug("RECVMSG: %d\n", ret);
	if (ret == -1)
		return -1;

	debug("RECV: %d [fl:%x]\n", ret, msg.msg_flags);
	debug("CMSG: %zu\n", msg.msg_controllen);
	debug("IOV: %zu [0]=%zu\n", msg.msg_iovlen, iov[0].iov_len);

	call->bytes_received += ret;

	/* Attach any used buffers to the call and discard the rest */
	if (ret > 0) {
		for (ioc = 0; ioc < 4 && ret > 0; ioc++) {
			unsigned added = RXGEN_BUFFER_SIZE - bufs[ioc]->io_cursor;
			debug("xfer[%d] space=%u rem=%d\n", ioc, added, ret);
			if (added > ret)
				added = ret;
			bufs[ioc]->io_cursor += added;
			call->data_count += added;
			ret -= added;
			if (call->buffer_tail == bufs[ioc])
				continue;
			call->buffer_tail->next = bufs[ioc];
			call->buffer_tail = bufs[ioc];
			if (ret <= 0) {
				ioc++;
				break;
			}
		}

		for (; ioc < 4; ioc++) {
			bufs[ioc]->magic = RXGEN_BUF_DEAD;
			free(bufs[ioc]->buf);
			free(bufs[ioc]);
		}
	}

	rxrpc_check_call(call);

	for (cursor = call->buffer_head; cursor; cursor = cursor->next)
		debug("RecvQ buf=%p data=%p iocur=%u\n",
		      cursor, cursor->buf, cursor->io_cursor);

	/* Process the metadata */
	if (msg.msg_flags & MSG_EOR)
		call->known_to_kernel = 0;
	if (!(msg.msg_flags & MSG_MORE))
		call->more_recv = false;

	for (cmsg = CMSG_FIRSTHDR(&msg); cmsg; cmsg = CMSG_NXTHDR(&msg, cmsg)) {
		unsigned char *p;
		int n;

		if (cmsg->cmsg_level != SOL_RXRPC)
			continue;

		n = cmsg->cmsg_len - CMSG_ALIGN(sizeof(*cmsg));
		p = CMSG_DATA(cmsg);

		switch (cmsg->cmsg_type) {
		case RXRPC_ABORT:
			if (n != sizeof(call->abort_code))
				call->abort_code = 0;
			else
				memcpy(&call->abort_code, p, sizeof(call->abort_code));
			z_conn->last_abort_code = call->abort_code;
			call->error_code = ECONNABORTED;
			call->state = rx_call_remotely_aborted;
			break;

		case RXRPC_NET_ERROR:
			if (n != sizeof(ret)) {
				errno = EBADMSG;
				return -1;
			}
			memcpy(&ret, p, sizeof(ret));
			call->error_code = ret;
			call->state = rx_call_net_error;
			break;

		case RXRPC_LOCAL_ERROR:
			if (n != sizeof(ret)) {
				errno = EBADMSG;
				return -1;
			}
			memcpy(&ret, p, sizeof(ret));
			call->error_code = ret;
			call->state = rx_call_local_error;
			break;

		case RXRPC_BUSY:
			call->error_code = ECONNREFUSED;
			call->state = rx_call_rejected_busy;
			break;

		case RXRPC_ACK:
			if (call->state == rx_call_sv_waiting_for_final_ack) {
				call->state = rx_call_sv_complete;
			} else {
				fprintf(stderr, "RxRPC: Recv-Ack in bad call state (%d)\n",
					call->state);
				abort();
			}
			break;

		case RXRPC_RESPONSE:
			call->secured = 1;
			break;

		default:
			break;
		}
	}

	/* Switch into appropriate decode state */
loop:
	switch (call->state) {
	case rx_call_cl_waiting_for_response:
	case rx_call_sv_waiting_for_opcode:
		call->state++;
	case rx_call_cl_decoding_response:
	case rx_call_sv_decoding_opcode:
	case rx_call_sv_decoding_params:
		if (call->need_size == UINT_MAX) {
			/* A split mode call wants everything as it comes in,
			 * and is willing to settle for nothing also.
			 */
			if (call->data_count <= 0 && call->more_recv)
				return 0;
		} else if (call->data_count < call->need_size) {
			if (!call->more_recv) {
				/* Short data */
				debug("SHORT %u < %x\n", call->data_count, call->need_size);
				call->error_code = ENODATA;
				rxrpc_abort_call(call, 1);
			}
			return 0;
		}

		/* Handle reception of the opcode in a server-side call.  Note
		 * that a call might have no parameters, in which case we
		 * should've got !MSG_MORE and incremented the state again.
		 */
		if (call->state == rx_call_sv_decoding_opcode) {
			fprintf(stderr, "Need to determine service based on opcode\n");
			abort();
			call->state++;
			goto loop;
		}

		ret = call->decoder(call);
		if (ret < 0) {
			rxrpc_abort_call(call, 1);
			break;
		}

		if (ret == 1)
			goto loop; /* The decoder wants more data */

		call->state++;
	case rx_call_cl_wait_for_no_MSG_MORE:
	case rx_call_sv_wait_for_no_MSG_MORE:
		rxgen_dec_discard_excess(call);
		if (!call->more_recv) {
			call->state++;
			if (call->state == rx_call_sv_processing) {
				/* Prepare to encode the response */
				call->data_cursor = call->data_start = call->buffer_head->buf;
				call->data_stop = call->buffer_head->buf + RXGEN_BUFFER_SIZE;
				call->buffer_head->io_cursor = 0;
				call->data_count = 0;
				call->buffer_space = 0;

				/* Invoke the processor */
				call->processor(call);
				return 0;
			}
		}
		break;

	case rx_call_cl_complete:
	case rx_call_sv_complete ... rx_call_rejected_busy:
		break;

	case rx_call_sv_processing:
		call->failed(call);
		return 0;

	default:
		fprintf(stderr, "RxRPC: Recv in bad call state (%d)\n", call->state);
		abort();
	}

	return 0;
}

/*
 * Abort a call.
 */
void rxrpc_abort_call(struct rx_call *call, uint32_t abort_code)
{
	struct msghdr msg;
	size_t ctrllen;
	unsigned char control[128];

	if (call->known_to_kernel) {
		memset(control, 0, sizeof(control));
		ctrllen = 0;
		RXRPC_ADD_CALLID(control, ctrllen, (unsigned long)call);
		RXRPC_ADD_ABORT(control, ctrllen, abort_code);

		msg.msg_name		= &call->conn->peer;
		msg.msg_namelen		= sizeof(call->conn->peer);
		msg.msg_iov		= NULL;
		msg.msg_iovlen		= 0;
		msg.msg_control		= control;
		msg.msg_controllen	= ctrllen;
		msg.msg_flags		= 0;

		sendmsg(call->conn->fd, &msg, 0);
		call->known_to_kernel = 0;
	}
	call->state = rx_call_locally_aborted;
}

/*
 * Terminate a call, aborting it if necessary.
 */
void rxrpc_terminate_call(struct rx_call *call, uint32_t abort_code)
{
	struct rx_buf *cursor, *next;

	rxrpc_check_call(call);
	if (call->known_to_kernel)
		rxrpc_abort_call(call, abort_code);
	call->magic = 0x7a7b7c7d;
	for (cursor = call->buffer_head; cursor; cursor = next) {
		rxrpc_check_buf(cursor);
		next = cursor->next;
		cursor->magic = RXGEN_BUF_DEAD;
		free(cursor->buf);
		free(cursor);
	}
	if (call->decoder_cleanup)
		call->decoder_cleanup(call);
	free(call);
}

/*
 * Run a single call synchronously.
 */
int rxrpc_run_sync_call(struct rx_call *call)
{
	struct pollfd fds[1];

	while (call->known_to_kernel) {
		fds[0].fd = call->conn->fd;
		fds[0].events = POLLIN;
		fds[0].revents = 0;

		if (poll(fds, 1, -1) == -1) {
			fprintf(stderr, "Poll failed: %m\n");
			return -1;
		}
		if (rxrpc_recv_data(call->conn, false)) {
			fprintf(stderr, "rxrpc_recv_data failed: %m\n");
			return -1;
		}
	}

	switch (call->state) {
	case rx_call_cl_complete:
		debug("Call complete\n");
		return 0;
	case rx_call_remotely_aborted ... rx_call_rejected_busy:
		debug("Call failed\n");
		errno = call->error_code;
		return -1;
	default:
		fprintf(stderr, "RxRPC: Ended in bad call state (%d)\n", call->state);
		abort();
	}
}

/*
 * Discard excess received data
 */
int rxgen_dec_discard_excess(struct rx_call *call)
{
	struct rx_buf *spent, *cursor;
	unsigned io_cursor;

	rxrpc_check_call(call);

	while (cursor = call->buffer_head,
	       cursor != call->buffer_tail
	       ) {
		spent = cursor;
		call->buffer_head = cursor->next;
		spent->magic = RXGEN_BUF_DEAD;
		free(spent->buf);
		free(spent);
	}

	rxrpc_check_call(call);

	io_cursor = cursor->io_cursor;
	call->data_start = call->data_cursor = call->data_stop = cursor->buf + io_cursor;
	call->data_count = 0;

	if (__builtin_expect(call->error_code, 0))
		return -1;
	return 0;
}

/*
 * Encode a string of bytes
 */
int rxrpc_enc_blob(struct rx_call *call, const void *data, size_t size)
{
	struct rx_buf *cursor, *new;
	uint8_t *buf;
	size_t seg;

	rxrpc_check_call(call);

	if (size == 0)
		return 0;
	if (call->error_code)
		return -1;

	for (;;) {
		if (call->data_cursor < call->data_stop) {
			seg = call->data_stop - call->data_cursor;
			if (seg > size)
				seg = size;
			memcpy(call->data_cursor, data, seg);
			data += seg;
			size -= seg;
			call->data_cursor += seg;
			if (size <= 0)
				return 0;
		}

		rxrpc_check_call(call);

		if (rxrpc_post_enc(call) < 0)
			return -1;

		new = calloc(1, sizeof(struct rx_buf));
		if (!new)
			goto handle_oom;
		new->buf = buf = malloc(RXGEN_BUFFER_SIZE);
		if (!buf)
			goto handle_oom_buf;

		new->magic = RXGEN_BUF_MAGIC;
		cursor = call->buffer_tail;
		cursor->next = new;
		call->data_cursor = call->data_start = buf;
		call->data_stop = buf + RXGEN_BUFFER_SIZE;
		call->buffer_space += RXGEN_BUFFER_SIZE;
		call->buffer_tail = new;
	}

handle_oom_buf:
	free(new);
handle_oom:
	call->error_code = ENOMEM;
	return -1;
}

/*
 * Slow path for decoding from data read from the buffer list.
 */
void rxrpc_enc_slow(struct rx_call *call, net_xdr_t data)
{
	rxrpc_enc_blob(call, &data, sizeof(data));
}

/*
 * Decode a blob.
 *
 * This works progressively and so may need to be called multiple times for any
 * particular set.
 *
 * call->blob_size indicates how many bytes we need to extract in total and
 * call->blob_offset indicates how many we have done so far.  blob_offset is
 * updated before returning.
 */
void rxrpc_dec_blob(struct rx_call *call)
{
	unsigned needed, segment;

	rxrpc_check_call(call);
	rxrpc_post_dec(call);

	needed = call->blob_size - call->blob_offset;
	segment = call->data_stop - call->data_cursor;
	debug("DEC BLOB dc=%u bsize=%u seg=%u\n", call->data_count, needed, segment);

	if (segment > 0) {
		if (segment > needed)
			segment = needed;

		debug("DEC BLOB copy %u\n", segment);
		memcpy(call->blob + call->blob_offset, call->data_cursor, segment);
		call->blob_decoded += segment;
		call->blob_offset += segment;
		call->data_cursor += segment;
		if (call->blob_offset >= call->blob_size)
			return;
	}

	rxrpc_dec_advance_buffer(call);
}

/*
 * Progress the buffer chain during decoding.
 */
void rxrpc_dec_advance_buffer(struct rx_call *call)
{
	struct rx_buf *cursor, *spent;
	unsigned segment;
	uint8_t *new_stop;

	/* More data may have come into a partially filled buffer from which we
	 * previously read.
	 */
	cursor = call->buffer_head;
	segment = cursor->io_cursor;
	new_stop = cursor->buf + segment;
	if (call->data_stop >= new_stop) {
		/* This buffer must then be completely used as we're required to check
		 * amount received before reading it.
		 */
		if (new_stop != cursor->buf + RXGEN_BUFFER_SIZE)
			abort(); /* Didn't completely consume a buffer */
		if (call->buffer_tail == cursor)
			abort(); /* Unexpectedly out of data */

		/* Move to the next buffer */
		rxrpc_post_dec(call);
		spent = cursor;
		cursor = cursor->next;
		call->buffer_head = cursor;

		call->data_cursor = call->data_start = cursor->buf;
		segment = cursor->io_cursor;
		if (segment == 0)
			abort();
		new_stop = cursor->buf + segment;

		spent->magic = RXGEN_BUF_DEAD;
		free(spent->buf);
		free(spent);
	}

	call->data_stop = new_stop;
	rxrpc_check_call(call);
}

/*
 * Slow path for decoding a 4-byte integer read from the buffer list.
 */
uint32_t rxrpc_dec_slow(struct rx_call *call)
{
	net_xdr_t x;
	uint32_t ret;

	debug("DEC SLOW %lu %ld\n",
	      (unsigned long)call->data_cursor & 3,
	      call->data_cursor - call->data_stop);

	call->blob_size = 4;
	call->blob_offset = 0;
	call->blob = &x;

	/* We should only come here if there is sufficient data in the
	 * buffers for us to complete all the copy operation(s).
	 */
	if (call->data_count < call->blob_size)
		abort();

	while (call->blob_offset < call->blob_size)
		rxrpc_dec_blob(call);

	ret = ntohl(x);
	debug("DEC SLOW = %x\n", ret);
	return ret;
}
