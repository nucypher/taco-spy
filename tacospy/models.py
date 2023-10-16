from dataclasses import field, dataclass

from slugify import slugify


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
