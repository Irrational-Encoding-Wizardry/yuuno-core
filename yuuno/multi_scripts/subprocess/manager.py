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
from typing import Optional, Dict
from multiprocessing import Pool, get_context
from multiprocessing.context import BaseContext as Context

from yuuno.multi_scripts.script import ScriptManager, Script
from yuuno.multi_scripts.subprocess.process import Subprocess
from yuuno.multi_scripts.subprocess.provider import ScriptProviderInfo


class SubprocessScriptManager(ScriptManager):
    """
    Manages and creates script-environments.
    """

    instances: Dict[str, Subprocess]
    default_provider_info: ScriptProviderInfo

    pool: Pool
    _next_process: Subprocess

    def __init__(self, default_provider_info=None):
        self.instances = {}
        self.default_provider_info = default_provider_info
        ctx: Context = get_context("spawn")
        self.pool = ctx.Pool()
        self._next_process = None
        self._checkout_next()

    def _checkout_next(self):
        prev = self._next_process
        self._next_process = Subprocess(self.pool, self.default_provider_info)
        return prev

    def create(self, name: str, *, initialize=False, provider_info=None, **config) -> Script:
        """
        Creates a new script environment.
        """
        if name in self.instances and self.instances[name].alive:
            raise ValueError("A core with this name already exists.")
        process = self._checkout_next()
        self.instances[name] = process

        if provider_info is None:
            provider_info = self.default_provider_info

        if initialize:
            process.initialize(provider_info=provider_info, **config)
        return process

    def get(self, name: str) -> Optional[Script]:
        """
        Returns the script with the given name.
        """
        return self.instances.get(name)

    def dispose_all(self) -> None:
        """
        Disposes all scripts
        """
        for process in list(self.instances.values()):
            if process.alive:
                return
            process.dispose()

    def disable(self) -> None:
        """
        Disposes all scripts and tries to clean up.
        """
        self.dispose_all()
        self._next_process.dispose()
