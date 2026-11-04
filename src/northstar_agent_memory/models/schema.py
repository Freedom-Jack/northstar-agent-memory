"""The strict-schema check that both adapters run before a call (DESIGN §1.4; the port's rules).

Each vendor accepts only part of JSON Schema in strict mode, and a schema it rejects
fails on the first live call of a run. `assert_strict` accepts only the part both
take: every object lists all of its properties in "required" and sets
"additionalProperties": false; an optional value is a type union with "null" or an
anyOf with a null branch. OpenAI refuses oneOf and allOf, and Anthropic refuses
numeric, length and count limits (its SDK moves them into descriptions), so those
are refused here too.
"""

from __future__ import annotations

from typing import Any

from northstar_agent_memory.models.port import SchemaNotStrict

KEYWORDS = frozenset(
    {
        "type",
        "properties",
        "required",
        "additionalProperties",
        "items",
        "anyOf",
        "enum",
        "description",
        "title",
        "$defs",
        "$ref",
        "format",
        "minItems",
    }
)
TYPES = frozenset({"object", "array", "string", "integer", "number", "boolean", "null"})
# String formats both vendors accept.
FORMATS = frozenset({"date-time", "time", "date", "duration", "email", "hostname", "ipv4", "ipv6", "uuid"})


def assert_strict(schema: dict) -> None:
    """Raise SchemaNotStrict unless both vendors would accept `schema` in strict mode."""
    if not isinstance(schema, dict) or schema.get("type") != "object":
        raise SchemaNotStrict('schema: the top level must be {"type": "object", ...}')
    _check(schema, "schema")


def _check(node: Any, path: str) -> None:
    if not isinstance(node, dict):
        raise SchemaNotStrict(f"{path}: expected a schema object")
    unknown = sorted(set(node) - KEYWORDS)
    if unknown:
        raise SchemaNotStrict(
            f"{path}: {', '.join(unknown)} not accepted in strict mode by both vendors "
            "(use anyOf for unions, a one-value enum for a constant, and the description for limits)"
        )
    if "$ref" in node:
        ref = node["$ref"]
        if not isinstance(ref, str) or not ref.startswith("#/$defs/"):
            raise SchemaNotStrict(f"{path}: $ref must point into the schema's own $defs")
    elif "type" not in node and "anyOf" not in node:
        raise SchemaNotStrict(f"{path}: needs a type, anyOf or $ref")

    types = _types(node, path)
    if "object" in types or "properties" in node:
        _check_object(node, path)
    if "array" in types:
        if "items" not in node:
            raise SchemaNotStrict(f"{path}: an array needs items")
        if node.get("minItems", 0) not in (0, 1):
            raise SchemaNotStrict(f"{path}: minItems may only be 0 or 1")
    if "items" in node:
        _check(node["items"], f"{path}.items")
    if "format" in node and node["format"] not in FORMATS:
        raise SchemaNotStrict(f"{path}: format {node['format']!r} is not one both vendors accept")
    if "enum" in node:
        enum = node["enum"]
        if not isinstance(enum, list) or not enum:
            raise SchemaNotStrict(f"{path}: enum must be a non-empty list")
        if not all(v is None or isinstance(v, (str, int, float, bool)) for v in enum):
            raise SchemaNotStrict(f"{path}: enum values must be strings, numbers, booleans or null")
    if "anyOf" in node:
        branches = node["anyOf"]
        if not isinstance(branches, list) or not branches:
            raise SchemaNotStrict(f"{path}: anyOf must be a non-empty list")
        for i, branch in enumerate(branches):
            _check(branch, f"{path}.anyOf[{i}]")
    for name, sub in node.get("$defs", {}).items():
        _check(sub, f"{path}.$defs.{name}")


def _types(node: dict, path: str) -> list[str]:
    declared = node.get("type")
    if declared is None:
        return []
    types = [declared] if isinstance(declared, str) else declared
    if not isinstance(types, list) or not types or any(t not in TYPES for t in types):
        raise SchemaNotStrict(f"{path}: type must be one of {sorted(TYPES)} or a list of them")
    return types


def _check_object(node: dict, path: str) -> None:
    if node.get("additionalProperties") is not False:
        raise SchemaNotStrict(f'{path}: an object must set "additionalProperties": false')
    properties = node.get("properties", {})
    if not isinstance(properties, dict):
        raise SchemaNotStrict(f"{path}: properties must be an object")
    required = node.get("required", [])
    missing = [name for name in properties if name not in required]
    if missing:
        raise SchemaNotStrict(
            f"{path}: every property must be required ({', '.join(missing)} missing); "
            'make an optional value a union with "null" instead'
        )
    extra = [name for name in required if name not in properties]
    if extra or len(set(required)) != len(required):
        raise SchemaNotStrict(f"{path}: required lists unknown or repeated names: {', '.join(extra) or required}")
    for name, sub in properties.items():
        _check(sub, f"{path}.properties.{name}")
