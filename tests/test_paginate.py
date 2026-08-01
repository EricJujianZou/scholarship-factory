from scholarship_factory.paginate import next_page_url


def test_anchor_rel_next_is_followed():
    html = '<a href="/page/2/" rel="next">Older</a>'
    assert next_page_url(html, "https://e.com/blog/") == "https://e.com/page/2/"


def test_link_rel_next_in_head_is_followed():
    html = '<head><link rel="next" href="https://e.com/?page=2"></head>'
    assert next_page_url(html, "https://e.com/") == "https://e.com/?page=2"


def test_rel_with_multiple_tokens_is_matched():
    html = '<a rel="noopener next" href="/p2">next</a>'
    assert next_page_url(html, "https://e.com/") == "https://e.com/p2"


def test_next_text_without_rel_is_ignored():
    """Link text is ambiguous enough to walk into the wrong part of a site."""
    html = '<a href="/somewhere-else">Next</a>'
    assert next_page_url(html, "https://e.com/") is None


def test_no_next_link_returns_none():
    assert next_page_url("<a href='/x'>x</a>", "https://e.com/") is None


def test_self_referential_next_is_not_a_next_page():
    html = '<a rel="next" href="https://e.com/blog/">same</a>'
    assert next_page_url(html, "https://e.com/blog/") is None
