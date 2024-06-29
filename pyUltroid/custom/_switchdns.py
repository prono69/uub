# switch to cloudflare's 1.1.1.1 if dnspython is installed.
# install httpx to have DNS over https


__all__ = tuple()


try:
    from dns import resolver
except ImportError:
    print("Using System-level DNS!")
else:
    res = resolver.Resolver()
    res.nameservers = [
        "1.1.1.1",
        "1.0.0.1",
        "2606:4700:4700::1111",
        "2606:4700:4700::1001",
        "8.8.4.4",
    ]
    resolver.override_system_resolver(res)
