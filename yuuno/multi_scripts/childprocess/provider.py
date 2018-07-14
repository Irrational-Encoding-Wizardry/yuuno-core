from typing import Optional
from yuuno.multi_scripts.subprocess.provider import ScriptProvider
from yuuno.multi_scripts.script import ScriptManager, Script


class ChildProcessManager(ScriptManager):

    def create(self, name: str, *, initialize=False, **config) -> Script:
        """
        Creates a new script environment.
        """
        raise NotImplementedError

    def get(self, name: str) -> Optional[Script]:
        """
        Returns the script with the given name.
        """
        raise NotImplementedError

    def dispose_all(self) -> None:
        """
        Disposes all scripts
        """
        raise NotImplementedError

    def disable(self) -> None:
        """
        Disposes all scripts and tries to clean up.
        """
        raise NotImplementedError


class ChildProcessProvider(ScriptProvider):

    def __init__(self, yuuno, **kwargs):
        super().__init__(yuuno)

    def initialize(self, env: 'LocalSubprocessEnvironment') -> None:
        """
        Called after _all_ extensions have been loaded
        and the system is ready to be loaded.
        """
        pass

    def deinitialize(self) -> None:
        """
        Called when the environment is being disabled.
        """
        pass

    def get_script(self) -> 'Script':
        """
        Returns the script.
        """
        pass

    def deploy_onto_manager(self, manager):
        pass
