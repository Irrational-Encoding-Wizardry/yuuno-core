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
from typing import Dict, Optional, Iterator, TYPE_CHECKING

from yuuno.core.extension import Extension
if TYPE_CHECKING:
    from yuuno.multi_scripts.script import ScriptManager


class MultiScriptExtension(Extension):

    _name = "MultiScript"
    managers: Dict[str, 'ScriptManager']

    @classmethod
    def is_supported(self):
        return True

    def __init__(self, *args, **kwargs):
        super(MultiScriptExtension, self).__init__(*args, **kwargs)
        self.managers = {}

    def initialize(self):
        pass

    def register_manager(self, name: str, manager: 'ScriptManager'):
        """
        Registers a new manager.

        :param name:     The name of the manager.
        :param manager:  The manager to register.
        :return: The registered manager.
        """
        if name in self.managers:
            raise ValueError("A manager with this name already exists.")
        self.managers[name] = manager

    def get_manager(self, name: str) -> Optional['ScriptManager']:
        """
        Returns the manager with the givern name.
        :param name:  The name of the manager.
        :return:      The manager that has been registered with this name.
        """
        return self.managers.get(name, None)

    def get_manager_names(self) -> Iterator[str]:
        """
        Returns all currently registered managers.

        :return: The currently registered manager.
        """
        yield from self.managers.keys()

    def deinitialize(self):
        for manager in self.managers.values():
            manager.dispose_all()
        self.managers = {}
