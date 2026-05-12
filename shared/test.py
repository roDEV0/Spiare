from shared.http_requests import HTTPRequester
import aiohttp
import asyncio


async def main():
    session = aiohttp.ClientSession()
    http_requester = HTTPRequester(session)

    results = await http_requester.post_request("towns", "c0c3798e-4d6a-422b-98f9-b91421b7b0ed")
    print(results)

asyncio.run(main())