import json
from typing import Any, Dict, List, Literal, Optional, Set, Tuple, Type, Union, cast
from urllib.parse import urlparse

import requests
from pydantic import AnyUrl, BaseModel, Field, create_model
from pydantic.fields import FieldInfo
from pydantic_core import PydanticUndefined


def extend_model(
    base_model: Type[BaseModel], extension: Type[BaseModel]
) -> Type[BaseModel]:
    class ExtendedModel(base_model, extension):  # type: ignore
        # TODO: make sure that properties are not overriden but rather conflated.
        pass

    return ExtendedModel


def from_json_schema(
    source: Union[str, Dict[str, Any]],
    predefined_models: Dict[str, Type[BaseModel]] = {},
) -> Union[Type[BaseModel], Type]:
    #########################
    # get json schema as dict
    if isinstance(source, dict) and (ref := source.get("$ref")):
        if ref.startswith("#/definitions/"):
            return predefined_models[ref[14:]]
        else:
            json_schema = _get_schema(ref)
    elif isinstance(source, dict):
        json_schema = source
    else:
        json_schema = _get_schema(source)

    #########################
    # get pre-defined models
    if definitions := json_schema.get("definitions"):
        predefined_models = {
            **predefined_models,
            **_get_definitions(definitions, predefined_models),
        }

    #########################
    # TODO: create model validators based off if/then/else objects
    # we will then need to add them to the new model

    ########################
    # Union types
    if one_of := json_schema.get("oneOf"):
        return _get_one_of(one_of, predefined_models)

    #########################
    # Other union type
    # TODO is this more a validator?
    if any_of := json_schema.get("anyOf"):
        return _get_any_of(any_of, predefined_models)

    #########################
    # Combined models
    if all_of := json_schema.get("allOf"):
        return _get_all_of(all_of, predefined_models)

    #########################
    # generic models

    ptype = json_schema.get("type")
    properties = json_schema.get("properties", {})

    if ptype == "object" or (ptype is None and properties):
        return _model_from_properties(
            properties, predefined_models, json_schema.get("required", None)
        )

    if ptype == "array":
        return _model_from_array(json_schema, predefined_models)

    else:
        return _model_from_generic(json_schema)


def _get_one_of(
    one_of: List[Dict[str, Any]], predefined_models: dict[str, Type[BaseModel]]
) -> Type[
    Union[BaseModel, BaseModel]
]:  # FIXME: is there a better way to declare return type?
    # generate models for all items
    # Create union type of all models
    # return union
    models = [from_json_schema(item, predefined_models) for item in one_of]
    return Union[models[0], *models[1:]]  # type: ignore


def _get_any_of(  # type: ignore
    one_of: List[Dict[str, Any]], predefined_models: dict[str, Type[BaseModel]]
) -> Type[BaseModel]:
    ...


def _get_all_of(
    all_of: List[Dict[str, Any]], predefined_models: Dict[str, Type[BaseModel]]
) -> Type[BaseModel]:
    # generate models for all items
    # merge models into one
    # return merged model
    models = [from_json_schema(item, predefined_models) for item in all_of]

    merged_model = models[0]
    for model in models[1:]:
        merged_model = extend_model(merged_model, model)

    return merged_model


def _model_from_properties(
    properties: Dict[str, Any],
    predefined_models: dict[str, Type[BaseModel]],
    required: Optional[List[str]] = None,
) -> Type[BaseModel]:
    field_definitions: Dict[str, Tuple[Type, FieldInfo]] = {}

    for key, property in properties.items():
        ftype = from_json_schema(property, predefined_models)

        if required is not None and key not in required:
            ftype = Optional[ftype]  # type: ignore
            default_value = property.get("const", None)
        else:
            default_value = property.get("const", PydanticUndefined)

        # TODO add more kwargs
        constrains: Dict[str, Any] = {}
        if ftype in [float, int]:
            constrains = {
                **constrains,
                # "gt": ...,
                # "lt": ...,
                # "ge": ...,
                # "le": ...,
                # "multiple_of": ...,
                # "allow_inf_nan": ...
            }

        if ftype == float:
            constrains = {
                **constrains,
                # "max_digits": ...,
                # "decimal_places": ...
            }

        if ftype == str:
            constrains = {
                **constrains,
                "min_length": property.get("minLength"),
                "max_length": property.get("maxLength"),
                # "pattern": ...
            }

        field_info = Field(
            default_value,
            title=property.get("title"),
            description=property.get("description"),
            **constrains,
        )

        field_definitions[key] = (ftype, field_info)

    return cast(
        Type[BaseModel],
        create_model(  # type: ignore
            "generic",
            __base__=BaseModel,
            __module__=__name__,
            __validators__=None,  # TODO: add validators
            **field_definitions,
        ),
    )


def _model_from_array(
    property: Dict[str, Any], predefined_models: dict[str, Type[BaseModel]]
) -> Type:
    items_type = from_json_schema(property["items"], predefined_models)
    if property.get("uniqueItems"):
        return Set[items_type]  # type: ignore
    else:
        return List[items_type]  # type: ignore


def _model_from_generic(property: Dict[str, Any]) -> Type:
    # TODO make this more complete
    types: Dict[str, Dict[str, Type]] = {
        "string": {"default": str, "iri": AnyUrl, "iri-reference": AnyUrl},
        "number": {"default": float},
    }

    ptype = property["type"]
    if const := property.get("const"):
        if ptype == "string":
            return Literal[f"{const}"]  # type: ignore
        # FIXME: How to dynamically create non string Literals?
        # elif ptype == "number":
        #     return Literal[const]

    sub_type = property.get("format", "default")
    return types[ptype][sub_type]


def _get_definitions(
    definitions: Dict[str, Any], predefined_models: dict[str, Type[BaseModel]]
) -> dict[str, Type[BaseModel]]:
    models = {}
    for key, definition in definitions.items():
        models[key] = from_json_schema(definition, predefined_models)
    return models


def _get_schema(source: str) -> Dict[str, Any]:
    # TODO deal with relative paths (could still be a url)

    href = str(source)
    if _is_url(href):
        rsp = requests.get(href)
        rsp.raise_for_status()
        json_schema = cast(Dict[str, Any], rsp.json())
        return json_schema
    else:
        with open(href) as f:
            href_contents = f.read()
        json_schema = cast(Dict[str, Any], json.loads(href_contents))
        return json_schema


def _is_url(href: str) -> bool:
    url = urlparse(href)
    return bool(url.scheme) and bool(url.netloc)
