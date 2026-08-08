from scholarship_factory.logos import logo_from_page

# Real markup from a live Greenhouse apply page (2026-08-08).
GREENHOUSE_HTML = """<html><head>
<meta property="og:image" content="https://s2-recruiting.cdn.greenhouse.io/external_greenhouse_job_boards/logos/400/621/800/original/MCG-Logo.png?1570752388"/>
</head><body>a job</body></html>"""

# Real markup from a live Lever apply page (2026-08-08).
LEVER_HTML = """<html><head>
<meta property="og:image" content="https://lever-client-logos.s3-us-west-2.amazonaws.com/b8300af6-1586196845320.png" />
</head><body>a job</body></html>"""

# Ashby serves only its own chrome — no employer logo anywhere in the page.
ASHBY_HTML = """<html><head>
<link rel="apple-touch-icon" sizes="180x180" href="https://cdn.ashbyprd.com/cdn_assets/87a4/apple-touch-icon.png" />
<meta property="og:title" content="Etched Jobs" />
</head><body>a job</body></html>"""


def test_reads_the_greenhouse_board_logo():
    assert logo_from_page(GREENHOUSE_HTML).endswith("MCG-Logo.png?1570752388")


def test_reads_the_lever_client_logo():
    assert "lever-client-logos" in logo_from_page(LEVER_HTML)


def test_reversed_attribute_order_still_matches():
    html = (
        '<meta content="https://lever-client-logos.s3.amazonaws.com/x.png" '
        'property="og:image">'
    )
    assert logo_from_page(html).endswith("x.png")


def test_ats_chrome_is_not_an_employer_logo():
    assert logo_from_page(ASHBY_HTML) is None


def test_a_careers_banner_is_not_a_logo():
    # Greenhouse-hosted boards also carry hero images; only /logos/ counts
    html = (
        '<meta property="og:image" '
        'content="https://images.stripeassets.com/careers_-_main-en-US_2x.png"/>'
    )
    assert logo_from_page(html) is None


def test_page_without_og_image_yields_nothing():
    assert logo_from_page("<html><body>plain</body></html>") is None


def test_non_http_url_is_rejected():
    html = '<meta property="og:image" content="//lever-client-logos.s3.com/x.png"/>'
    assert logo_from_page(html) is None
