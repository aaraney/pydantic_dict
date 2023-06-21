from functools import lru_cache
from typing import Any, Type


__SENTINEL = object()


@lru_cache(maxsize=None)
def getclsattr(cls: Type[Any], name: str, __default: Any = __SENTINEL) -> Any:
    super_classes = cls.__mro__
    needles = name.split(".")

    result = __SENTINEL
    for s in super_classes[::-1]:
        intermediate_object = s
        for idx, needle in enumerate(needles):
            intermediate_object = getattr(intermediate_object, needle, __SENTINEL)
            if intermediate_object == __SENTINEL:
                break
            if idx == len(needles) - 1:
                result = intermediate_object

    if result != __SENTINEL:
        return result

    if __default != __SENTINEL:
        return __default

    raise AttributeError(f"{cls.__name__!r} object has no attribute {name!r}")
