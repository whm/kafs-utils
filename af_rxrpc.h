/* AF_RXRPC definitions
 *
 * Copyright (C) 2014 Red Hat, Inc. All Rights Reserved.
 * Written by David Howells (dhowells@redhat.com)
 *
 * This program is free software; you can redistribute it and/or
 * modify it under the terms of the GNU General Public Licence
 * as published by the Free Software Foundation; either version
 * 2 of the Licence, or (at your option) any later version.
 */

#ifndef AF_RXRPC_H
#define AF_RXRPC_H

#include <sys/socket.h>
#include <netinet/in.h>

/*
 * Rx kerberos security abort codes
 * - unfortunately we have no generalised security abort codes to say things
 *   like "unsupported security", so we have to use these instead and hope the
 *   other side understands
 */
#define RXKADINCONSISTENCY	19270400	/* security module structure inconsistent */
#define RXKADPACKETSHORT	19270401	/* packet too short for security challenge */
#define RXKADLEVELFAIL		19270402	/* security level negotiation failed */
#define RXKADTICKETLEN		19270403	/* ticket length too short or too long */
#define RXKADOUTOFSEQUENCE	19270404	/* packet had bad sequence number */
#define RXKADNOAUTH		19270405	/* caller not authorised */
#define RXKADBADKEY		19270406	/* illegal key: bad parity or weak */
#define RXKADBADTICKET		19270407	/* security object was passed a bad ticket */
#define RXKADUNKNOWNKEY		19270408	/* ticket contained unknown key version number */
#define RXKADEXPIRED		19270409	/* authentication expired */
#define RXKADSEALEDINCON	19270410	/* sealed data inconsistent */
#define RXKADDATALEN		19270411	/* user data too long */
#define RXKADILLEGALLEVEL	19270412	/* caller not authorised to use encrypted conns */

/*
 * AF_RXRPC socket address type. 
 */
struct sockaddr_rxrpc {
	sa_family_t	srx_family;	/* address family (AF_RXRPC) */
	unsigned short	srx_service;	/* service desired */
	unsigned short	transport_type;	/* type of transport socket (SOCK_DGRAM) */
	unsigned short	transport_len;	/* length of transport address */
	union {
		sa_family_t family;		/* transport address family */
		struct sockaddr_in sin;		/* IPv4 transport address */
		struct sockaddr_in6 sin6;	/* IPv6 transport address */
	} transport;
};

/* cmsg_level value and sockopt level */
#define SOL_RXRPC		272

/* cmsg_type values */
#define RXRPC_USER_CALL_ID	1	/* User call ID specifier */
#define RXRPC_ABORT		2	/* Abort request / notification */
#define RXRPC_ACK		3	/* [Server] RPC op final ACK received */
#define RXRPC_RESPONSE		4	/* [Server] security response received */
#define RXRPC_NET_ERROR		5	/* network error received */
#define RXRPC_BUSY		6	/* server busy received */
#define RXRPC_LOCAL_ERROR	7	/* local error generated */
#define RXRPC_PREPARE_CALL_SLOT	8	/* Propose user call ID specifier for next call */

/* sockopt optname */
#define RXRPC_SECURITY_KEY		1	/* [clnt] set client security key */
#define RXRPC_SECURITY_KEYRING		2	/* [srvr] set ring of server security keys */
#define RXRPC_EXCLUSIVE_CONNECTION	3	/* [clnt] use exclusive RxRPC connection */
#define RXRPC_MIN_SECURITY_LEVEL	4	/* minimum security level */

/* RXRPC_MIN_SECURITY_LEVEL sockopt values */
#define RXRPC_SECURITY_PLAIN	0	/* plain secure-checksummed packets only */
#define RXRPC_SECURITY_AUTH	1	/* authenticated packets */
#define RXRPC_SECURITY_ENCRYPT	2	/* encrypted packets */

/*
 * Add a call ID to a control message sequence.
 */
#define RXRPC_ADD_CALLID(control, ctrllen, id)				\
do {									\
	void *__buffer = (control);					\
	unsigned long *__data;						\
	struct cmsghdr *__cmsg;						\
	__cmsg = __buffer + (ctrllen);					\
	__cmsg->cmsg_len	= CMSG_LEN(sizeof(*__data));		\
	__cmsg->cmsg_level	= SOL_RXRPC;				\
	__cmsg->cmsg_type	= RXRPC_USER_CALL_ID;			\
	__data = (void *)CMSG_DATA(__cmsg);				\
	*__data = (id);							\
	(ctrllen) += __cmsg->cmsg_len;					\
									\
} while (0)

/*
 * Add an abort instruction to a control message sequence.
 */
#define RXRPC_ADD_ABORT(control, ctrllen, abort_code)			\
do {									\
	void *__buffer = (control);					\
	unsigned int *__data;						\
	struct cmsghdr *__cmsg;						\
	__cmsg = __buffer + (ctrllen);					\
	__cmsg->cmsg_len	= CMSG_LEN(sizeof(__data));		\
	__cmsg->cmsg_level	= SOL_RXRPC;				\
	__cmsg->cmsg_type	= RXRPC_ABORT;				\
	__data = (void *)CMSG_DATA(__cmsg);				\
	*__data = (abort_code);						\
	(ctrllen) += __cmsg->cmsg_len;					\
									\
} while (0)

#endif /* AF_RXRPC_H */
