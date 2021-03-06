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
import abc
from typing import TYPE_CHECKING
from collections.abc import Sequence
from yuuno.vs.flags import Features

if TYPE_CHECKING:
    import vapoursynth as vs


class AlphaOutputClipMeta(abc.ABCMeta):
    vs = None

    def __subclasscheck__(self, subclass):
        if self.vs is None:
            import vapoursynth as vs
            self.vs = vs

        if Features.SUPPORT_ALPHA_OUTPUT_TUPLE:

            return issubclass(self.vs.AlphaOutputTuple, subclass)

        return False

    @classmethod
    def __instancecheck__(self, obj):

        if self.__subclasscheck__(self, type(obj)):
            return True

        if not isinstance(obj, Sequence):
            return False

        if len(obj) != 2:
            return False

        return all(i is None or isinstance(i, self.vs.VideoNode) for i in obj)


class AlphaOutputClip(metaclass=AlphaOutputClipMeta):
    def __getitem__(self, item: int) -> 'vs.VideoNode': pass
    def __len__(self) -> int: pass
