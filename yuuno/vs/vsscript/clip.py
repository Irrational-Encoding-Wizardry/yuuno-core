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

from yuuno.utils import future_yield_coro, auto_join
from yuuno.vs.clip import VapourSynthClip, VapourSynthFrame

if TYPE_CHECKING:
    from yuuno.vs.vsscript.script import VSScript


class Wrapper:
    @classmethod
    def from_script(cls, script, *args, **kwargs):
        import vapoursynth as vs
        env = script.perform(lambda: vs.vpy_current_environment()).result()
        return cls(env, *args, **kwargs)


class WrappedFrame(VapourSynthFrame, Wrapper):

    def __init__(self, env, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.env = env

    def get_environment(self):
        return self.env


class WrappedClip(VapourSynthClip, Wrapper):


    def __init__(self, env, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.env = env

    def get_environment(self):
        return self.env

    def make_frame(self, fcl, fobj, allow_compat=True):
        return WrappedFrame(self.env, fcl, fobj, allow_compat)