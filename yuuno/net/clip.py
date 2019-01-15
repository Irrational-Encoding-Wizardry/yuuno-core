from yuuno.net.handler import RequestReplyClientConnection
from yuuno.net.handler import RequestReplyMethod
from yuuno.net.base import Connection

from yuuno.clip import Clip, Frame, RawFormat
from yuuno.utils import future_yield_coro


class ConnectionFrame(Frame):

    def __init__(self, connclip: 'ConnectionClip'):
        self.connclip = connclip




class ConnectionClip(RequestReplyClientConnection, Clip):
    _length = RequestReplyMethod("length")
    _metadata = RequestReplyMethod("metadata")
    _format = RequestReplyMethod("format")
    _frame = RequestReplyMethod("frame")


    def __init__(self, parent: Connection, length: int):
        RequestReplyClientConnection.__init__(self, parent)
        self.length = length

    def __len__(self) -> int:
        """
        Calculates the length of the clip in frames.

        :return: The amount of frames in the clip
        """
        return self.length

    @future_yield_coro
    def get_metadata(self) -> Future:
        """
        Retrieve meta-data about the clip.
        """
        raw_meta, _ = yield self._metadata({'frame': None}, [])
        return raw_meta

    @future_yield_coro
    def __getitem__(self, item: int) -> Future:
        """
        Extracts the frame from the clip.

        :param item: The frame number
        :return: A frame-instance with the given data.
        """
        format = self._format()
        raise ConnectionFrame()