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
from yuuno.net.handler import RequestReplyServerConnection, ClipHandler
from yuuno.net.multiplexer import ConnectionMultiplexer

from yuuno.utils import future_yield_coro


class ScriptController(RequestReplyServerConnection):

    def __init__(self, parent, multiplexer, client, script):
        super().__init__(parent)
        self.multiplexer = multiplexer

        self.client = client
        self.script = script

        self.opened_clips = {}

    @future_yield_coro
    def on_results(self, data, binaries):
        results = {
            name: len(script)
            for name, script in (yield self.script.results()).items()
        }
        return results, []

    @future_yield_coro
    def on_execute(self, data, binaries):
        yield self.script.execute(data['script']), []

    @future_yield_coro
    def on_open_clip(self, data, binaries):
        name = data['name']
        if name in self.opened_clips:
            raise ValueError("Name already taken")

        clips = yield self.script.results()

        target = data['target']
        if target not in clips:
            raise ValueError("Unknown clip.")

        clip = clips[name]
        
        handler = ClipHandler(self.multiplexer.register(name), clip)
        self.opened_clips[name] = (clip, handler)
        return {}, []

    def on_close_clip(self, data, binaries):
        self.multiplexer.unregister(data['name'])
        return {}, []


class Controller(RequestReplyServerConnection):

    def __init__(self, parent, multiplexer,client):
        super().__init__(parent)
        self.multiplexer = multiplexer
        self.client = client
        self.scripts = {}

    def on_list_scripts(self, data, binaries):
        return list(self.scripts.keys()), []

    def on_create_script(self, data, binaries):
        name = data.get("name")
        if name is None:
            return {'name': None}, []

        script = self.mgr.create(self.client.name + "::" + name, initialize=True)
        self.scripts[name] = script
        conn = ConnectionMultiplexer(self.multiplexer.register(name))
        ScriptController(conn.register(None), conn, self.client, script)
        return {'name': name}, []

    def on_destroy_script(self, data, binaries):
        self.scripts.pop(name).dispose()
        self.multiplexer.unregister(data["name"])

        return {}, []


class Client(object):

    def __init__(self, connection, base, addr, log, mgr):
        self.name = f"script::{addr[0]}::{addr[1]}"
        self.mgr = mgr
        self.log = log
        self.base_connection = base
        self.connection = connection

        self.scripts = {}

        