# switch to cloudflare's 1.1.1.1 if dnspython is installed.
# install httpx to have DNS over https

__all__ = tuple()


import socket

try:
    from dns import resolver
except ImportError:
    print("Using System-level DNS!")
else:
    res = resolver.Resolver(filename=None)
    res.nameservers = [
        "1.1.1.1",
        "1.0.0.1",
        "2606:4700:4700::1111",
        "2606:4700:4700::1001",
        "8.8.4.4",
    ]
    resolver.default_resolver = res

    _original_getaddrinfo = socket.getaddrinfo

    def custom_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
        try:
            answer = resolver.resolve(host, "A")
            ip_address = answer[0].to_text()
            return _original_getaddrinfo(ip_address, port, family, type, proto, flags)
        except resolver.NXDOMAIN:
            print("errror")
            return _original_getaddrinfo(host, port, family, type, proto, flags)

    socket.getaddrinfo = custom_getaddrinfo
