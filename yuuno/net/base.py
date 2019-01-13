from typing import List, Callable


class Connection(object):
    receive: Callable[[dict, List[bytes]], None]

    def __init__(self):
        pass

    def receive(self, data: dict, binaries: List[bytes]) -> None:
        pass

    def send(self, data: dict, binaries: List[bytes]) -> None:
        pass


class ChildConnection(Connection):

    def __init__(self, parent: Connection):
        super().__init__()
        self.parent = parent
        self.parent.receive = self._receive

    def _receive(self, d, b):
        self.receive(d, b)
    
    def send(self, data: dict, binaries: List[bytes]) -> None:
        self.parent.send(data, binaries)
