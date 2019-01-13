# -*- encoding: utf-8 -*-

# Yuuno - IPython + VapourSynth
# Copyright (C) 2017-2019 StuxCrystal (Roland Netzsch <stuxcrystal@encode.moe>)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
import ctypes
from functools import wraps
from typing import Tuple, overload
from contextlib import contextmanager
from concurrent.futures import Future

from PIL import Image

import vapoursynth as vs
from vapoursynth import VideoNode, VideoFrame

from yuuno import Yuuno
from yuuno.utils import external_yield_coro, gather, resolve
from yuuno.clip import Clip, Frame, Size, RawFormat, AlphaFrame
from yuuno.vs.extension import VapourSynth
from yuuno.vs.utils import get_proxy_or_core, is_single
from yuuno.vs.flags import Features
from yuuno.vs.alpha import AlphaOutputClip


# On MAC OSX VapourSynth<=R43 is actually returned as XRGB instead of RGBX
COMPAT_PIXEL_FORMAT = "XRGB" if Features.COMPATBGR_IS_XRGB else "BGRX"


def calculate_size(frame: VideoFrame, planeno: int) -> Tuple[int, int]:
    """
    Calculates the size of the plane

    :param frame:    The frame
    :param planeno:  The plane
    :return: (width, height)
    """
    width, height = frame.width, frame.height
    if planeno != 0:
        width >>= frame.format.subsampling_w
        height >>= frame.format.subsampling_h
    return width, height

@overload
def extract_plane_r36compat(frame: VideoFrame, planeno: int, *, compat: bool=False , direction: int = -1, raw=True) -> bytes: pass
@overload
def extract_plane_r36compat(frame: VideoFrame, planeno: int, *, compat: bool=False, direction: int = -1, raw=False) -> Image.Image: pass
def extract_plane_r36compat(frame, planeno, *, compat=False, direction=-1, raw=False):
    """
    Extracts the plane using the old VapourSynth API for reading a frame.

    Since we are doing raw memory operations using ctypes, this function has proven to be prone
    to SIGSEGV while developing.

    This code will subseqently be dropped from this codebase when VapourSynth r36 is officially dropped
    with the official release of R39.

    :param frame:     The frame
    :param planeno:   The plane number
    :param compat:    Are we dealing with a compat format.
    :param direction: -1 bottom to top, 1 top to bottom
    :param raw:       Return bytes instead of an image.
    :return: The extracted image.
    """
    width, height = calculate_size(frame, planeno)
    stride = frame.get_stride(planeno)
    s_plane = height * stride
    buf = (ctypes.c_byte*s_plane).from_address(frame.get_read_ptr(planeno).value)

    if raw:
        return bytes(buf)
    else:
        if not compat:
            return Image.frombuffer('L', (width, height), buf, "raw", "L", stride, direction)
        else:
            return Image.frombuffer('RGB', (width, height), buf, "raw", COMPAT_PIXEL_FORMAT, stride, direction)

@overload
def extract_plane_new(frame: VideoFrame, planeno: int, *, compat: bool=False , direction: int = -1, raw=True) -> bytes: pass
@overload
def extract_plane_new(frame: VideoFrame, planeno: int, *, compat: bool=False, direction: int = -1, raw=False) -> Image.Image: pass
def extract_plane_new(frame, planeno, *, compat=False, direction=-1, raw=False):
    """
    Extracts the plane with the VapourSynth R37+ array-API.

    :param frame:     The frame
    :param planeno:   The plane number
    :param compat:    Are we dealing with a compat format.
    :param direction: -1 bottom to top, 1 top to bottom
    :param raw:       Return bytes instead of an image.
    :return: The extracted image.
    """
    arr = frame.get_read_array(planeno)
    height, width = arr.shape
    stride = frame.format.bytes_per_sample * width

    if raw:
        return bytes(arr)
    else:
        if not compat:
            return Image.frombuffer('L', (width, height), bytes(arr), "raw", "L", stride, direction)
        else:
            return Image.frombuffer('RGB', (width, height), bytes(arr), "raw", COMPAT_PIXEL_FORMAT, stride, direction)


if Features.EXTRACT_VIA_ARRAY:
    extract_plane = extract_plane_new
else:
    extract_plane = extract_plane_r36compat


@contextmanager
def _noop():
    yield

