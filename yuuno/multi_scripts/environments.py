from typing import Callable, Any, MutableMapping
from yuuno.multi_scripts.subprocess.proxy import Request


class RequestManager:

    handlers: MutableMapping[str, Callable[[Request], Any]]

    def register_command(self, name: str, cb: Callable[[Request], Any]) -> None:
        """
        Registers a new command.
        :param name:   The name of the
        :param cb:
        :return:
        """
        self.handlers[name] = cb
