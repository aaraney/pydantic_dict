import pytest
from pydantic import ValidationError
from pydantic_dict import BaseModelDict, Unset
from pydantic_dict.base_model_dictionary import _unset_sentinel

from typing import Tuple, Optional
from typing_extensions import TypeAlias

FieldKey: TypeAlias = str
DictKey: TypeAlias = str


class KVModel(BaseModelDict):
    key: str
    unset_key: Optional[str] = Unset


class KVModelWithFieldValidation(KVModel):
    class Config(KVModel.Config):
        validate_assignment = True


class KVModelFrozen(KVModel):
    class Config(KVModel.Config):
        frozen = True


class KVModelIgnoreExtra(KVModel):
    class Config(KVModel.Config):
        extra = "ignore"


class KVModelForbidExtra(KVModel):
    class Config(KVModel.Config):
        extra = "forbid"


DataRetType = Tuple[KVModel, FieldKey, FieldKey, DictKey]


@pytest.fixture
def data() -> DataRetType:
    m = KVModel(key="value")
    m["key2"] = "value2"

    return m, "key", "unset_key", "key2"


@pytest.fixture
def data_with_validate_assignment() -> DataRetType:
    m = KVModelWithFieldValidation(key="value")
    m["key2"] = "value2"

    return m, "key", "unset_key", "key2"


@pytest.fixture
def data_with_frozen_model() -> DataRetType:
    m = KVModelFrozen(key="value", key2="value2")
    return m, "key", "unset_key", "key2"


@pytest.fixture
def data_with_ignore_extras() -> DataRetType:
    m = KVModelIgnoreExtra(key="value", key2="value2")
    return m, "key", "unset_key", "key2"


@pytest.fixture
def data_with_forbid_extras() -> DataRetType:
    m = KVModelForbidExtra(key="value")
    return m, "key", "unset_key", "key2"


def test___contains__(data: DataRetType):
    model, field_key, unset_key, dict_key = data
    assert field_key in model
    assert unset_key not in model
    assert dict_key in model

    m1 = model.copy(deep=True)
    m2 = model.copy(deep=True)

    assert unset_key not in m1
    assert unset_key not in m2

    m1[unset_key] = "value"
    assert unset_key in m1

    m2.unset_key = "value"
    assert unset_key in m2


def test___delitem__(data: DataRetType):
    model, field_key, unset_key, dict_key = data

    del model[dict_key]
    assert dict_key not in model

    assert field_key in model
    # cannot delete field key
    with pytest.raises(KeyError):
        del model[field_key]

    # cannot delete unset field key
    with pytest.raises(KeyError):
        del model[unset_key]


def test___eq__():
    class D(BaseModelDict):
        a: Optional[int] = None

    class D2(BaseModelDict):
        a: Optional[int] = Unset

    m1 = D()
    m2 = D2()
    assert m1 != m2


def test___getattribute__(data: DataRetType):
    model, field_key, unset_key, dict_key = data

    # testing that this does not raise
    getattr(model, field_key)
    getattr(model, unset_key)
    getattr(model, dict_key)


def test___getitem__(data: DataRetType):
    model, field_key, unset_key, dict_key = data

    # testing that this _does_ raise
    with pytest.raises(KeyError):
        model[unset_key]

    # testing that these do not raise
    model[field_key]
    model[dict_key]


def test___hash__():
    class D(BaseModelDict):
        c: Optional[int] = Unset

        class Config(BaseModelDict.Config):
            frozen = True

    m1 = D(a=42, b=42)
    m2 = D.fromkeys(["a", "b"], 42)
    assert hash(m1) == hash(m2)

    m3 = D(a=42, b=42, c=42)
    assert hash(m1) != hash(m3)


def test___iter__(data: DataRetType):
    # test `unset_key` is not included in iter
    model, field_key, unset_key, dict_key = data
    assert set(iter(model)) == {field_key, dict_key}


def test___len__(data: DataRetType):
    model, _, _, _ = data
    assert len(model) == 2
    # test that _unset field is not counted in dictionary length
    assert len(model) != len(model.__dict__)


def test___setattr__(data: DataRetType):
    model, field_key, unset_key, _ = data
    setattr(model, field_key, "new_value")
    setattr(model, unset_key, "new_value")


def test___setitem__(data: DataRetType):
    model, field_key, unset_key, dict_key = data
    model[field_key] = "new_value"
    assert model[field_key] == "new_value"

    model[dict_key] = "new_value"
    assert model[dict_key] == "new_value"

    assert unset_key not in model
    model[unset_key] = "new_value"


def test_clear(data: DataRetType):
    model, field_key, unset_key, dict_key = data
    assert dict_key in model

    # clear does not remove field keys
    model.clear()
    assert field_key in model
    assert unset_key in model.__dict__
    assert unset_key not in model
    assert dict_key not in model


def test_copy(data: DataRetType):
    model, _, unset_key, _ = data
    copy = model.copy()
    assert copy == model
    assert model._unset == copy._unset
    assert model._default_unset == copy._default_unset

    setattr(model, unset_key, "value")
    copy = model.copy()
    assert copy == model
    assert model._unset == copy._unset
    assert model._default_unset == copy._default_unset
    assert model[unset_key] == "value"
    assert copy[unset_key] == "value"


