from typing import Callable, List

from yuuno.net.base import ChildConnection, Connection


class MultiplexedConnection(Connection):

    def __init__(self, name: str, parent: Connection):
        super().__init__()
        self.name = name
        self.parent = parent

    def send(self, data: dict, binaries: List[bytes]) -> None:
        self.parent.send({'target': self.name, 'payload': data}, binaries)


class ConnectionMultiplexer(ChildConnection):

    def __init__(self, parent: Connection):
        super().__init__(parent)
        self.targets = {}

    def register(self, name: str) -> Connection:
        multiplexer = MultiplexedConnection(name, self)
        self.targets[name] = multiplexer
        return multiplexer

    def unregister(self, name):
        self.targets.pop(name)

    def send(self, data: dict, binaries: List[bytes])-> None:
        self.parent.send(data, binaries)

    def receive(self, data: dict, binaries: List[bytes]) -> None:
        target = data['target']
        payload = data['payload']
        if target not in self.targets:
            return
        self.targets[target].receive(payload, binaries)