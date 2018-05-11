from pathlib import Path
from typing import TYPE_CHECKING

from yuuno.utils import future_yield_coro
from yuuno.multi_scripts.script import Script

if TYPE_CHECKING:
    from yuuno.multi_scripts.subprocess.process import LocalSubprocessEnvironment


class BasicCommands(object):

    script: Script
    env: 'LocalSubprocessEnvironment'

    def __init__(self, script: Script, env: 'LocalSubprocessEnvironment'):
        self.script = script
        self.env = env

    @property
    def commands(self):
        return {
            'script/subprocess/execute': self.execute,
            'script/subprocess/results': self.results,
            'script/subprocess/results/raw': self.frame_data,
            'script/subprocess/results/meta': self.frame_meta
        }

    @future_yield_coro
    def execute(self, type: str, code: str):
        if type == 'path':
            code = Path(code)
        return (yield self.script.execute(code))

    @future_yield_coro
    def results(self):
        outputs = yield self.script.get_results()
        return {
            str(k): len(v)
            for k, v in outputs.items()
        }

    @future_yield_coro
    def frame_meta(self, id: str, frame: int):
        outputs = yield self.script.get_results()
        clip = outputs.get(id, None)
        if clip is None:
            return None
        try:
            frame = yield clip[frame]
        except IndexError:
            return None
        return frame.size(), frame.format()

    @future_yield_coro
    def frame_data(self, id: str, frame: int):
        outputs = yield self.script.get_results()
        clip = outputs.get(id, None)
        if clip is None:
            return None
        try:
            frame = yield clip[frame]
        except IndexError:
            return None
        frame = frame.to_raw()

        from yuuno.multi_scripts.subprocess.process import FRAME_BUFFER_SIZE
        if len(frame) > FRAME_BUFFER_SIZE:
            return frame

        with self.env.framebuffer() as f:
            f[:len(frame)] = frame

        return len(frame)
