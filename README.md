# Pydantic jsonschema

A library to generate Pydantic Modules from JSONSCHEMA at runtime

```python

from pydantic_jsonschema.parser import from_json_schema

MyModel = from_json_schema("path_to_file.json")

MyModel(**kwags)

```
