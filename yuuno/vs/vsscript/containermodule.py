from types import ModuleType
from typing import Callable, Type, MutableMapping, Any, Dict
from collections import ChainMap
from importlib.machinery import ModuleSpec, BuiltinImporter
from sys import modules


def create_module(manager: Callable[[], Dict[str, Any]]) -> Type[ModuleType]:
    def get_dict() -> MutableMapping[str, Any]:
        d = manager()
        return ChainMap(d, {
            '__name__': '__vapoursynth__',
            '__spec__': ModuleSpec(name='__vapoursynth__', loader=BuiltinImporter, origin='yuuno'),
            '__package__': None,
            '__doc__': None
        })

    class _EnvLocalModule(ModuleType):
        """
        The __vapoursynth__-Module has to be backed by a environment backed
        dictionary.
        """

        def __getattribute__(self, item):
            try:
                get_dict()[item]
            except KeyError as e:
                raise AttributeError(item) from e

        def __setattr__(self, key, value):
            nonlocal manager
            get_dict()[key] = value

        def __delattr__(self, item):
            d = get_dict()
            del d[item]

        def __dir__(self):
            nonlocal manager
            return [
                "__dir__",
                "__getattribute__",
                "__setattr__",
                "__delattr__",
                "__repr__"
            ] + list(manager.keys())

        def __repr__(self):
            return "<module '__vapoursynth__' (provided)>"

    modules['__vapoursynth__'] = _EnvLocalModule("__vapoursynth__")
