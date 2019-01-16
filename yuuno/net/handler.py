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
from yuuno.net.base import Connection, ChildConnection
from yuuno.utils import future_yield_coro
from yuuno.clip import Clip, Frame
from yuuno.yuuno import Yuuno


from concurrent.futures import Future
from typing import Callable, List
from threading import Lock
import traceback


def _raise(exc):
    raise exc


class RequestReplyServerConnection(ChildConnection):

    @future_yield_coro
    def receive(self, data: dict, binaries: List[bytes]) -> None:
        rqid = data.get('id')
        if rqid is None:
            return

        type = data.get('type')
        if type is None:
            return

        payload = data.get('payload', {})
        
        try:
            func = getattr(self, f'on_{type}', lambda d, b: _raise(ValueError("Unknown function.")))
            res = func(payload, binaries)
            if isinstance(res, Future):
                res, binaries = yield res
            else:
                res, binaries = res

        except Exception as e:
            tb = traceback.print_exception(type(e), e, e.__traceback__)
            tb = ''.join(tb)
            self.send({
                'id': rqid,
                'type': 'failure',
                'payload': {
                    'message': tb
                }
            })

        else:
            self.send({
                'id': rqid,
                'type': 'response',
                'payload': res
            }, binaries)


class RequestReplyMethod:

    def __init__(self, name):
        self.name = name

    def __get__(self, instance, owner):
        def _func(data=(), binaries=None):
            if binaries is None:
                binaries = {}
            return owner._request(instance, self.name, data, binaries)
        return _func


class RequestReplyClientConnection(ChildConnection):

    def __init__(self, parent: Connection) -> None:
        super().__init__(parent)
        self._current_id = 0
        self._id_lock = Lock()
        self._running_requests = {}

    def _increment_id(self) -> int:
        with self._id_lock:
            res = self._current_id
            self._current_id += 1
            return res

    def _request(self, name: str, data: dict, binaries: List[bytes]) -> None:
        future = Future()
        rid = f'{id(self)}--{self._increment_id()}'
        self._running_requests[rid] = future
        self.send({
            'id': rid,
            'type': name,
            'payload': data
        }, binaries)
        return future

    def receive(self, data: dict, binaries: List[bytes]) -> None:
        rqid = data.get('id')
        if rqid is None:
            return

        future = self._running_requests.pop(rqid, None)
        if future is None:
            return

        type = data.get('type', 'response')
        if type == "failure":
            future.set_exception(RuntimeError(data.get('payload', {}).get('message', '')))
        else:
            future.set_result((data.get('payload', None), binaries))


class ClipHandler(RequestReplyServerConnection):

    def __init__(self, parent: Connection, clip: Clip, yuuno: Yuuno):
        super().__init__(parent)
        self.clip = clip
        self.yuuno = yuuno
        self._cache = [None, None]

    def frame_at(self, frame):
        if self._cache[0] == frame:
            return self._cache[1]
        self._cache = frame, self.clip[frame]
        return self._cache

    def on_length(self, data, binaries) -> None:
        return {'length': len(self.clip)}, []

    @future_yield_coro
    def on_metadata(self, data, binaries) -> None:
        frame = data.get('frame', None)
        if frame is None:
            return (yield self.clip.get_metadata()), []

        if frame > len(self.clip):
            frame = len(self.clip)-1

        frame = yield self.frame_at(frame)
        return (yield frame.get_metadata()), []

    @future_yield_coro
    def on_format(self, data, binaries) -> None:
        frame = data.get('frame', 0)
        if frame > len(self.clip):
            frame = len(self.clip)-1

        frame = yield self.frame_at(frame)
        return frame.format().to_json(), []
        
    @future_yield_coro
    def on_size(self, data, binaries) -> None:
        frame = data.get('frame', 0)
        if frame > len(self.clip):
            frame = len(self.clip)-1

        frame = yield self.frame_at(frame)
        return frame.get_size(), []

    @future_yield_coro
    def on_render(self, data, binaries) -> None:
        frame = data.get('frame', 0)
        if frame > len(self.clip):
            frame = len(self.clip)-1

        frame = yield self.frame_at(frame)
        format = data.get('format')
        if format is None:
            format = frame.format()
        else:
            format = RawFormat.from_json(format)
        
        if not (yield frame.can_render(format)):
            return {'size': None}, []
    
        plane = data.get('plane', None)
        if plane is None:
            return {size: frame.get_size()}, []

        return {'size': frame.get_size()}, [(yield frame.render(plane, format))]

    @future_yield_coro
    def on_frame(self, data, binaries) -> None:
        frame = data.get('frame', 0)
        if frame > len(self.clip):
            frame = len(self.clip)-1

        frame = yield self.frame_at(frame)
        return {'size': frame.get_size()}, [self.yuuno.output.bytes_of(frame)]