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
from typing import TYPE_CHECKING, Callable, Any, TypeVar, Generic

from yuuno.clip import Clip, Frame

if TYPE_CHECKING:
    from yuuno.vs.vsscript.script import VSScript


T = TypeVar("T", Clip, Frame)


class WrappedMixin(Generic[T]):
    env: 'VSScript'
    parent: T

    def __init__(self, env: 'VSScript', parent: T):
        self.env = env
        self.parent = parent

    @staticmethod
    def wrap(name: str) -> Callable[..., Any]:
        def _func(self: 'WrappedMixin', *args, **kwargs):
            func = getattr(self.parent, name)
            result = self.env.perform(lambda: func(*args, **kwargs)).result()
            if isinstance(result, Frame):
                result = WrappedFrame(self.env, result)
            return result
        return _func


class WrappedFrame(WrappedMixin[Frame], Frame):
    to_pil = WrappedMixin.wrap('to_pil')
    to_raw = WrappedMixin.wrap('to_raw')


class WrappedClip(WrappedMixin[Clip], Clip):
    __len__ = WrappedMixin.wrap('__len__')
    __getitem__ = WrappedMixin.wrap('__getitem__')

    @property
    def clip(self):
        return self.parent.clip
