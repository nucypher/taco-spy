import asyncio

import aiohttp

from constants import INTERVAL
from status import assign_node_status
from tdec import simple_taco
from utils import read_node_config


async def perform_health_checks(session, group, nested_dict, gague, data):
    for nested_key, nodes in nested_dict.items():
        tasks = [fetch_and_assign_status(session, node, group, nested_key, gauge=gague, data=data) for node in nodes]
        await asyncio.gather(*tasks)


async def health_check(gague, data):
    config = read_node_config()
    while True:
        async with aiohttp.ClientSession() as session:
            group_tasks = [perform_health_checks(session, group, nested_dict, gague=gague, data=data) for
                           group, nested_dict in config.items()]
            await asyncio.gather(*group_tasks)
        await asyncio.sleep(INTERVAL)


async def check_tdec_health(gauge):
    while True:
        print("Checking tDEC health...")
        result = simple_taco()
        gauge.set(int(result))  # Cast boolean to int; True will become 1, False will become 0
        await asyncio.sleep(INTERVAL)


async def fetch_http_status(session, url, timeout):
    try:
        async with session.get(url, timeout=timeout, ssl=False) as response:
            return response.status
    except aiohttp.ClientError as e:
        print(e)
        return "client_error"
    except Exception as e:
        print(e)
        return "error"


async def fetch_and_assign_status(session, node, group, nested_key, gauge, data):
    label = f"{node.url}"
    http_status = await fetch_http_status(session, node.full_url, node.timeout)
    data[group][nested_key][label] = assign_node_status(node, http_status)

    # Update Prometheus metrics
    if http_status == 200:
        gauge.labels(group=group, nested_key=nested_key, name=label).set(1)
    else:
        gauge.labels(group=group, nested_key=nested_key, name=label).set(0)
