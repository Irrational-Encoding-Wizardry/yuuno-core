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
from yuuno import Yuuno
from yuuno.core.environment import Environment
from yuuno.net.multiplexer import ConnectionMultiplexer

from yuuno.server.connection import SocketConnection
from yuuno.server.client import Client

from socket import socket, AF_INET, SOCK_STREAM, SHUT_RDWR, timeout

from traitlets import Unicode, Int, Any
from traitlets.config import Application


class ServerEnvironment(Environment):
    """
    Defines the current environment used in Yuuno.
    """

    application: 'YuunoServerApplication' = Any()

    def additional_extensions(self):
        """
        Defines additional extensions that should be
        loaded inside the environment
        """
        return ['yuuno.multi_scripts.extension.MultiScriptExtension']

    def post_extension_load(self) -> None:
        """
        Called directly after extensions have been loaded
        (but not enabled)
        """
        pass

    def initialize(self) -> None:
        """
        Called by yuuno to tell it that yuuno has
        initialized to the point that it can now initialize
        interoperability for the given environment.
        """

    def deinitialize(self) -> None:
        """
        Called by yuuno before it deconfigures itself.
        """

class YuunoServerApplication(Application):

    ip = Unicode(default_value="127.0.0.1", config=True)
    port = Int(default_value=21987, config=True)

    manager = Unicode(config=True)

    aliases = {
        'log-level': 'Application.log_level',
        'ip': 'YuunoServerApplication.ip',
        'port': 'YuunoServerApplication.port',
        'manager': 'YuunoServerApplication.manager'
    }

    def init_client(self, sock, addr):
        self.log.info("New connection from %s:%d"%addr)
        conn = ConnectionMultiplexer(SocketConnection(sock))
        control = conn.register(None)
        Client(control, conn, addr, self.log, self._manager)

    def start(self):
        self.log.info("Yuuno Encode Server")
        self.yuuno = Yuuno.instance(parent=self, config=self.config)
        self.yuuno.environment = ServerEnvironment(parent=self.yuuno, application=self)
        self.yuuno.start()

        self._manager = self.yuuno.get_extension("MultiScript").get_manager(self.manager)

        sock = socket(AF_INET, SOCK_STREAM)
        sock.settimeout(1)
        sock.bind((self.ip, self.port))
        sock.listen(5)

        while True:
            try:
                client, addr = sock.accept()
            except timeout:
                continue
            self.init_client(client, addr)

if __name__ == "__main__":
    YuunoServerApplication.launch_instance()