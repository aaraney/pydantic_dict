from pydantic import BaseModel, Extra, ValidationError
from typing import (
    Any,
    ClassVar,
    Dict,
    ItemsView,
    Iterable,
    Iterator,
    KeysView,
    Tuple,
    TypeVar,
    ValuesView,
)

from typing_extensions import Self

from functools import wraps
from typing import Callable, Any, TypeVar
from typing_extensions import ParamSpec

from ._utils import getclsattr
from .exceptions import UnreachableException

M = TypeVar("M", bound="BaseModelDict")
P = ParamSpec("P")
R = TypeVar("R", covariant=True)


def _raise_type_error_if_immutable(fn: Callable[P, R]) -> Callable[P, R]:
    @wraps(fn)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        self = args[0]

        disallow_mutation = getclsattr(type(self), "Config.frozen", False) | (
            not getclsattr(type(self), "Config.allow_mutation", True)
        )

        if disallow_mutation:
            raise TypeError(
                f'"{type(self).__name__}" is immutable and does not support item assignment'
            )

        return fn(*args, **kwargs)

    return wrapper


def _raise_value_error_if_extra_fields_not_allowed(m: BaseModel):
    extra = getclsattr(type(m), "Config.extra", None)
    if extra is None:
        raise UnreachableException()
    if extra != Extra.allow:
        raise ValueError(f'"{type(m).__name__}" does not allow extra fields.')


