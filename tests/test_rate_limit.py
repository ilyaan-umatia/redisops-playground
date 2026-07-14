from httpx import AsyncClient


async def test_fixed_window_blocks_requests_over_limit(client: AsyncClient) -> None:
    headers = {"X-Client-ID": "fixed-client"}

    responses = [await client.get("/rate-limit-demo/fixed", headers=headers) for _ in range(6)]

    assert all(response.status_code == 200 for response in responses[:5])
    assert responses[4].json()["remaining"] == 0
    assert responses[5].status_code == 429
    assert int(responses[5].headers["Retry-After"]) > 0


async def test_sliding_window_blocks_requests_over_limit(client: AsyncClient) -> None:
    headers = {"X-Client-ID": "sliding-client"}

    responses = [await client.get("/rate-limit-demo/sliding", headers=headers) for _ in range(6)]

    assert all(response.status_code == 200 for response in responses[:5])
    assert responses[5].status_code == 429
    assert responses[5].json() == {"detail": "Rate limit exceeded"}


async def test_rate_limit_requires_valid_client_id(client: AsyncClient) -> None:
    missing = await client.get("/rate-limit-demo/fixed")
    invalid = await client.get("/rate-limit-demo/fixed", headers={"X-Client-ID": "bad id!"})

    assert missing.status_code == 422
    assert invalid.status_code == 422
