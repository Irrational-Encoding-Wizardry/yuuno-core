from yuuno.net.base import Connection, ChildConnection
from yuuno.utils import future_yield_coro
from yuuno.clip import Clip, Frame
from yuuno.yuuno import Yuuno


from concurrent.futures import Future
from typing import Callable, List
import traceback


def _raise(exc):
    raise exc


class RequestReplyConnection(ChildConnection):

    @future_yield_coro
    def receive(self, data: dict, binaries: List[bytes]) -> None:
        rqid = data.get('id')
        if rqid is None:
            return

        type = data.get('type')
        if type is None:
            return

        payload = data.get('payload', {})
        
        try:
            func = getattr(self, f'on_{type}', lambda d, b: _raise(ValueError("Unknown function.")))
            res = func(payload, binaries)
            if isinstance(res, Future):
                res, binaries = yield res
            else:
                res, binaries = res

        except Exception as e:
            tb = traceback.print_exception(type(e), e, e.__traceback__)
            tb = ''.join(tb)
            self.send({
                'id': rqid,
                'type': 'failure',
                'payload': {
                    'message': tb
                }
            })

        else:
            self.send({
                'id': rqid,
                'type': 'response',
                'payload': res
            }, binaries)


class ClipHandler(RequestReplyConnection):

    def __init__(self, parent: Connection, clip: Clip, yuuno: Yuuno):
        super().__init__(parent)
        self.clip = clip
        self.yuuno = yuuno

    def on_length(self, data, binaries) -> None:
        return {'length': len(self.clip)}, []

    @future_yield_coro
    def on_metadata(self, data, binaries) -> None:
        frame = data.get('frame', 0)
        if frame > len(self.clip):
            frame = len(self.clip)-1

        frame = yield self.clip[frame]
        return (yield frame.get_metadata()), []

    @future_yield_coro
    def on_format(self, data, binaries) -> None:
        frame = data.get('frame', 0)
        if frame > len(self.clip):
            frame = len(self.clip)-1

        frame = yield self.clip[frame]
        return frame.format(), []

    @future_yield_coro
    def on_frame(self, data, binaries) -> None:
        frame = data.get('frame', 0)
        if frame > len(self.clip):
            frame = len(self.clip)-1

        frame = yield self.clip[frame]
        return {'size': frame.get_size()}, [self.yuuno.output.bytes_of(frame)]