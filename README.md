# pydantic_dictionary

A `pydantic` model subclass that implements Python's dictionary interface.

**Example:**

```python
from pydantic_dict import BaseModelDict

class User(BaseModelDict):
    id: int
    name: str = 'Jane Doe'

user = User(id=42)

user["session_id"] = "95607c42-250a-4913-9dfb-00eb6535e685"
assert user.session_id == "95607c42-250a-4913-9dfb-00eb6535e685"
assert user["session_id"] == "95607c42-250a-4913-9dfb-00eb6535e685"
user.pop("session_id")
assert "session_id" not in user

assert user.get("last_name", None) is None

user.update({"email": "jane.doe@email.com"})
print(user.json())

```

## Install

```shell
pip install pydantic_dict
```