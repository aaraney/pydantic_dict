from pydantic import BaseModel, Extra, PrivateAttr, ValidationError, Field
from typing import (
    Any,
    ClassVar,
    Dict,
    FrozenSet,
    ItemsView,
    Iterable,
    Iterator,
    KeysView,
    Set,
    Tuple,
    TypeVar,
    ValuesView,
)

from typing_extensions import Self

from functools import wraps
from typing import Callable, Any, TypeVar
from typing_extensions import ParamSpec

from ._utils import getclsattr
from ._sentinel import Sentinel
from .exceptions import UnreachableException

M = TypeVar("M", bound="BaseModelDict")
P = ParamSpec("P")
R = TypeVar("R", covariant=True)

_unset_sentinel = Sentinel()


def _unset_sentinel_singleton():
    return _unset_sentinel


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


Unset: None = Field(default_factory=_unset_sentinel_singleton)


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
    _default_unset: ClassVar[FrozenSet[str]]
    """set of fields on a _subclass_ with default value, `Unset`"""

    _unset: Set[str] = PrivateAttr(default_factory=set)
    """set of fields on an _instance_ that _are_, currently, `Unset`"""

    class Config(BaseModel.Config):
        extra = Extra.allow

    def __init_subclass__(cls) -> None:
        cls._default_unset = frozenset(
            name
            for name, field in cls.__fields__.items()
            if field.default_factory == _unset_sentinel_singleton
        )
        return super().__init_subclass__()

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)

        # filter fields that were set during __init__ by `Unset` by default.
        self._unset = set(
            field
            for field in self._default_unset
            if self.__dict__[field] == _unset_sentinel
        )

    def _field_unset(self, key: str) -> bool:
        return key in self._unset

    def __contains__(self, key: str) -> bool:
        if self._field_unset(key):
            return False

        return key in self.__dict__

    @_raise_type_error_if_immutable
    def __delitem__(self, key: str):
        if key in self.__fields__:
            raise KeyError("Deleting non-extra fields is forbidden.")

        del self.__dict__[key]

    def __getitem__(self, key: str) -> Any:
        if self._field_unset(key):
            raise KeyError(key)
        return self.__dict__[key]

    def __len__(self) -> int:
        return len(self.__dict__) - len(self._unset)

    def __setattr__(self, name: str, value: Any):
        # remove field if now set
        if name in self._unset and value != _unset_sentinel:
            # pop to preserve dictionary ordering. dictionary insertion order if
            # lifo in python >= 3.7
            old_value = self.__dict__.pop(name)
            try:
                # setattr will add field back to dictionary
                super().__setattr__(name, value)
            except Exception as e:
                # if set attr fails for whatever reason, ordering will not be
                # maintained, but the dictionary will be preserved.
                self.__dict__[name] = old_value
                raise e
            self._unset.remove(name)
            return
        super().__setattr__(name, value)

    def __setitem__(self, key: str, value: Any):
        # validation is performed if `Config.validate_assignment` flag on
        setattr(self, key, value)

    def __iter__(self) -> Iterator[str]:
        # filter `Unset` fields
        return set(self.__dict__).difference(self._unset).__iter__()

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
        return {k: v for k, v in self.__dict__.items() if k not in self._unset}.items()

    def keys(self) -> KeysView[str]:
        return {k: None for k in self.__dict__.keys() if k not in self._unset}.keys()

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
        original_unset = self._unset.copy()

        try:
            for key, value in values.items():
                self[key] = value
        except (ValidationError, TypeError) as e:
            # `pydantic.BaseModel.__setattr__` overload embeds __dict__ within __dict__ if set
            # through it's `__setattr__`. use object's __setattr__ to get around this.
            object.__setattr__(self, "__dict__", original_state)
            object.__setattr__(self, "_unset", original_unset)
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
        for field in values:
            if field in self._unset:
                self._unset.remove(field)
        self.__dict__.update(values)

    def values(self) -> ValuesView[Any]:
        return {k: v for k, v in self.__dict__.items() if k not in self._unset}.values()