FORMAT_COMPATBGR32 = RawFormat(
    sample_type=RawFormat.SampleType.INTEGER,
    family=RawFormat.ColorFamily.RGB,
    bits_per_sample=8,
    subsampling_h=0,
    subsampling_w=0,
    num_fields=4,
    packed=True,
    planar=False
)
FORMAT_COMPATYUY2 = RawFormat(
    sample_type=RawFormat.SampleType.INTEGER,
    family=RawFormat.ColorFamily.YUV,
    bits_per_sample=8,
    subsampling_h=1,
    subsampling_w=1,
    num_fields=3,
    packed=True,
    planar=False
)


class VapourSynthObject:

    @staticmethod
    def protect(func):
        @wraps(func)
        def _wrapper(self, *args, **kwargs):
            mgr = getattr(self, 'get_environment', _noop)
            with mgr():
                return func(self, *args, **kwargs)
        return _wrapper


class VapourSynthFrame(Frame):

    def __init__(self, single_frame_clip, fobj=None, allow_compat=True):
        if fobj is None:
            fobj = single_frame_clip
            single_frame_clip = None

        self.sfc = single_frame_clip
        self.fobj = fobj
        self._allow_compat = allow_compat
        if self.fobj.format.color_family == vs.COMPAT:
            raise ValueError("Passed a compat-frame even when forbidden.")

        self._format_cache = {}

    @property
    def extension(self) -> VapourSynth:
        return Yuuno.instance().get_extension(VapourSynth)

    def format(self):
        ff: vs.Format = self.fobj.format

        planar = ff.color_family == vs.COMPAT
        if planar:
            if int(ff) == vs.COMPAGBGR32:
                return FORMAT_COMPATBGR32
            else:
                return FORMAT_COMPATYUY2
        else:
            fam = {
                vs.RGB: RawFormat.ColorFamily.RGB,
                vs.GRAY: RawFormat.ColorFamily.GREY,
                vs.YUV: RawFormat.ColorFamily.YUV,
                vs.YCOCG: RawFormat.ColorFamily.YUV
            }[ff.color_family]

        samples = RawFormat.SampleType.INTEGER if ff.sample_type==vs.INTEGER else RawFormat.SampleType.FLOAT
        return RawFormat(
            sample_type=samples,
            family=fam,
            num_fields=ff.num_planes,
            subsampling_w=ff.subsampling_w,
            subsampling_h=ff.subsampling_h,
            bits_per_sample=ff.bits_per_sample,
            packed=False,
            planar=True
        )

    def get_size(self) -> Size:
        return Size(self.fobj.width, self.fobj.height)

    def can_render(self, format: RawFormat) -> bool:
        if format == self.format:
            return True
        elif not format.planar:
            if format == FORMAT_COMPATBGR32:
                return True
            elif format == FORMAT_COMPATYUY2:
                return True
            else:
                return False
        elif format.num_fields in (2, 4):
            return False
        elif format.packed:
            return False
        else:
            return True

    @external_yield_coro
    def render(self, plane: int, format: RawFormat):
        if not self.can_render(format):
            raise ValueError("Cannot convert to format.")

        if not (0 <= plane < format.num_planes):
            raise ValueError("Planeno outside range.")

        if format in self._format_cache:
            return self._format_cache[format]

        mgr = getattr(self, 'get_environment', _noop)()
        with mgr:
            _converted = self._convert(format)
            _frame_fut = _converted.get_frame_async(0)
        frame = yield _frame_fut

        extracted = extract_plane(frame, plane, raw=True)
        self._format_cache[format] = extracted
        return extracted
        
    def _convert_sfc_compat(self, format: RawFormat, resizer):
        if format == FORMAT_COMPATBGR32:
            clip = self._convert_sfc_rgb(8, RawFormat.SampleType.INTEGER, resizer)
            return resizer(clip, format=vs.COMPATBGR32)
        else:
            clip = self._convert_sfc_yuv(8, 1, 1, RawFormat.SampleType.INTEGER, resizer)
            return resizer(clip, format=vs.COMPATYUY2)
    
    def _convert_sfc_rgb(self, bits, family, resizer):
        core = get_proxy_or_core()
        target = core.get_format(vs.RGB24).replace(
            bits_per_sample=bits,
            sample_type = (vs.INTEGER if family==RawFormat.SampleType.INTEGER else vs.FLOAT)
        )
        params = {
            'format': target
        }
        if self.fobj.format != target:
            if self.fobj.format.color_family == vs.YUV:
                params.update(
                    matrix_in_s=self.extension.yuv_matrix,
                    prefer_props=self.extension.prefer_props
                )
            return resizer(
                self.sfc,
                **params
            )
        else:
            return self.sfc

    def _convert_sfc_yuv(self, bits, sw, sh, family, resizer):
        core = get_proxy_or_core()
        target = core.get_format(vs.YUV444P8).replace(
            bits_per_sample=bits,
            subsampling_w=sw,
            subsampling_h=sh,
            sample_type=(vs.INTEGER if family==RawFormat.SampleType.INTEGER else vs.FLOAT)
        )
        params = {'format': target}
        if self.fobj.format != target:
            if self.fobj.format.color_family != vs.YUV:
                params.update(
                    matrix_s=self.extension.yuv_matrix,
                    prefer_props=self.extension.prefer_props
                )
            
            return resizer(
                self.sfc,
                format=target,
                matrix_in_s=self.extension.yuv_matrix,
                matrix_s=self.extension.yuv_matrix,
                prefer_props=self.extension.prefer_props
            )
        else:
            return self.sfc

    def _convert_sfc_grey(self, bits, family, resizer):
        core = get_proxy_or_core()
        target = core.get_format(vs.GRAY8).replace(
            bits_per_sample=bits,
            sample_type = (vs.INTEGER if family==RawFormat.SampleType.INTEGER else vs.FLOAT)
        )
        if self.fobj.format != target:
            return resizer(
                self.sfc,
                format=target,
                matrix_in_s=self.extension.yuv_matrix,
                prefer_props=self.extension.prefer_props
            )
        else:
            return self.sfc

    def _make_sfc(self):
        core = get_proxy_or_core()
        bc = core.std.BlankClip(
            length=1,
            format=self.fobj.format,
            fpsnum=1,
            fpsden=1,
            width=self.fobj.width,
            height=self.fobj.height
        )
        return bc.std.ModifyFrame([bc], lambda n, f: self.fobj.copy())

    def get_metadata(self):
        return resolve({
            k: (v.decode("unicode-escape") if isinstance(v, bytes) else v)
            for k, v in self.fobj.props.items()
        })

    def _convert(self, format):
        if self.sfc is None:
            self.sfc = self._make_sfc()
        resizer = self.extension.resize_filter
        if not format.planar:
            return self._convert_sfc_compat(format, resizer)
        elif format.family == RawFormat.ColorFamily.YUV:
            return self._convert_sfc_yuv(
                format.bits_per_sample,
                format.subsampling_w,
                format.subsampling_h,
                format.sample_type,
                resizer
            )
        elif format.family == RawFormat.ColorFamily.RGB:
            return self._convert_sfc_rgb(
                format.bits_per_sample,
                format.sample_type,
                resizer
            )
        else:
            return self._convert_sfc_grey(
                format.bits_per_sample,
                format.sample_type,
                resizer
            )

