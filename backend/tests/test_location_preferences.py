import pytest
from backend.models import Job, JobPreferences
from backend.routers.jobs import _matches_refinements


def matches(preference, location, modes=None):
    return _matches_refinements(
        Job(title='Engineer', locations=[location], tags=[], source_url='https://example.com/job', company_name='Example', company_slug='example'),
        JobPreferences(locations=[preference] if preference else [], work_modes=modes or []),
    )


@pytest.mark.parametrize('alias', ['US', 'USA', 'U.S.', 'U.S.A.', 'United States', 'United States of America', ' us '])
@pytest.mark.parametrize('listing', ['San Francisco, CA, US', 'New York, USA', 'Remote (US)', 'Austin, TX'])
def test_us_country_aliases(alias, listing):
    assert matches(alias, listing)
    assert not matches(alias, 'Mumbai, India')


@pytest.mark.parametrize('alias', ['India', 'IN', 'Bharat'])
def test_india_country_aliases(alias):
    assert matches(alias, 'Mumbai, India')
    assert not matches(alias, 'Austin, TX')


def test_city_blank_and_work_modes():
    assert matches('New York, USA', 'New York, US')
    assert not matches('York', 'Yorkshire, UK')
    assert matches('', 'Mumbai, India')
    assert matches('US', 'Remote (US)', ['remote'])
    assert not matches('US', 'Austin, TX', ['remote'])


def test_remote_does_not_override_country_restrictions():
    assert not matches("US", "Remote (India)", ["remote"])
    assert not matches("India", "Remote (US)", ["remote"])
    assert matches("US", "Remote", ["remote"])
