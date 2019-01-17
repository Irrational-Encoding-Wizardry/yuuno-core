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
from yuuno.net.base import BinaryConnection

from threading import Thread, Lock
from socket import socket
import struct


class SocketConnection(BinaryConnection):

    def __init__(self, sock: socket):
        super().__init__()
        self.sock = sock
        self.alive = False

        self.wlock = Lock()
        self.rthread = Thread(target=self._run)
        self.rthread.daemon = True
        self.rthread.start()

    def _run(self):
        def _readall(length):
            data = self.sock.recv(length)
            buffers = []
            while length > 0 and data:
                buffers.append(data)
                length -= len(data)
                if length == 0:
                    break
                data = self.sock.recv(length)

            if not data:
                raise IOError("Socket closed unexpectedly")

            return b''.join(buffers)

        self.alive = True
        while self.alive:
            framesz = struct.unpack(">I", _readall(4))[0]
            self.parse(_readall(framesz))

    def stop(self):
        self.alive = False
        self.sock.shutdown()


    def write(self, data: bytes):
        with self.wlock:
            self.sock.sendall(struct.pack(">I", len(data)))
            self.sock.sendall(data)