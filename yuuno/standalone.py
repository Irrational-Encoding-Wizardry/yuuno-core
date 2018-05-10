from yuuno.yuuno import Yuuno
from yuuno.core.environment import Environment


class StandaloneEnvironment(Environment):
    pass


def init_standalone(*, additional_extensions=()) -> Yuuno:
    y = Yuuno.instance(parent=None)
    y.environment = StandaloneEnvironment()
    y.environment.additional_extensions = lambda: additional_extensions
    y.start()
    return y
