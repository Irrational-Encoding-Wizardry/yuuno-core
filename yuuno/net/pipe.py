from yuuno.net.base import ChildConnection


class SimplexPipe(ChildConnection):

    def __init__(self, src, dst):
        super().__init__(src)
        self.dst = dst

    def receive(self, data: dict, binaries: List[bytes]) -> None:
        self.dst.send(data, binaries)

    def send(self, data: dict, binaries: List[bytes]) -> None:
        pass

    def closed(self) -> None:
        self.dst.shutdown()

    def shutdown(self) -> None:
        pass


class DuplexPipe(object):
    
    def __init__(pipe1, pipe2):
        self.forward = SimplexPipe(pipe1, pipe2)
        self.backward = SimplexPipe(pipe2, pipe1)

        self.pipe1 = pipe1
        self.pipe2 = pipe2

    def shutdown(self):
        self.pipe1.shutdown()
        self.pipe2.shutdown()