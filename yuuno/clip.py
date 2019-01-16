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
import math
from enum import IntEnum
from typing import TypeVar, NamedTuple, Tuple

from yuuno.utils import inline_resolved, future_yield_coro, resolve, Future, gather


T = TypeVar("T")


class Size(NamedTuple):
    width: int
    height: int


class SampleType(IntEnum):
    INTEGER = 0
    FLOAT = 1


class ColorFamily(IntEnum):
    GREY = 0
    RGB = 1
    YUV = 2


class RawFormat(NamedTuple):
    bits_per_sample: int
    num_fields: int
    family: ColorFamily
    sample_type: SampleType
    subsampling_h: int = 0
    subsampling_w: int = 0
    packed: bool = True
    planar: bool = True

    @classmethod
    def from_json(self, data):
        if data[-1] == "v1":
            data = list(data)
            data[2] = ColorFamily(data[2])
            data[3] = SampleType(data[3])
            return RawFormat(*data[:-1])
        raise ValueError("Unsupported format")

    def to_json(self):
        return (*self, "v1")

    @property
    def bytes_per_sample(self) -> int:
        # This is faster than
        # int(ceil(bpp/8))
        # and faster than (l,m=divmod(bpp,8); l+bool(m))
        bpp = self.bits_per_sample
        return (bpp//8)+(bpp%8 != 0)

    @property
    def num_planes(self) -> int:
        if self.planar:
            return self.num_fields
        else:
            return 1

    def get_stride(self, plane: int, size: int) -> int:
        stride = size.width * self.bytes_per_sample
        if not self.packed:
            stride += stride%4
        return stride
    
    def get_plane_size(self, plane: int, size: Size) -> int:
        """
        Calcute the size of the plane in bytes.

        :param plane:  The index of the plane.
        :param size:   The size of the frame (on plane 0)
        """
        w, h = self.size()
        if not planar:
            return self.bytes_per_sample * self.num_fields * w * h

        if 0 < plane < 4:
            w >>= self.subsampling_w
            h >>= self.subsampling_h

        stride = w*self.bytes_per_sample
        if not self.packed:
            stride += stride%4

        return h*stride

RawFormat.SampleType = SampleType
RawFormat.ColorFamily = ColorFamily


GRAY8 = RawFormat(8, 1, RawFormat.ColorFamily.GREY, RawFormat.SampleType.INTEGER)
RGB24 = RawFormat(8, 3, RawFormat.ColorFamily.RGB, RawFormat.SampleType.INTEGER)
RGBA32 = RawFormat(8, 4, RawFormat.ColorFamily.RGB, RawFormat.SampleType.INTEGER)


class Frame(object):
    """
    This class represents a single frame out of a clip.
    """

    def format(self) -> RawFormat:
        """
        Returns the raw-format of the image.
        :return: The raw-format of the image.
        """
        return RGB24

    def get_size(self) -> Size:
        """
        Returns the size of the frame.
        """
        return Size(0, 0)

    def can_render(self, format: RawFormat) -> Future:
        """
        Checks if the frame can be rendered in the given format.
        """
        return resolve(self.format == format)

    def render(self, plane: int, format: RawFormat) -> Future:
        """
        Renders the frame in the given format.
        Note that the frame can always be rendered in the format given by the
        format attribute.
        """
        return resolve(b'')

    def get_metadata(self) -> Future:
        """
        Store meta-data about the frame.
        """
        return resolve({})


class AlphaFrame(Frame):

    def __init__(self, main, alpha):
        self.main = main
        self.alpha = alpha

    def format(self) -> RawFormat:
        """
        Returns the raw-format of the image.
        :return: The raw-format of the image.
        """
        main_format = list(self.main.format())
        main_format[1] += 1
        return RawFormat(*main_format)

    def get_size(self) -> Size:
        """
        Returns the size of the frame.
        """
        return self.main.get_size()

    def can_render(self, format: RawFormat) -> Future:
        """
        Checks if the frame can be rendered in the given format.
        """
        if not format.planar:
            return False

        f = self.main.format()
        if format.num_fields in (1,3):
            return self.main.can_render(format)
        else:
            f = list(format)
            f[1] -= 1
            if not self.main.can_render(RawFormat(*f)):
                return False

            f[1] = 1
            f[2] = ColorFamily.GREY
            if not self.alpha.can_render(RawFormat(*f)):
                return False

            return True

    def render(self, plane: int, format: RawFormat) -> Future:
        """
        Renders the frame in the given format.
        Note that the frame can always be rendered in the format given by the
        format attribute.
        """
        if not self.can_render(format):
            raise ValueError("Unsupported format.")

        if format.num_fields in (1, 3):
            return self.main.render(plane, format)
        elif (format.num_fields == 2 and plane==1) or (format.num_fields==4 and plane==3):
            f = list(format)
            f[1] = 1
            f[2] = ColorFamily.GREY
            return self.alpha.render(0, RawFormat(*f))
        else:
            f = list(format)
            f[1] -= 1
            return self.main.render(plane, RawFormat(*f))

    @future_yield_coro
    def get_metadata(self) -> Future:
        """
        Store meta-data about the frame.
        """
        m, a = self.main.get_metadata(), self.alpha.get_metadata()
        yield gather([m, a])
        a = a.result().copy()
        a.update(m.result())
        return a

    def dispose(self) -> None:
        self.main.dispose()
        self.alpha.dispose()


class Clip(object):
    """
    Encapsulates a clip for the applications.

    Some special functions might require an extended
    interface that is defined in its respective places.

    .. automethod:: __len__
    .. automethod:: __getitem__
    """

    def __init__(self, clip: T) -> None:
        self.clip: T = clip

    def __len__(self) -> int:
        """
        Calculates the length of the clip in frames.

        :return: The amount of frames in the clip
        """
        raise NotImplementedError

    def get_metadata(self) -> Future:
        """
        Retrieve meta-data about the clip.
        """
        return resolve({})

    def __getitem__(self, item: int) -> Future:
        """
        Extracts the frame from the clip.

        :param item: The frame number
        :return: A frame-instance with the given data.
        """
        raise NotImplementedError

    def dispose(self) -> None:
        """
        Disposes the clip after it has been used. This function may be called
        after it has been disposed.

        Leave this empty if unused.
        """

    def __del__(self):
        self.dispose()