class BaseModelDict(BaseModel):
    """
    A `pydantic.BaseModel` subtype that implements the built-in `dict` interface.
    By default, extra fields are allowed.
    See `pydantic` [model config options `extra`](https://docs.pydantic.dev/latest/usage/model_config/#options)).
    However there are subtle divergent behavioral differences between `BaseModelDict` and the
    built-in `dict` type:

    `BaseModelDict` vs `dict`:
        - `clear()` removes all extra fields; non-extra fields are untouched. As a result, `len()`
        after a `clear()` will not be 0 if the `BaseModelDict` has non-fields.

        - Deleting non-extra fields is a `KeyError`. `del` and `pop()` will always raise
        `KeyError`'s if a non-extra field name is provided.

        - `popitem()` will pop the last inserted extra field; A `KeyError` is raised if the only
        remaining fields are non-extra fields or the `__dict__` is empty.

        - If `Config.validate_assignment` is **on**, non-extra fields are validated. As a results,
        setting via `[]` (`__setitem__`) or `setdefault()` could raise a `pydantic.ValidationError`
        if validation fails.

        - If `Config.validate_assignment` is **on**, `update()` can raise a
        `pydantic.ValidationError`. However, `update()` _guarantees_ if a `pydantic.ValidationError`
        is thrown, `__dict__` will _not_ be left in a partially updated state. Meaning, the
        pre-`update()` state of `__dict__` will be restored. A performance penalty is taken to
        guarantee this. A deep copy of `__dict__` is taken for roll-back purposes. The
        `update_unsafe()` method is provided if you need to avoid this performance penalty. Note,
        `update_unsafe()` operates the same as `update()` when `Config.validate_assignment` if off.
    """

    __SENTINEL: ClassVar[object] = object()

    class Config(BaseModel.Config):
        extra = Extra.allow

    def __contains__(self, key: str) -> bool:
        return key in self.__dict__

    @_raise_type_error_if_immutable
    def __delitem__(self, key: str):
        if key in self.__fields__:
            raise KeyError("Deleting non-extra fields is forbidden.")

        del self.__dict__[key]

    def __getitem__(self, key: str) -> Any:
        return self.__dict__[key]

    def __len__(self) -> int:
        return len(self.__dict__)

    @_raise_type_error_if_immutable
    def __setitem__(self, key: str, value: Any):
        if key in self.__fields__:
            # validation is performed if `Config.validate_assignment` flag on
            setattr(self, key, value)
            return

        _raise_value_error_if_extra_fields_not_allowed(self)

        self.__dict__[key] = value

    def __iter__(self) -> Iterator[str]:
        return self.__dict__.__iter__()

    @_raise_type_error_if_immutable
    def clear(self):
        """Remove all non-extra fields."""
        keys_to_remove = set(self.__dict__).difference(self.__fields__)
        for key in keys_to_remove:
            del self.__dict__[key]

    @classmethod
    def fromkeys(cls, iterable: Iterable[Any], value: Any = None) -> Self:
        return cls(**{k: value for k in iterable})

    def get(self, key: str, default: Any = None) -> Any:
        if key not in self:
            return default
        return self[key]

    def items(self) -> ItemsView[str, Any]:
        return self.__dict__.items()

    def keys(self) -> KeysView[str]:
        return self.__dict__.keys()

    @_raise_type_error_if_immutable
    def pop(self, key: str, default: Any = __SENTINEL) -> Any:
        if key in self.__fields__:
            raise KeyError("Deleting non-extra fields is forbidden.")

        if default == self.__SENTINEL:
            return self.__dict__.pop(key)

        return self.__dict__.pop(key, default)

    @_raise_type_error_if_immutable
    def popitem(self) -> Tuple[str, Any]:
        # SAFETY: Changed in version 3.7: Dictionary order is guaranteed to be insertion order.
        # see: https://docs.python.org/3.7/library/stdtypes.html#dict.values
        for key in self.__dict__:
            if key not in self.__fields__:
                return key, self.__dict__.pop(key)

        raise KeyError(
            "popitem(): dictionary is empty or all items in dictionary are model fields"
        )

    @_raise_type_error_if_immutable
    def setdefault(self, key: str, default: Any = None):
        try:
            return self[key]
        except KeyError:
            _raise_value_error_if_extra_fields_not_allowed(self)
            self[key] = default

        return default

    @_raise_type_error_if_immutable
    def update(self, values: Dict[str, Any]):
        """
        Update the dictionary with the key/value pairs from `values`, overwriting existing keys.

        Note, if `Config.validate_assignment` is **on**, `update()` can raise a
        `pydantic.ValidationError`. However, `update()` _guarantees_ if a `pydantic.ValidationError`
        is thrown, `__dict__` will _not_ be left in a partially updated state. Meaning, the
        pre-`update()` state of `__dict__` will be restored. A performance penalty is taken to
        guarantee this. A deep copy of `__dict__` is taken for roll-back purposes. The
        `update_unsafe()` method is provided if you need to avoid this performance penalty. Note,
        `update_unsafe()` operates the same as `update()` when `Config.validate_assignment` if off.

        Parameters
        ----------
        values : Dict[str, Any]

        Raises
        ------
        ValidationError
            This can only be raised if `Config.validate_assignment` is on.
        """
        # fail fast if extra fields are not allowed and present in `values`
        for key in values:
            if key not in self.__fields__:
                _raise_value_error_if_extra_fields_not_allowed(self)

        validate_assignment = getclsattr(
            type(self), "Config.validate_assignment", False
        )
        # field validation is off. fast branch.
        if not validate_assignment:
            self.update_unsafe(values)
            return

        # field validation is on. It is possible while updating fields that validation fails and
        # `__dict__` is left in a partially updated state. For this reason, `__dict__` must be
        # deep copied.  Then try and update with `values`, if there are exceptions, `__dict__` is
        # replaced with the copy.
        import copy

        original_state = copy.deepcopy(self.__dict__)

        try:
            for key, value in values.items():
                self[key] = value
        except (ValidationError, TypeError) as e:
            # `pydantic.BaseModel.__setattr__` overload embeds __dict__ within __dict__ if set
            # through it's `__setattr__`. use object's __setattr__ to get around this.
            object.__setattr__(self, "__dict__", original_state)
            raise e

    @_raise_type_error_if_immutable
    def update_unsafe(self, values: Dict[str, Any]):
        """
        Update the dictionary with the key/value pairs from `values`, overwriting existing keys even
        if `Config.extra` is `ignore` or `forbid` or `Config.validate_assignment` is True. Field
        validation will not be performed even if `Config.validate_assignment` flag is on. Use
        `update()` if `Config.validate_assignment` is
        **off** -- there is no benefit to using this method.

        Parameters
        ----------
        values : Dict[str, Any]
        """
        self.__dict__.update(values)

    def values(self) -> ValuesView[Any]:
        return self.__dict__.values()
