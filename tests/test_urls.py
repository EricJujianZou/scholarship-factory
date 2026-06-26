from scholarship_factory.urls import normalize_apply_url


def test_tracking_params_stripped():
    a = normalize_apply_url("https://example.com/apply?utm_source=newsletter&id=1")
    b = normalize_apply_url("https://example.com/apply?id=1")
    assert a == b


def test_trailing_slash_normalized():
    a = normalize_apply_url("https://example.com/apply/")
    b = normalize_apply_url("https://example.com/apply")
    assert a == b


def test_http_and_https_equal():
    a = normalize_apply_url("http://example.com/apply")
    b = normalize_apply_url("https://example.com/apply")
    assert a == b


def test_different_urls_do_not_collide():
    a = normalize_apply_url("https://example.com/apply-a")
    b = normalize_apply_url("https://example.com/apply-b")
    assert a != b
