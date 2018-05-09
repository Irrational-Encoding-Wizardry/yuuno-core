# -*- encoding: utf-8 -*-

# Yuuno - IPython + VapourSynth
# Copyright (C) 2018 StuxCrystal (Roland Netzsch <stuxcrystal@encode.moe>)
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
from multiprocessing import Connection
from threading import Thread, Lock, Event
from typing import Dict


class Handler(Thread):
    read: Connection
    write: Connection
    
    write_lock: Lock
    stopped: Event

    def __init__(self, read: Connection, write: Connection):
        super(Handler, self).__init__()
        self.read = read
        self.write = write
        
        self.stopped = Event()
        self.lock = Lock()

    def _handle(self, obj):
        pass

    def run(self):
        while not self.stopped.is_set():
            if not self.read.poll(1):
                continue

            self._handle(self.read.recv())

    def send(self, obj):
        with self.lock:
            self.write.send(obj)
        
    def stop(self):
        self.stopped.set()
        self.join()


class SubprocessResponder(Handler):
    """
    Implements a subprocess handler.
    """