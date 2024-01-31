from tacospy.utils import read_node_config

def test_read_node_config():
    config = read_node_config("tests/example_inventory.yml")
    assert config.keys() == {"tapir", "lynx"}
    assert config["tapir"].keys() == {"nodes", "porters"}
    assert len(config["tapir"]["nodes"]) == 5