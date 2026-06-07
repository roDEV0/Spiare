import asyncio

async def get_valid_data(requester, category, get_list, retries=3):
    check_list = await requester.post_request_batch(category, get_list)
    if not check_list:
        check_list = []
    if len(check_list) != len(get_list):
        if retries <= 0:
            print(f"{len(get_list) - len(check_list)} objects were unable to be fetched")
            return check_list, (set(get_list) - {item["uuid"] for item in check_list})
        print(f"Retrying {category}...")
        await asyncio.sleep(1)
        return await get_valid_data(requester, category, get_list, retries - 1)
    return check_list, []