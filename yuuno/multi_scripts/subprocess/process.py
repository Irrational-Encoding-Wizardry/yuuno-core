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
import sys
import pickle
import subprocess
from base64 import b64decode, b64encode
from multiprocessing import Connection, Pipe

from yuuno.core.environment import Environment
from yuuno.multi_scripts.script import Script

class LocalSubprocessEnvironment(Environment):
    """
    
    """
    _additional_extensions = []
    _script_provider_module = None

    @classmethod
    def main(self, argv):
        # Parse args
        read = b64decode(argv[1])
        write = b64decode(argv[2])

        from yuuno import Yuuno
        yuuno = Yuuno.instance(parent=None)
        env = cls(parent=yuuno, read=read, write=write)
        yuuno.environment = env

        
        


class Subprocess(Script):

    def __init__(self):
        self.process: subprocess.Popen = None
        self.read, self.write = Pipe(duplex=True)

    @property
    def alive(self) -> bool:
        return self.process is not None and self.process.poll() is None

    def initialize(self):
        if self.alive:
            return

        modname = ['-m', __name__]
        if __name__ == "__main__":
            modname = [__file__]

        b64read_remote = b64encode(pickle.dumps(self.write))
        b64write_remote = b64encode(pickle.dumps(self.read))

        self.process = subprocess.Popen(
            [sys.executable] + modname + [b64read_remote, b64write_remote]
        )


if __name__ == "__main__":