def test_dict():
    model = KVModel(key="value")
    model["key2"] = "value2"
    assert model.dict(exclude_unset=True) == dict(key="value", key2="value2")

    assert model.dict() == dict(key="value", key2="value2", unset_key=_unset_sentinel)


def test_fromkeys():
    model_keys = ["key", "key2"]
    model_value = "value"
    model = KVModel.fromkeys(model_keys, model_value)

    for key in model:
        assert model[key] == model_value

    assert len(model) == 2
    assert len(model.__dict__) != 2


def test_get():
    model = KVModel(key="value", key2="value2")

    # unset key returns default
    assert model.get("unset_key") == None

    # positive cases
    assert model.get("key") == "value"
    assert model.get("key2") == "value2"


def test_items():
    model = KVModel(key="value", key2="value2")

    # collect key, value pairs into dictionary
    collected_model = dict(model.items())

    assert collected_model == dict(key="value", key2="value2")


def test_json(data: DataRetType):
    import json

    model = KVModel(key="value", key2="value2")

    with pytest.raises(TypeError):
        assert model.json() == json.dumps(model.dict())

    assert model.json(exclude_unset=True) == json.dumps(model.dict(exclude_unset=True))


def test_keys():
    model = KVModel(key="value", key2="value2")

    assert set(model.keys()) == {"key", "key2"}

    model.unset_key = "value"
    assert set(model.keys()) == {"key", "key2", "unset_key"}


def test_parse_obj(data: DataRetType):
    model, _, _, _ = data
    assert KVModel.parse_obj(model.dict(exclude_unset=True)) == model


def test_parse_raw(data: DataRetType):
    model, _, _, _ = data

    assert model == KVModel.parse_raw(model.json(exclude_unset=True))


def test_pop(data: DataRetType):
    model, field_key, unset_key, dict_key = data

    # cannot pop a field key
    with pytest.raises(KeyError):
        model.pop(field_key)

    with pytest.raises(KeyError):
        model.pop(unset_key)

    # you can remove a dict_key
    dict_key_value = model[dict_key]
    assert dict_key_value == model.pop(dict_key)
    assert dict_key not in model

    # you should be able to return a non-default value for a non-existent key
    assert False == model.pop("non_existent_key", False)


def test_setdefault(data: DataRetType):
    model, _, unset_key, _ = data

    assert unset_key not in model
    assert model.setdefault(unset_key, "value") == "value"

    model_len = len(model)
    assert model.setdefault("key3", "value3") == "value3"
    assert len(model) == model_len + 1


def test_update(data: DataRetType):
    model, _, _, _ = data

    assert "unset_key" not in model
    more_testing_data = {"unset_key": "value"}
    model.update(more_testing_data)
    assert "unset_key" in model


def test_values(data: DataRetType):
    model = KVModel(key="value1", key2="value2")
    assert list(model.values()) == ["value1", "value2"]

    model.unset_key = "value3"
    assert list(model.values()) == ["value1", "value2", "value3"]


def test_update_with_validate_assignment(data_with_validate_assignment: DataRetType):
    model, model_key, unset_key, _ = data_with_validate_assignment

    pre_op_dict = model.__dict__.copy()
    copy = model.copy()
    deep_copy = model.copy(deep=True)

    # force type validation error, cannot coerce a function type into a str
    # unset_key should remain Unset
    more_testing_data = {unset_key: lambda: 42}
    with pytest.raises(ValidationError):
        model.update(more_testing_data)

    assert model == copy
    assert model == deep_copy
    assert pre_op_dict == model.__dict__


def test_update_unsafe_with_validate_assignment(
    data_with_validate_assignment: DataRetType,
):
    model, _, unset_key, _ = data_with_validate_assignment

    more_testing_data = {unset_key: "value3"}
    model.update_unsafe(more_testing_data)
    assert unset_key in model
    # ensure `unset_key` is removed from set of currently unset fields
    assert unset_key not in model._unset


def test_frozen_model_raises_on_mutation(data_with_frozen_model: DataRetType):
    model, _, unset_key, _ = data_with_frozen_model

    with pytest.raises(TypeError):
        model.pop(unset_key)
    with pytest.raises(TypeError):
        model.setdefault(unset_key, "42")
    with pytest.raises(TypeError):
        setattr(model, unset_key, "42")
    with pytest.raises(TypeError):
        model[unset_key] = "42"

    assert getattr(model, unset_key) == _unset_sentinel


def test_modifying_field_data_with_ignore_extras_enabled(
    data_with_ignore_extras: DataRetType,
):
    model, _, unset_key, _ = data_with_ignore_extras
    model[unset_key] = "value2"
    model.setdefault(unset_key, "value")
    model.update({unset_key: "value2"})


def test_modifying_field_data_with_forbid_extras_enabled(
    data_with_forbid_extras: DataRetType,
):
    model, _, unset_key, _ = data_with_forbid_extras
    model[unset_key] = "value2"
    model.setdefault(unset_key, "value")
    model.update({unset_key: "value2"})
