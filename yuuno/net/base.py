# -*- encoding: utf-8 -*-

# Yuuno - IPython + VapourSynth
# Copyright (C) 2019 StuxCrystal (Roland Netzsch <stuxcrystal@encode.moe>)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
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

    def closed(self) -> None:
        pass

    def shutdown(self) -> None:
        pass


class ChildConnection(Connection):

    def __init__(self, parent: Connection):
        super().__init__()
        self.parent = parent
        self.parent.receive = self._receive
        self.parent.shutdown = self._shutdown

        self._receive_func = None
        self._closed_func = None

    def _receive(self, d, b):
        self.receive(d, b)

    def _shutdown(self):
        self.shutdown()

    @property
    def receive(self):
        return self._receive_func

    @receive.setter
    def receive(self, value):
        if self._closed_func is not None:
            self.closed()
        self._receive_func = value

    @property
    def closed(self):
        if self._closed_func is None:
            return

        def _wrapper():
            self._closed_func()
            self._closed_func = None
        return _wrapper

    @closed.setter
    def closed(self, value):
        self.closed_func = value
    
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

        print("<", repr(text_blob))
        self.receive(text_blob, [])


    def write(self, data: bytes) -> None:
        pass

    def send(self, data: dict, binaries: List[bytes]) -> None:
        print(">", repr(data))
        data_blob = json.dumps(data).encode('utf-8')
        raw = struct.pack(
            f">HI{len(binaries)}I",
            len(binaries)+1,
            len(data_blob),
            *map(len, binaries)
        )
        self.write(raw)