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