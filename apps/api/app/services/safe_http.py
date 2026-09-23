"""Bounded public HTTP requests with pinned DNS and original TLS identity."""
import asyncio
import ipaddress
import socket
from urllib.parse import urljoin

import httpx


async def public_addresses(host, port):
    if host.rstrip('.').lower() in {'localhost', 'localhost.localdomain', 'metadata.google.internal', 'host.docker.internal'}:
        raise ValueError('Destination is not public')
    try:
        records = await asyncio.to_thread(socket.getaddrinfo, host, port, type=socket.SOCK_STREAM)
    except OSError:
        raise ValueError('Destination DNS unavailable') from None
    addresses = list(dict.fromkeys(row[4][0] for row in records))
    if not addresses or any(not ipaddress.ip_address(ip).is_global or ipaddress.ip_address(ip).is_multicast for ip in addresses):
        raise ValueError('Destination is not public')
    return addresses


async def public_request(method, url, *, max_bytes, timeout=20, headers=None, content=None, redirects=0):
    # A fresh client per hop prevents reuse across different pinned TLS identities.
    async with asyncio.timeout(timeout):
        for hop in range(redirects + 1):
            original = httpx.URL(url)
            if original.scheme not in {'http', 'https'} or not original.host or original.username or original.password:
                raise ValueError('Invalid public HTTP destination')
            addresses = await public_addresses(original.host, original.port or (443 if original.scheme == 'https' else 80))
            pinned = original.copy_with(host=addresses[0])
            request_headers = {**(headers or {}), 'Host': original.netloc.decode('ascii')}
            async with httpx.AsyncClient(timeout=httpx.Timeout(timeout, connect=5), follow_redirects=False, trust_env=False) as client:
                async with client.stream(method, pinned, headers=request_headers, content=content,
                                         extensions={'sni_hostname': original.host}) as response:
                    if response.is_redirect:
                        if hop >= redirects or method != 'GET':
                            raise ValueError('Redirect is not permitted')
                        target = urljoin(str(original), response.headers['location'])
                        if original.scheme == 'https' and httpx.URL(target).scheme != 'https':
                            raise ValueError('TLS downgrade is not permitted')
                        url = target
                        continue
                    body = bytearray()
                    async for chunk in response.aiter_bytes():
                        if len(body) + len(chunk) > max_bytes:
                            raise ValueError('Outbound response exceeds configured size limit')
                        body.extend(chunk)
                    clean_headers = {k:v for k,v in response.headers.items() if k.lower() not in {'content-encoding', 'content-length', 'transfer-encoding'}}
                    return httpx.Response(response.status_code, headers=clean_headers, content=bytes(body),
                                          request=httpx.Request(method, original))
    raise ValueError('Redirect limit exceeded')
