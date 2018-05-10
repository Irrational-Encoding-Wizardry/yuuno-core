from typing import TYPE_CHECKING
from typing import Optional, Tuple

from PIL.Image import Image, frombytes, merge

from yuuno.clip import Clip, Frame, Size, RawFormat
from yuuno.utils import future_yield_coro, auto_join, inline_resolved

if TYPE_CHECKING:
    from yuuno.multi_scripts.subprocess.process import Subprocess


class ProxyFrame(Frame):

    clip: str
    frameno: int
    script: 'Subprocess'

    _cached_img: Optional[Image]
    _cached_meta: Optional[Tuple[Size, RawFormat]]
    _cached_raw: Optional[bytes]

    def __init__(self, clip: str, frameno: int, script: 'Subprocess'):
        self.clip = clip
        self.frameno = frameno
        self.script = script

        self._cached_img = None
        self._cached_meta = None
        self._cached_raw = None

    @auto_join
    @future_yield_coro
    def _meta(self) -> Tuple[Size, RawFormat]:
        if self._cached_meta is None:
            self._cached_meta = yield self.script.requester.submit('script/subprocess/results/meta', {
                "id": self.clip,
                "frame": self.frameno
            })
        return self._cached_meta

    def size(self) -> Size:
        return self._meta()[0]

    def format(self) -> RawFormat:
        return self._meta()[1]

    @auto_join
    @future_yield_coro
    def to_raw(self) -> bytes:
        if self._cached_raw is None:
            self._cached_raw = yield self.script.requester.submit('script/subprocess/results/raw', {
                "id": self.clip,
                "frame": self.frameno
            })
        return self._cached_raw

    def to_pil(self):
        if self._cached_img is not None:
            return self._cached_img

        format = self.format()
        size = self.size()
        raw = self.to_raw()

        index = 0
        planes = []
        for i in range(format.num_planes):
            plane = self.plane_size(i)
            planedata = raw[index:index+plane]
            planes.append(frombytes('L', size, planedata, 'raw', "L", 0, -1))
            index += plane

        pil_format = "RGB"
        if format.num_planes == 4:
            pil_format += "A"
        return merge(pil_format, planes)


class ProxyClip(Clip):

    script: 'Subprocess'
    length: int

    def __init__(self, clip: str, length: int, script: 'Subprocess'):
        super(ProxyClip, self).__init__(clip)
        self.script = script
        self.length = length

    def __len__(self):
        return self.length

    @inline_resolved
    def __getitem__(self, item):
        if item >= len(self):
            raise IndexError("The clip does not have as many frames.")
        return ProxyFrame(clip=self.clip, frameno=item, script=self.script)
