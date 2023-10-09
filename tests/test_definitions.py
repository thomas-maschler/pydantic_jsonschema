from typing import List, Literal, get_type_hints

from pydantic import AnyUrl

from pydantic_jsonschema.parser import from_json_schema

json_schema = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "$id": "https://link.to.schema#",
    "title": "Test Schema",
    "type": "object",
    "description": "This is a test schema.",
    "definitions": {
        "links": {
            "title": "Item links",
            "description": "Links to item relations",
            "type": "array",
            "items": {"type": "string", "format": "iri"},
        }
    },
    "properties": {
        "href": {
            "title": "Link reference",
            "type": "string",
            "format": "iri-reference",
        },
        "title": {
            "title": "A String field",
            "type": "string",
            "minLength": 1,
        },
        "version": {"title": "Version number", "type": "string", "const": "1.0.0"},
        "links": {"$ref": "#/definitions/links"},
        "count": {"title": "A number field", "type": "number"},
    },
}


def test_properties():
    result = from_json_schema(json_schema)
    types = get_type_hints(result)

    assert types == {
        "href": AnyUrl,
        "title": str,
        "version": Literal["1.0.0"],
        "links": List[AnyUrl],
        "count": float,
    }
