import asyncio
import threading
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from dataclasses import field, dataclass
from typing import Dict, List

import aiohttp
import requests
import yaml
from flask import Flask, jsonify
from flask import request
from prometheus_client import Gauge, start_http_server
from slugify import slugify

from tdec import simple_taco

app = Flask(__name__)
logger = app.logger

requests.packages.urllib3.disable_warnings()

# To store the status of nodes
node_status = defaultdict(lambda: defaultdict(dict))

taco_metric = Gauge('taco_metric', 'Description of taco_metric')
node_up = Gauge('node_up', 'Node availability', ['group', 'nested_key', 'name'])

executor = ThreadPoolExecutor()

# Define a mapping of HTTP status codes to status messages
HTTP_STATUS_CODES_TO_MESSAGE = {
    200: "OK",
    201: "Created",
    204: "No Content",
    400: "Bad Request",
    401: "Unauthorized",
    403: "Forbidden",
    404: "Not Found",
    408: "Request Timeout",
    500: "Internal Server Error",
    502: "Bad Gateway",
    503: "Service Unavailable",
    504: "Gateway Timeout"
    # Add more as needed
}


@dataclass
class NodeConfig:
    url: str
    port: int
    check: str
    name: str
    timeout: int = field(default=2)

    @property
    def full_url(self):
        return f"{self.url}:{self.port}/{self.check}"

    @property
    def slug(self):
        return slugify(self.name) if self.name else slugify(self.full_url)


@dataclass
class NodeStatus:
    name: str
    status: str
    timestamp: int
    url: str
    port: int
    check: str
    name: str
    timeout: int = field(default=2)
    code: int = None
    message: str = None


def read_node_config() -> Dict[str, Dict[str, List[NodeConfig]]]:
    with open("inventory.yml", "r") as f:
        config = yaml.safe_load(f)
    result = {
        outer_key: {
            inner_key: [NodeConfig(**node) for node in inner_nodes]
            for inner_key, inner_nodes in outer_value.items()
        }
        for outer_key, outer_value in config.items()
    }
    return result


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


def assign_node_status(node, http_status) -> NodeStatus:
    common = dict(
        timestamp=int(time.time()),
        check=node.check,
        timeout=node.timeout,
        port=node.port,
        url=node.url
    )
    if http_status == 200:
        return NodeStatus(
            name=node.name,
            status="up",
            code=http_status,
            message=HTTP_STATUS_CODES_TO_MESSAGE.get(http_status),
            **common
        )
    elif isinstance(http_status, str):
        return NodeStatus(name=node.name, status=http_status, **common)
    else:
        return NodeStatus(
            name=node.name,
            status="down",
            code=http_status,
            message=HTTP_STATUS_CODES_TO_MESSAGE.get(http_status, "Unknown Status"),
            **common
        )


async def fetch_and_assign_status(session, node, group, nested_key):
    label = f"{node.url}"
    http_status = await fetch_http_status(session, node.full_url, node.timeout)
    node_status[group][nested_key][label] = assign_node_status(node, http_status)

    # Update Prometheus metrics
    if http_status == 200:
        node_up.labels(group=group, nested_key=nested_key, name=label).set(1)
    else:
        node_up.labels(group=group, nested_key=nested_key, name=label).set(0)


async def perform_health_checks(session, group, nested_dict):
    for nested_key, nodes in nested_dict.items():
        tasks = [fetch_and_assign_status(session, node, group, nested_key) for node in nodes]
        await asyncio.gather(*tasks)


async def health_check():
    config = read_node_config()
    while True:
        async with aiohttp.ClientSession() as session:
            group_tasks = [perform_health_checks(session, group, nested_dict) for group, nested_dict in config.items()]
            await asyncio.gather(*group_tasks)
        await asyncio.sleep(5)


async def check_tdec_health():
    logger.info("Performing tDec health check")
    result = await simple_taco()
    taco_metric.set(int(result))  # Cast boolean to int; True will become 1, False will become 0


def serialize_status(status_data: dict) -> dict:
    result = {}
    for nested_key, nested_status_data in status_data.items():
        nested_result = {}
        for label, _status in nested_status_data.items():
            if isinstance(_status, NodeStatus):
                nested_result[label] = asdict(_status)
            else:
                nested_result[label] = "Not a NodeStatus instance"
        result[nested_key] = nested_result
    return result


def generate_summary(status_data: dict) -> dict:
    _summary = {}
    for group, nested_status_data in status_data.items():
        group_summary = {
            "up": 0,
            "down": 0,
            "client_error": 0,
            "error": 0,
        }

        for nested_key, statuses in nested_status_data.items():
            for label, _node_status in statuses.items():
                if isinstance(_node_status, NodeStatus):
                    _status = _node_status.status
                    group_summary[_status] = group_summary.get(_status, 0) + 1
                else:
                    group_summary["error"] += 1
        _summary[group] = group_summary
    return _summary


@app.route("/summary", methods=["GET"])
def summary():
    summary_data = generate_summary(node_status)
    return jsonify(summary_data)


@app.route("/status", methods=["GET"])
def status():
    _summary = generate_summary(node_status)
    ordered_response = {"timestamp": int(time.time()), "summary": _summary}
    group_filter = request.args.get('domain')
    if group_filter:
        filtered_status = serialize_status(node_status.get(group_filter, {}))
        ordered_response["details"] = {group_filter: filtered_status}
    else:
        serializable_status = {group: serialize_status(nodes) for group, nodes in node_status.items()}
        ordered_response["details"] = serializable_status
    return jsonify(ordered_response)


async def main_loop():
    while True:
        await asyncio.gather(
            health_check(),
            check_tdec_health(),
        )
        await asyncio.sleep(10)


def run_async_health_check_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main_loop())


if __name__ == "__main__":

    # Start Prometheus client
    start_http_server(8001)

    # Start Flask app
    t = threading.Thread(target=run_async_health_check_loop)
    t.start()
    app.run(host="0.0.0.0", port=8000)
