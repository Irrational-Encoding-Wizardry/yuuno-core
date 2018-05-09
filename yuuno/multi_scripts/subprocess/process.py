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

from traitlets.utils.importstring import import_item
from traitlets import Instance

from yuuno.core.environment import Environment
from yuuno.multi_scripts.script import Script
from yuuno.multi_scripts.subprocess.provider import ScriptProviderInfo, ScriptProvider


class LocalSubprocessEnvironment(Environment):
    """
    
    """
    _provider_meta: ScriptProviderInfo

    write: Connection = Instance(Connection)
    read: Connection = Instance(Connection)
    provider: ScriptProvider = Instance(ScriptProvider)


    def additional_extensions(self) -> List[str]:
        """
        Defines additional extensions that should be
        loaded inside the environment
        """
        result = []

        for ext in self._provider_meta.extensions:
            if not ext.startswith("="):
                ext = "="+ext

            name, extension = [s.strip() for s in ext.split("=")]
            extension = import_item(extension)

            if name:
                extension._name = name
            result.append(extension)

        return result

    def post_extension_load(self) -> None:
        """
        Called directly after extensions have been loaded
        (but not enabled)
        """

        # Let's initialize it here.
        provider_class = import_item(self._provider_meta.providercls)
        self.provider = provider_class(**self._provider_meta.providerparams)

    def initialize(self) -> None:
        """
        Called by yuuno to tell it that yuuno has
        initialized to the point that it can now initialize
        interoperability for the given environment.
        """
        self.provider.initialize()

    def run(self):
        """
        Wait for commands.
        """

    def deinitialize(self) -> None:
        """
        Called by yuuno before it deconfigures itself.
        """
        self.provider.deinitialize()

    @classmethod
    def main(self, argv):
        # Parse args
        read: Connection = pickle.loads(b64decode(argv[1]))
        write: Connection = pickle.loads(b64decode(argv[2]))

        # 
        from yuuno import Yuuno
        yuuno = Yuuno.instance(parent=None)
        env = cls(parent=yuuno, read=read, write=write)
        yuuno.environment = env

        # Wait for the ProviderMeta to be set. (Zygote initialize)
        env._provider_meta = read.recv()
        yuuno.start()


class Subprocess(Script):

    def __init__(self):
        self.process: subprocess.Popen = None
        self.self_read, self.self_write = Pipe(duplex=False)
        self.child_read, self.child_write = Pipe(duplex=False)

    @property
    def alive(self) -> bool:
        return self.process is not None and self.process.poll() is None

    def initialize(self):
        if self.alive:
            return

        modname = ['-m', __name__]
        if __name__ == "__main__":
            modname = [__file__]

        b64read_remote = b64encode(pickle.dumps(self.self_read))
        b64write_remote = b64encode(pickle.dumps(self.child_write))
        self.self_read.close()
        self.child_write.close()

        self.process = subprocess.Popen(
            [sys.executable] + modname + [b64read_remote, b64write_remote]
        )


if __name__ == "__main__":
    