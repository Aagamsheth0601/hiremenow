from backend.services.yc_scraper import _public_company_url


def test_contact_lookup_rejects_local_and_private_hosts() -> None:
    assert _public_company_url("http://127.0.0.1:8000/admin") is None
    assert _public_company_url("http://169.254.169.254/latest/meta-data") is None
    assert _public_company_url("http://localhost:8000") is None
    assert _public_company_url("http://company.local") is None
    assert _public_company_url("http://user:password@example.com") is None
