from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

_TRACKING_PARAMS = {"fbclid", "gclid", "mc_eid", "ref", "ref_src"}


def normalize_apply_url(url: str) -> str:
    parts = urlsplit(url)
    scheme = "https"
    host = parts.netloc.lower()

    path = parts.path
    if path != "/" and path.endswith("/"):
        path = path[:-1]

    query_pairs = [
        (k, v)
        for k, v in parse_qsl(parts.query)
        if not k.lower().startswith("utm_") and k.lower() not in _TRACKING_PARAMS
    ]
    query_pairs.sort()
    query = urlencode(query_pairs)

    return urlunsplit((scheme, host, path, query, ""))
