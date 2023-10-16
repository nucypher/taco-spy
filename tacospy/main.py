import asyncio
import threading
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

import prometheus_client
import requests
from flask import Flask, jsonify
from flask import request
from prometheus_client import Gauge

from constants import INTERVAL
from tasks import health_check, check_tdec_health
from utils import serialize_status, generate_summary

requests.packages.urllib3.disable_warnings()

app = Flask(__name__)
logger = app.logger

node_status = defaultdict(lambda: defaultdict(dict))

taco_metric = Gauge('taco_metric', 'Description of taco_metric')
node_up = Gauge('node_up', 'Node availability', ['group', 'nested_key', 'name'])


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
            health_check(gague=node_up, data=node_status),
            check_tdec_health(gauge=taco_metric),
        )
        await asyncio.sleep(INTERVAL)


def run_async_health_check_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main_loop())


if __name__ == "__main__":
    t = threading.Thread(target=run_async_health_check_loop)
    t.start()
    prometheus_client.start_http_server(addr='0.0.0.0', port=8001)
    app.run(host="0.0.0.0", port=8000)
