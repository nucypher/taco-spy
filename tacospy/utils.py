from dataclasses import asdict
from typing import Dict, List

import yaml

from tacospy.models import NodeConfig, NodeStatus



def read_node_config(inventory_path) -> Dict[str, Dict[str, List[NodeConfig]]]:
    with open(inventory_path, "r") as f:
        config = yaml.safe_load(f)
    result = {
        domain: {
            node_type_label: [NodeConfig(**node) for node in nodes]
            for node_type_label, nodes in node_types.items()
        }
        for domain, node_types in config.items()
    }
    return result


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
