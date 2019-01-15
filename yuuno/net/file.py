import struct
from yuuno.net.base import Connection


class FileConnection(Connection):

    def __init__(self, fp_r, fp_w):
        super().__init__(self)
        self.fp_r = fp_r
        self.fp_w = fp_w

    def read(self):
        """
        Call this function to read the next frame.
        """
        data = self.fp_r.read(8)
        frame_sz = struct.unpack('>I', data)
        data = self.fp_r.read(frame_sz)
        if len(data) < frame_sz:
            raise IOException("Frame size did not match.")
        self.parse(data)

    def write(self, data: bytes) -> None:
        header = struct.pack(">I", len(data))
        self.fp_w.write(header)
        self.fp_w.write(data)