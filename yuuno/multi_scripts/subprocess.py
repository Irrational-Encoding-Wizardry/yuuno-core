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
from yuuno.core.environment import Environment

from traitlets import Instance

import multiprocessing
import pickle
import sys

class SubprocessEnvironment(Environment):
    """
    Implements a subprocess environment.
    """

    def initialize(self):
        pass

    def script_create(self) -> str:
        """
        Creates a new script. Returns the name of the script.
        """
        pass

    def script_dispose(self, name: str) -> None:
        """
        Disposes a script.
        """

    def script_results(self) -> Dict[str, str]:
        """
        Returns all result-ints.
        """

    def script_result_length(self, script: str, id: str) -> None:
        """
        Returns the length of a script
        """

    def script_result_extract(self, script: str, id: str, frame: int) -> bytes:
        """
        Extracts an image from a script.
        """