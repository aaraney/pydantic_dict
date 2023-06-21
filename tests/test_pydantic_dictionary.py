import pytest
from pydantic import ValidationError
from pydantic_dict import BaseModelDict
from typing import Tuple
from typing_extensions import TypeAlias

FieldKey: TypeAlias = str
DictKey: TypeAlias = str


class KVModel(BaseModelDict):
    key: str


class KVModelWithFieldValidation(KVModel):
    key: str

    class Config(KVModel.Config):
        validate_assignment = True


class KVModelFrozen(KVModel):
    key: str

    class Config(KVModel.Config):
        frozen = True


class KVModelIgnoreExtra(KVModel):
    key: str

    class Config(KVModel.Config):
        extra = "ignore"


class KVModelForbidExtra(KVModel):
    key: str

    class Config(KVModel.Config):
        extra = "forbid"


DataRetType = Tuple[KVModel, FieldKey, DictKey]


@pytest.fixture
def data() -> DataRetType:
    m = KVModel(key="value")
    m["key2"] = "value2"

    return m, "key", "key2"


@pytest.fixture
def data_with_validate_assignment() -> DataRetType:
    m = KVModelWithFieldValidation(key="value")
    m["key2"] = "value2"

    return m, "key", "key2"


@pytest.fixture
def data_with_frozen_model() -> DataRetType:
    m = KVModelFrozen(key="value", key2="value2")
    return m, "key", "key2"


@pytest.fixture
def data_with_ignore_extras() -> DataRetType:
    m = KVModelIgnoreExtra(key="value", key2="value2")
    return m, "key", "key2"


@pytest.fixture
def data_with_forbid_extras() -> DataRetType:
    m = KVModelForbidExtra(key="value")
    return m, "key", "key2"


def test___contains__(data: DataRetType):
    model, field_key, dict_key = data
    assert field_key in model
    assert dict_key in model


def test___delitem__(data: DataRetType):
    model, field_key, dict_key = data

    del model[dict_key]
    assert dict_key not in model

    assert field_key in model
    # cannot delete field key
    with pytest.raises(KeyError):
        del model[field_key]


def test___eq__():
    class D(BaseModelDict):
        a: int

    class D2(BaseModelDict):
        ...

    m1 = D(a=42)
    m2 = D2()
    m2["a"] = 42
    assert m1 == m2


def test___getattribute__(data: DataRetType):
    model, field_key, dict_key = data

    # testing that this does not raise
    getattr(model, field_key)
    getattr(model, dict_key)


def test___getitem__(data: DataRetType):
    model, field_key, dict_key = data

    # testing that these do not raise
    model[field_key]
    model[dict_key]


def test___hash__():
    class D(BaseModelDict):
        class Config(BaseModelDict.Config):
            frozen = True

    m1 = D(a=42, b=42)
    m2 = D.fromkeys(["a", "b"], 42)
    assert hash(m1) == hash(m2)


def test___iter__(data: DataRetType):
    model, field_key, dict_key = data
    assert set(iter(model)) == {field_key, dict_key}


def test___len__(data: DataRetType):
    model, _, _ = data
    assert len(model) == 2


def test___setattr__(data: DataRetType):
    model, field_key, _ = data
    setattr(model, field_key, "new_value")


def test___setitem__(data: DataRetType):
    model, field_key, dict_key = data
    model[field_key] = "new_value"
    assert model[field_key] == "new_value"

    model[dict_key] = "new_value"
    assert model[dict_key] == "new_value"


def test_clear(data: DataRetType):
    model, field_key, dict_key = data
    assert dict_key in model

    # clear does not remove field keys
    model.clear()
    assert field_key in model
    assert dict_key not in model


def test_copy(data: DataRetType):
    model, _, _ = data
    assert model.copy() == model


def test_dict():
    model = KVModel(key="value")
    model["key2"] = "value2"
    assert model.dict() == dict(key="value", key2="value2")


def test_fromkeys():
    model_keys = ["key", "key2"]
    model_value = "value"
    model = KVModel.fromkeys(model_keys, model_value)

    for key in model:
        assert model[key] == model_value

    assert len(model) == 2


def test_get():
    model = KVModel(key="value", key2="value2")

    # positive cases
    assert model.get("key") == "value"
    assert model.get("key2") == "value2"

    # negative cases
    assert model.get("missing_key") == None


def test_items():
    model = KVModel(key="value", key2="value2")

    # collect key, value pairs into dictionary
    collected_model = dict(model.items())

    assert collected_model == dict(key="value", key2="value2")


