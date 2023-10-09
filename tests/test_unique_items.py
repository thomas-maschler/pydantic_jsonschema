from typing import List, Set, get_type_hints

from pydantic import AnyUrl

from pydantic_jsonschema.parser import from_json_schema

json_schema = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "$id": "https://link.to.schema#",
    "title": "Test Schema",
    "type": "object",
    "description": "This is a test schema.",
    "properties": {
        "links": {
            "title": "Item links",
            "description": "Links to item relations",
            "type": "array",
            "items": {"type": "string", "format": "iri"},
        },
        "unique_links": {
            "title": "Item links",
            "description": "Links to item relations",
            "type": "array",
            "items": {"type": "string", "format": "iri"},
            "uniqueItems": True,
        },
    },
}


def test_properties():
    result = from_json_schema(json_schema)
    types = get_type_hints(result)

    assert types == {
        "links": List[AnyUrl],
        "unique_links": Set[AnyUrl],
    }
