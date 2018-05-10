from typing import Callable, Mapping, Generic, TypeVar, Iterator

from types import MappingProxyType

K = TypeVar("K")
S = TypeVar("S")
T = TypeVar("T")


class ConvertingMappingProxy(Mapping[K, T], Generic[K, S, T]):
    converter: Callable[[S], T]
    mapping: Mapping[K, S]

    __slots__ = ['converter', 'mapping']

    def __init__(self, mapping: Mapping[K, S], converter: Callable[[S], T]):
        self.mapping = MappingProxyType(mapping)
        self.converter = converter

    def __getitem__(self, item) -> T:
        val: S = super(ConvertingMappingProxy, self).__getitem__(item)
        return self.converter(val)

    def __len__(self):
        return len(self.mapping)

    def __iter__(self) -> Iterator[T]:
        return (self.converter(v) for v in self.mapping)
