# pydantic_dict

A `pydantic` model subclass that implements Python's dictionary interface.

**Example:**

```python
from pydantic_dict import BaseModelDict

class User(BaseModelDict):
    id: int
    name: str = "Jane Doe"

user = User(id=42)

user["session_id"] = "95607c42-250a-4913-9dfb-00eb6535e685"
assert user.session_id == "95607c42-250a-4913-9dfb-00eb6535e685"
assert user["session_id"] == "95607c42-250a-4913-9dfb-00eb6535e685"
user.pop("session_id")
assert "session_id" not in user

assert user.get("last_name", None) is None

user.update({"email": "jane.doe@email.com"})
print(user.json())
# >>> {"id": 42, "name": "Jane Doe", "email": "jane.doe@email.com"}

user.clear()  # fields are NOT removed. only non-fields are removed
print(user.json())
# >>> {"id": 42, "name": "Jane Doe"}

user.setdefault("last_active", "2023-01-01T19:56:10Z")
del user["last_active"]
```

**`Unset` marker type**

The `Unset` marker type provides a way to "mark" that an optional model field
is by default not set and is not required to construct the model. This enables
more semantic usage of built-in dict methods like `get()` and `setdefault()`
that can return or set a default value. Likewise, fields that are `Unset` are
not considered to be members of a `BaseModelDict` dictionary (e.g.
`"unset_field" not in model_dict`) and are not included in `__iter__()`,
`keys()`, `values()`, or `len(model_dict)`. This feature is especially useful
when refactoring existing code to use pydantic.

**Example:**


```python
from pydantic_dict import BaseModelDict, Unset
from typing import Optional

class User(BaseModelDict):
    id: int
    name: str = "Jane Doe"
    email: Optional[str] = Unset

user = User(id=42)

assert "email" not in user
user["email"] # raises KeyError

assert len(user) == 2
assert set(user.keys()) == {"id", "name"}

user.setdefault("email", f"{user.id}@service.com") # returns `42@service.com`
assert "email" in user
```

## Install

```shell
pip install pydantic_dict
```