def test_json(data: DataRetType):
    import json

    model = KVModel(key="value", key2="value2")

    assert model.json() == json.dumps(model.dict())


def test_keys():
    model = KVModel(key="value", key2="value2")

    assert set(model.keys()) == {"key", "key2"}


def test_parse_obj(data: DataRetType):
    model, _, _ = data
    assert KVModel.parse_obj(model.dict()) == model


def test_parse_raw(data: DataRetType):
    model, _, _ = data

    assert model == KVModel.parse_raw(model.json())


def test_pop(data: DataRetType):
    model, field_key, dict_key = data

    # cannot pop a field key
    with pytest.raises(KeyError):
        model.pop(field_key)

    # you can remove a dict_key
    dict_key_value = model[dict_key]
    assert dict_key_value == model.pop(dict_key)
    assert dict_key not in model

    # you should be able to return a non-default value for a non-existent key
    assert False == model.pop("non_existent_key", False)


def test_popitem(data: DataRetType):
    model, _, dict_key = data

    dict_key_value = model[dict_key]
    assert model.popitem() == (dict_key, dict_key_value)
    assert dict_key not in model

    while len(model) != len(model.__fields__):
        model.popitem()

    # cannot pop model field, value pairs
    with pytest.raises(KeyError):
        model.popitem()


def test_setdefault(data: DataRetType):
    model, _, dict_key = data

    dict_key_value = model[dict_key]
    assert model.setdefault(dict_key) == dict_key_value

    model_len = len(model)
    assert model.setdefault("key3", "value3") == "value3"
    assert len(model) == model_len + 1


def test_update(data: DataRetType):
    model, _, _ = data

    more_testing_data = {"key3": "value3"}
    model.update(more_testing_data)
    assert "key3" in model


def test_values(data: DataRetType):
    model = KVModel(key="value1", key2="value2")
    assert list(model.values()) == ["value1", "value2"]


def test_update_with_validate_assignment(data_with_validate_assignment: DataRetType):
    model, model_key, _ = data_with_validate_assignment

    # force type validation error, cannot coerce a function type into a str
    more_testing_data = {model_key: lambda: 42}
    with pytest.raises(ValidationError):
        model.update(more_testing_data)


def test_update_unsafe_with_validate_assignment(
    data_with_validate_assignment: DataRetType,
):
    model, _, _ = data_with_validate_assignment

    more_testing_data = {"key3": "value3"}
    model.update_unsafe(more_testing_data)
    assert "key3" in model


def test_frozen_model_raises_on_mutation(data_with_frozen_model: DataRetType):
    model, _, dict_key = data_with_frozen_model

    with pytest.raises(TypeError):
        model.popitem()
    with pytest.raises(TypeError):
        model.clear()
    with pytest.raises(TypeError):
        del model[dict_key]
    with pytest.raises(TypeError):
        model.pop(dict_key)
    with pytest.raises(TypeError):
        model.setdefault(dict_key, "42")
    with pytest.raises(TypeError):
        model.update({})
    with pytest.raises(TypeError):
        model.update_unsafe({})
    with pytest.raises(TypeError):
        setattr(model, dict_key, "42")
    with pytest.raises(TypeError):
        model[dict_key] = "42"


def test_modifying_field_data_with_ignore_extras_enabled(
    data_with_ignore_extras: DataRetType,
):
    model, field_key, _ = data_with_ignore_extras
    model[field_key] = "value2"
    model.setdefault(field_key, "value")
    model.update({field_key: "value2"})


def test_modifying_field_data_with_forbid_extras_enabled(
    data_with_forbid_extras: DataRetType,
):
    model, field_key, _ = data_with_forbid_extras
    model[field_key] = "value2"
    model.setdefault(field_key, "value")
    model.update({field_key: "value2"})


def test_raises_when_adding_data_to_non_field_with_ignore_extras_enabled(
    data_with_ignore_extras: DataRetType,
):
    model, _, dict_key = data_with_ignore_extras

    with pytest.raises(ValueError):
        model[dict_key] = "value2"

    with pytest.raises(ValueError):
        model.setdefault(dict_key, "value2")

    with pytest.raises(ValueError):
        model.update({dict_key: "value2"})


def test_raises_when_adding_data_to_non_field_with_forbid_extras_enabled(
    data_with_forbid_extras: DataRetType,
):
    model, _, dict_key = data_with_forbid_extras
    with pytest.raises(ValueError):
        model[dict_key] = "value2"

    with pytest.raises(ValueError):
        model.setdefault(dict_key, "value2")

    with pytest.raises(ValueError):
        model.update({dict_key: "value2"})
