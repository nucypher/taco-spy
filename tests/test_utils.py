from tacospy.utils import read_node_config

def test_read_node_config():
    config = read_node_config()
    assert config