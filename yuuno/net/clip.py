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
from yuuno.net.handler import RequestReplyClientConnection
from yuuno.net.handler import RequestReplyMethod
from yuuno.net.base import Connection

from yuuno.clip import Clip, Frame, RawFormat, Size
from yuuno.utils import future_yield_coro, gather

from concurrent.futures import Future


class ConnectionFrame(Frame):

    def __init__(self, connclip: 'ConnectionClip', no: int, format: RawFormat, size: Size):
        self.connclip = connclip
        self._no = no
        self._format = format
        self._size = size

    def format(self):
        return self._format

    def get_size(self):
        return self._size

    @future_yield_coro
    def can_render(self, format: RawFormat) -> Future:
        """
        Checks if the frame can be rendered in the given format.
        """
        data = (yield self.connclip._render({'frame': self._no, 'format': format.to_json(), 'plane': None}))[0]
        return data['size'] is not None

    def render(self, plane: int, format: RawFormat) -> Future:
        """
        Renders the frame in the given format.
        Note that the frame can always be rendered in the format given by the
        format attribute.
        """
        sz, buf = yield self.connclip._render({'frame': self._no, 'format': format.to_json(), 'plane': plane})
        if not buf:
            raise ValueError("Unsupported format")
        return buf[0]

    def get_metadata(self) -> Future:
        """
        Store meta-data about the frame.
        """
        return (yield self.connclip._metadata({'frame': self._no}))[0]


class ConnectionClip(RequestReplyClientConnection, Clip):
    _length = RequestReplyMethod("length")
    _metadata = RequestReplyMethod("metadata")
    _format = RequestReplyMethod("format")
    _render = RequestReplyMethod("render")
    _frame = RequestReplyMethod("frame")


    def __init__(self, parent: Connection, length: int):
        RequestReplyClientConnection.__init__(self, parent)
        self.length = length

    @classmethod
    @future_yield_coro
    def from_connection(cls, connection: Connection) -> 'ConnectionClip':
        _clip = cls(connection, None)
        length, _ = yield _clip._length()
        _clip.length = length['length']
        return _clip

    def __len__(self) -> int:
        """
        Calculates the length of the clip in frames.

        :return: The amount of frames in the clip
        """
        return self.length

    @future_yield_coro
    def get_metadata(self) -> Future:
        """
        Retrieve meta-data about the clip.
        """
        raw_meta, _ = yield self._metadata({'frame': None})
        return raw_meta

    @future_yield_coro
    def __getitem__(self, item: int) -> Future:
        """
        Extracts the frame from the clip.

        :param item: The frame number
        :return: A frame-instance with the given data.
        """
        _f = self._format()
        _s = self._render({'plane': None, 'frame': item})
        yield gather([_f, _s])

        format = RawFormat.from_json(_f.result())
        size = Size(*_s.result()[0]["size"])
        raise ConnectionFrame(self, item, format, size)