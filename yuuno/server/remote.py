from yuuno.net.handler import RequestReplyClientConnection, RequestReplyMethod
from yuuno.net.multiplexer import ConnectionMultiplexer
from yuuno.net.clip import ConnectionClip

from yuuno.server.connection import SocketConnection

from yuuno.multi_scripts.script import Script, ScriptManager

from yuuno.utils import future_yield_coro, resolve, gather
from yuuno.clip import Clip

from typing import Optional
from concurrent.futures import Future
from socket import socket, AF_INET, SOCK_STREAM 


class RemoteClip(Clip):

    def __init__(self, length, clip_creator, dispose=None) -> None:
        self.clip_creator = clip_creator
        self._dispose = dispose
        self._disposed = False
        self._inst = None
        self._length = length

    @property
    def _clip(self):
        if self._inst is None:
            self._inst = self.clip_creator()
            if not isinstance(self._inst, Future):
                self._inst = resolve(self._inst)
        return self._inst

    def __len__(self) -> int:
        """
        Calculates the length of the clip in frames.

        :return: The amount of frames in the clip
        """
        return len(self._length)

    @future_yield_coro
    def get_metadata(self) -> Future:
        """
        Retrieve meta-data about the clip.
        """
        clip = yield self._clip
        return (yield clip.get_metadata())

    @future_yield_coro
    def __getitem__(self, item: int) -> Future:
        """
        Extracts the frame from the clip.

        :param item: The frame number
        :return: A frame-instance with the given data.
        """
        clip = yield self._clip
        return (yield clip[item])

    def dispose(self):
        if self._disposed:
            return

        if self._inst is not None:
            if self._inst.running():
                # Postpone disposal until the clip is actually ready. 
                self._inst.add_done_callback(lambda f: self.dispose())
                return

            # Resolving the proxy failed.
            if self._inst.exception() is not None:
                pass

            # Initiate the disposal.
            if self._dispose is not None:
                self._dispose(self._inst.result())

            # Call the underlying dispose function.
            self._inst.dispose()

        self._disposed = True


class RemoteScript(RequestReplyClientConnection, Script):
    _results    = RequestReplyMethod("results")
    _execute    = RequestReplyMethod("execute")
    _open_clip  = RequestReplyMethod("open_clip")
    _close_clip = RequestReplyMethod("close_clip")


    def __init__(self, parent, name, manager):
        self._script_multiplexer = ConnectionMultiplexer(parent)
        super().__init__(self._script_multiplexer.register(None))
        self.manager = manager
        self.name = name

        self._alive = True
    
    @property
    def alive(self) -> bool:
        """
        Checks if the environment is still alive.
        """
        return self.manager._is_alive(self.name)

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
        self._alive = False
        self.manager._destroy(self.name)


    @future_yield_coro
    def get_results(self) -> Future:
        """
        Returns a dictionary with clips
        that represent the results of the script.
        """
        def _make_clip(name, length):
            name = f"{id(self)}/{id(_make_clip)}/{name}"

            @future_yield_coro
            def _connect():
                conn = ClipConnection(self._script_multiplexer.register(name), length)
                yield self._open_clip({'name': name, 'target': name})
                return conn

            def _disconnect(clip):
                self._close_clip({'name': name})

            return RemoteClip(length, _connect, _disconnect)

        result, _ = yield self._results()
        return {
            name: _make_clip(name, length)
            for name, length in result.items()
        }

    def execute(self, code: str) -> Future:
        """
        Executes the code inside the environment
        """
        yield self._execute({'script': code})


class RemoteScriptManager(RequestReplyClientConnection, ScriptManager):
    """
    Manages and creates script-environments.
    """

    _list_scripts = RequestReplyMethod("list_scripts")
    _create_script = RequestReplyMethod("create_script")
    _destroy_script = RequestReplyMethod("destroy_script")

    def __init__(self, connection):
        self._main_connection = connection
        self.connection = ConnectionMultiplexer(connection)
        self._scripts = {}
        super().__init__(self.connection.register(None))
    
    @classmethod
    def from_socket(cls, sock):
        if not isinstance(sock, socket):
            _sock = socket(AF_INET, SOCK_STREAM)
            _sock.connect(sock)
            sock = _sock
        return cls(SocketConnection(sock))

    def create(self, name: str, *, initialize=False) -> Script:
        """
        Creates a new script environment.
        """
        self._create_script({'name': name})
        return self.get(name)

    def get(self, name: str) -> Optional[Script]:
        """
        Returns the script with the given name.
        """
        if name in self._scripts:
            return self._scripts[name]

    @future_yield_coro
    def dispose_all(self) -> None:
        """
        Disposes all scripts
        """
        s, _ = yield self._list_scripts()
        yield gather([self._destroy(n) for n in s])

    @future_yield_coro
    def disable(self) -> None:
        """
        Disposes all scripts and tries to clean up.
        """
        yield self.dispose_all()
        self._main_connection.shutdown()

    def _is_alive(self, name):
        return name in self._scripts

    def _destroy(self, name):
        if self._is_alive(name):
            del self._scripts[name]
        return self._destroy_script({'name': name})
