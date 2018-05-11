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
    starter: ScriptProviderInfo

    pool: Pool
    _next_process: Subprocess

    def __init__(self, starter: ScriptProviderInfo):
        self.instances = {}
        self.starter = starter
        ctx: Context = get_context("spawn")
        self.pool = ctx.Pool()
        self._next_process = None
        self._checkout_next()

    def _checkout_next(self):
        prev = self._next_process
        self._next_process = Subprocess(self.pool, self.starter)
        return prev

    def create(self, name: str, *, initialize=False) -> Script:
        """
        Creates a new script environment.
        """
        if name in self.instances and self.instances[name].alive:
            raise ValueError("A core with this name already exists.")
        process = self._checkout_next()
        self.instances[name] = process
        if initialize:
            process.initialize()
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
