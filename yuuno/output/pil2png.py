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

from io import BytesIO

from traitlets import Unicode, CInt, Any
from traitlets.config import Configurable
from PIL.Image import Image, frombytes, merge

from yuuno.clip import Frame, RawFormat, RGB24, RGBA32
from yuuno.utils import future_yield_coro, gather
from yuuno.output.srgb_png import srgb


def _patch2unpacked(format: RawFormat) -> RawFormat:
    f = list(format)
    f[6] = False
    return RawFormat(*f)

SUPPORTED_FORMATS = [
    (RGBA32, "RGBA"),
    (RGB24, "RGB"),
    (_patch2unpacked(RGBA32), "RGBA"),
    (_patch2unpacked(RGB24), "RGB")
]


class YuunoImageOutput(Configurable):
    """
    Defines an output for PNG-files
    """

    ################
    # Settings
    yuuno = Any(help="Reference to the current Yuuno instance.")

    zlib_compression: int = CInt(6, help="0=No compression\n1=Fastest\n9=Slowest", config=True)
    icc_profile: str = Unicode("sRGB", help="Specify the path to an ICC-Profile (Defaults to sRGB).", allow_none=True, config=True)

    @future_yield_coro
    def to_pil(self, im: Frame) -> Image:
        import threading
        planes = []
    
        for raw_format, pil_format in SUPPORTED_FORMATS:
            if im.can_render(raw_format):
                break
        else:
            raise ValueError("Cannot convert frame to RGB")

        for p in range(raw_format.num_planes):
            planes.append(im.render(p, raw_format))

        yield gather(planes)
        planes = [plane.result() for plane in planes]
        
        sz = im.get_size()
        planes = [
            frombytes('L', sz, p, 'raw', 'L', raw_format.get_stride(n, sz), 1)
            for n, p in enumerate(planes)
        ]
        return merge(pil_format, planes)


    def bytes_of(self, im: Frame) -> bytes:
        """
        Converts the frame into a bytes-object containing
        the frame as a PNG-file.

        :param im: the frame to convert.
        :return: A bytes-object containing the image.
        """
        import threading
        if not isinstance(im, Image):
            im = self.to_pil(im).result()
        if im.mode not in ("RGBA", "RGB", "1", "L", "P"):
            im = im.convert("RGB")

        settings = {
            "compress_level": self.zlib_compression,
            "format": "png"
        }
        if self.icc_profile is not None:
            if self.icc_profile != "sRGB":
                with open(self.icc_profile, "rb") as f:
                    settings["icc_profile"] = f.read()
            else:
                settings.update(srgb())

        f = BytesIO()
        im.save(f, **settings)
        return f.getvalue()
