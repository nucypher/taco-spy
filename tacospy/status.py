import time

from constants import HTTP_STATUS_CODES_TO_MESSAGE
from models import NodeStatus


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
