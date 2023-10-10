import pytest
from pydantic import ValidationError

from pydantic_jsonschema.parser import from_json_schema

json_schema = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "$id": "https://link.to.schema#",
    "title": "Test Schema",
    "type": "object",
    "description": "This is a test schema.",
    "properties": {
        "value": {"type": "string", "enum": ["nan", "inf", "-inf"]},
    },
}


def test_properties():
    result = from_json_schema(json_schema)

    result(value="inf")
    result(value="-inf")
    result(value="nan")
    with pytest.raises(ValidationError):
        result(value="Not allowed")
