import sys
from pathlib import Path
from types import ModuleType
from contextlib import contextmanager

from typing import Dict, Union

from yuuno.clip import Clip
from yuuno.utils import inline_resolved
from yuuno.core.environment import Environment

from yuuno.multi_scripts.script import Script
from yuuno.multi_scripts.subprocess.provider import ScriptProvider
from yuuno.multi_scripts.subprocess.process import LocalSubprocessEnvironment


@contextmanager
def shadow_module(name: str, module: ModuleType):
    before = sys.modules.get(name, None)
    sys.modules[name] = module
    try:
        yield
    finally:
        if before is None:
            del sys.modules[name]
        else:
            sys.modules[name] = before


class DummyModule(object):
    pass


class VSStandaloneScript(Script):

    def __init__(self, env: Environment):
        import vapoursynth
        self.vapoursynth = vapoursynth
        self.env = env
        self._current_code_exec = 0
        self.init_ns()

    def init_ns(self):
        self.main_module = ModuleType("__vapoursynth__")
        self.namespace = self.main_module.__dict__

    @property
    def alive(self) -> bool:
        """
        Checks if the environment is still alive.
        """
        return True

    def initialize(self) -> None:
        """
        Called when the script is going to be
        initialized.

        We need this to find out if script-creation
        is actually costly.
        """
        pass

    def dispose(self) -> None:
        """
        Disposes the script.
        """
        self.vapoursynth.clear_outputs()

    @inline_resolved
    def get_results(self) -> Dict[str, Clip]:
        """
        Returns a dictionary with clips
        that represent the results of the script.
        """
        return {
            str(k): self.env.parent.wrap(v)
            for k, v in self.vapoursynth.get_outputs().items()
        }

    @property
    def next_code_no(self) -> int:
        self._current_code_exec += 1
        return self._current_code_exec

    @inline_resolved
    def execute(self, code: Union[str, Path]) -> None:
        """
        Executes the code inside the environment
        """

        if isinstance(code, Path):
            file = code
            with open(code, "rb") as f:
                code = f.read()
        else:
            file = "<yuuno:%r>"

        f = compile(code, filename=file, dont_inherit=True, mode="exec")
        with shadow_module('__vapoursynth__', self.main_module):
            with shadow_module('__main__', self.main_module):
                exec(f, self.namespace, {})


class VSScriptProvider(ScriptProvider):

    def initialize(self, env: 'LocalSubprocessEnvironment') -> None:
        """
        Called after _all_ extensions have been loaded
        and the system is ready to be loaded.
        """
        self.script = VSStandaloneScript(env)

    def deinitialize(self) -> None:
        """
        Called when the environment is being disabled.
        """
        self.script.dispose()

    def get_script(self) -> 'Script':
        """
        Returns the script.
        """
        return self.script

    @classmethod
    def get_registration(cls):
        return
