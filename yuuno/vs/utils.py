# -*- encoding: utf-8 -*-

# Yuuno - IPython + VapourSynth
# Copyright (C) 2017,2018 StuxCrystal (Roland Netzsch <stuxcrystal@encode.moe>)
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
import enum
import types
import functools
from typing import AnyStr, Callable, TypeVar
from concurrent.futures import Future

from traitlets.utils.importstring import import_item


T = TypeVar("T")


def inline_resolved(func: Callable[..., T]) -> Callable[..., Future]:
    @functools.wraps(func)
    def _wrapped(*args, **kwargs) -> Future:
        fut = Future()
        fut.set_running_or_notify_cancel()
        try:
            result_value = func(*args, **kwargs)
        except Exception as e:
            fut.set_exception(e)
        else:
            fut.set_result(result_value)
        return fut
    return _wrapped


def get_proxy_or_core(*, resolve_proxy=False):
    """
    Returns the current core-proxy or a core instance for pre Vapoursynth R37 installations
    :param resolve_proxy: If you have R37 or later, force resolving the proxy object
    :return: A proxy or the actual core.
    """
    try:
        from vapoursynth import core
        if resolve_proxy:
            core = core.core
    except ImportError:
        from vapoursynth import get_core
        core = get_core()
    return core


def filter_or_import(name: AnyStr) -> Callable:
    """
    Loads the filter from the current core or tries to import the name.

    :param name: The name to load.
    :return:  A callable.
    """
    core = get_proxy_or_core()

    try:
        ns, func = name.split(".", 1)
        return getattr(getattr(core, ns), func)
    except (ValueError, AttributeError):
        return import_item(name)


def is_single():
    import vapoursynth
    if not hasattr(vapoursynth, 'Environment'):
        return vapoursynth._using_vsscript
    return vapoursynth.Environment.is_single()


class MessageLevel(enum.IntEnum):
    mtDebug = 0
    mtWarning = 1
    mtCritical = 2
    mtFatal = 3


class VapourSynthEnvironment(object):

    def __init__(self):
        self.previous_outputs = {}
        self.old_outputs = None

    @staticmethod
    def get_global_outputs():
        import vapoursynth
        if hasattr(vapoursynth, "get_outputs"):
            return vapoursynth.get_outputs()
        return types.MappingProxyType(vapoursynth._get_output_dict("OutputManager.get_outputs"))

    def _set_outputs(self, output_dict):
        import vapoursynth
        vapoursynth.clear_outputs()
        for k, v in output_dict.items():
            v.set_output(k)

    @property
    def outputs(self):
        if self.old_outputs is None:
            return self.previous_outputs
        return self.get_global_outputs()

    def __enter__(self):
        self.old_outputs = self.get_global_outputs().copy()
        self._set_outputs(self.previous_outputs)

    def __exit__(self, exc, val, tb):
        self.previous_outputs = self.get_global_outputs().copy()
        self._set_outputs(self.old_outputs)
        self.old_outputs = None


