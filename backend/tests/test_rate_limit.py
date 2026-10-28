import asyncio
from types import SimpleNamespace

from backend import rate_limit


def request(path, token=''):
    return SimpleNamespace(url=SimpleNamespace(path=path), method='POST',
                           headers={'authorization': token}, client=SimpleNamespace(host='127.0.0.1'))


async def accepted(_request):
    return SimpleNamespace(status_code=200)


def test_session_limit_cannot_be_bypassed_with_arbitrary_headers():
    rate_limit._calls.clear()
    for i in range(100):
        assert asyncio.run(rate_limit.guard_expensive_actions(request('/sessions', str(i)), accepted)).status_code == 200
    assert asyncio.run(rate_limit.guard_expensive_actions(request('/sessions', 'new-header'), accepted)).status_code == 429


def test_reparse_and_upload_share_the_same_budget():
    rate_limit._calls.clear()
    for _ in range(5):
        assert asyncio.run(rate_limit.guard_expensive_actions(request('/resumes/latest/reparse', 'visitor'), accepted)).status_code == 200
    assert asyncio.run(rate_limit.guard_expensive_actions(request('/resumes', 'visitor'), accepted)).status_code == 429


def test_random_identities_cannot_grow_memory_without_limit(monkeypatch):
    rate_limit._calls.clear()
    monkeypatch.setattr(rate_limit, '_MAX_BUCKETS', 2)
    for token in ['a', 'b']:
        assert asyncio.run(rate_limit.guard_expensive_actions(request('/resumes', token), accepted)).status_code == 200
    assert asyncio.run(rate_limit.guard_expensive_actions(request('/resumes', 'c'), accepted)).status_code == 429
    assert len(rate_limit._calls) == 2


def test_expired_buckets_are_removed(monkeypatch):
    rate_limit._calls.clear()
    monkeypatch.setattr(rate_limit.time, 'monotonic', lambda: 10000)
    monkeypatch.setattr(rate_limit, '_last_cleanup', 0)
    rate_limit._calls[('resumes', 'expired')].append(1)
    asyncio.run(rate_limit.guard_expensive_actions(request('/resumes'), accepted))
    assert ('resumes', 'expired') not in rate_limit._calls
