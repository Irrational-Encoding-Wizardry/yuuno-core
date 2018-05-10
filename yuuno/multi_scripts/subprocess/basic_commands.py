from pathlib import Path

from yuuno.utils import future_yield_coro
from yuuno.multi_scripts.script import Script


class BasicCommands(object):

    script: Script

    def __init__(self, script: Script):
        self.script = script

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
        print(type(frame))
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
        return frame.to_raw()