class VapourSynthClip(Clip):

    def __init__(self, clip):
        self.clip = clip

    def _get_environment(self):
        mgr = getattr(self, 'get_environment', _noop)()
        return mgr

    def _check_alive(self):
        with self._get_environment():
            if not is_single():
                try:
                    get_proxy_or_core().std.BlankClip(self.clip)
                except vs.Error:
                    raise RuntimeError("Tried to access clip of a dead core.") from None

    def make_frame(self, fcl, fobj, allow_compat=True):
        return VapourSynthFrame(fcl, fobj, allow_compat)

    def __len__(self):
        return len(self.clip)

    @external_yield_coro
    def __getitem__(self, index):
        self._check_alive()

        if not isinstance(self.clip, AlphaOutputClip):
            with self._get_environment():
                fcl = self.clip[index].std.Cache(size=1, fixed=True)
                _fq = fcl.get_frame_async(0)
            # Issue the frame request.
            fobj = yield _fq
            return self.make_frame(fcl, fobj)
        else:
            with self._get_environment():
                main = self.clip[0][index].std.Cache(size=1, fixed=True)
                alpha = self.clip[1][index].std.Cache(size=1, fixed=True)

                f_ff = main.get_frame_async(0)
                f_fa = alpha.get_frame_async(0)

            yield gather([f_ff, f_fa])
            ff, fa = f_ff.result(), f_fa.result()

            return AlphaFrame(
                self.make_frame(main, ff, allow_compat=False),
                self.make_frame(alpha, ff, allow_compat=False)
            )