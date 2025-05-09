import socket


def parse_proxy_file(path: str) -> list[str]:
    with open(path, encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def resolve_proxies(lines: list[str]) -> tuple[list[str], str, list[str]]:
    host_cache: dict[str, str] = {}
    resolved: list[str] = []
    first_old = first_new = None

    for raw in lines:
        parts = raw.split(":")
        host = parts[0]
        ip = host_cache.get(host)
        if ip is None:
            try:
                ip = socket.gethostbyname(host)
            except socket.gaierror:
                ip = host
            host_cache[host] = ip
        if first_old is None:
            first_old, first_new = host, ip
        parts[0] = ip
        resolved.append(":".join(parts))

    mapping = f"{first_old} -> {first_new}" if first_old != first_new else first_old
    return resolved, mapping, resolved[0].split(":")
