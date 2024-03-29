import asyncio
import os

from dotenv import load_dotenv
from pathlib import Path
import aiohttp
from hexbytes import HexBytes
from nucypher.blockchain.eth import domains

from constants import INTERVAL
from status import assign_node_status
from tdec import simple_taco
from utils import read_node_config

dotenv_path = Path('deploy/.env')
load_dotenv(dotenv_path=dotenv_path)
INVENTORY_PATH = os.environ.get("TACOSPY_INVENTORY_PATH", "deploy/inventory.yml")
print(f"Using inventory file: {INVENTORY_PATH}")


async def perform_health_checks(session, domain, node_type_dict, gague, data):
    for node_type, nodes in node_type_dict.items():
        tasks = [fetch_and_assign_status(session, node, domain, node_type, gauge=gague, data=data) for node in nodes]
        await asyncio.gather(*tasks)


async def health_check(gague, data):
    config = read_node_config(INVENTORY_PATH)
    while True:
        async with aiohttp.ClientSession() as session:
            group_tasks = [perform_health_checks(session, domain, node_type_dict, gague=gague, data=data) for
                           domain, node_type_dict in config.items()]
            await asyncio.gather(*group_tasks)
        await asyncio.sleep(INTERVAL)


async def check_lynx_tdec_health(gauge):
    goerli_endpoint = os.environ["GOERLI_PROVIDER_URI"]
    polygon_endpoint = os.environ["MUMBAI_PROVIDER_URI"]
    lynx_enrico_secret = HexBytes(os.environ["LYNX_DEMO_ENRICO_PRIVATE_KEY"])
    lynx_dkg_public_key = HexBytes(os.environ["LYNX_DEMO_DKG_PUBLIC_KEY"])
    while True:
        print("Checking Lynx tDEC health...")
        result = simple_taco(
            domain=domains.LYNX,
            eth_endpoint=goerli_endpoint,
            polygon_endpoint=polygon_endpoint,
            enrico_secret=lynx_enrico_secret,
            dkg_public_key=lynx_dkg_public_key,
        )
        gauge.set(int(result))  # Cast boolean to int; True will become 1, False will become 0
        await asyncio.sleep(INTERVAL)


async def check_tapir_tdec_health(gauge):
    sepolia_endpoint = os.environ["SEPOLIA_PROVIDER_URI"]
    polygon_endpoint = os.environ["MUMBAI_PROVIDER_URI"]
    tapir_enrico_secret = HexBytes(os.environ["TAPIR_DEMO_ENRICO_PRIVATE_KEY"])
    tapir_dkg_public_key = HexBytes(os.environ["TAPIR_DEMO_DKG_PUBLIC_KEY"])
    while True:
        print("Checking Tapir tDEC health...")
        result = simple_taco(
            domain=domains.TAPIR,
            eth_endpoint=sepolia_endpoint,
            polygon_endpoint=polygon_endpoint,
            enrico_secret=tapir_enrico_secret,
            dkg_public_key=tapir_dkg_public_key,
        )
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


async def fetch_and_assign_status(session, node, domain, node_type, gauge, data):
    label = f"{node.url}"
    http_status = await fetch_http_status(session, node.full_url, node.timeout)
    data[domain][node_type][label] = assign_node_status(node, http_status)

    # Update Prometheus metrics
    if http_status == 200:
        gauge.labels(group=domain, nested_key=node_type, name=label).set(1)
    else:
        gauge.labels(group=domain, nested_key=node_type, name=label).set(0)
