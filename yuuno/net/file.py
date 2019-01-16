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
import struct
from yuuno.net.base import Connection


class FileConnection(Connection):

    def __init__(self, fp_r, fp_w):
        super().__init__(self)
        self.fp_r = fp_r
        self.fp_w = fp_w

    def read(self):
        """
        Call this function to read the next frame.
        """
        data = self.fp_r.read(8)
        frame_sz = struct.unpack('>I', data)
        data = self.fp_r.read(frame_sz)
        if len(data) < frame_sz:
            raise IOException("Frame size did not match.")
        self.parse(data)

    def write(self, data: bytes) -> None:
        header = struct.pack(">I", len(data))
        self.fp_w.write(header)
        self.fp_w.write(data)