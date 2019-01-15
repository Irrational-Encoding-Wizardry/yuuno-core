import json
import struct
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


class BinaryConnection(Connection):

    def read(self, data: bytes) -> None:
        pass

    def parse(self, data: bytes) -> None:
        data = memoryview(data)
        index = 0

        sz = struct.calcsize("HI")
        length, first_blob_length = struct.unpack('>HI', data[index:index+sz])
        index += sz

        binary_blobs = struct.unpack(f'>{length}I', data[index:index+sz])
        index += sz
        
        text_blob = json.loads(data[index:index+first_blob_length].decode('utf-8'))
        index += first_blob_length

        data = []
        for blob_size in binary_blobs:
            data.append(bytes(data[index:index+blob_size]))
            index += blob_size

        self.receive(text_blob, [])


    def write(self, data: bytes) -> None:
        pass

    def send(self, data: dict, binaries: List[bytes]) -> None:
        data_blob = json.dumps(data).encode('utf-8')
        raw = struct.pack(
            f">HI{len(binaries)}I"
            len(binaries)+1,
            len(data_blob)
            *map(len, binaries)
        )
        self.write(raw)