import pytest

from northstar_agent_memory.models.port import SchemaNotStrict
from northstar_agent_memory.models.schema import assert_strict

GOOD = {
    "type": "object",
    "properties": {
        "answer": {"type": "string"},
        "note": {"type": ["string", "null"]},
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"id": {"type": "integer"}},
                "required": ["id"],
                "additionalProperties": False,
            },
        },
        "kind": {"enum": ["a", "b"], "type": "string"},
        "maybe": {"anyOf": [{"type": "string"}, {"type": "null"}]},
    },
    "required": ["answer", "note", "items", "kind", "maybe"],
    "additionalProperties": False,
}


def test_strict_schema_passes():
    assert_strict(GOOD)


def test_missing_additional_properties():
    bad = {"type": "object", "properties": {"a": {"type": "string"}}, "required": ["a"]}
    with pytest.raises(SchemaNotStrict, match="additionalProperties"):
        assert_strict(bad)


def test_property_not_required():
    bad = {
        "type": "object",
        "properties": {"a": {"type": "string"}, "b": {"type": "string"}},
        "required": ["a"],
        "additionalProperties": False,
    }
    with pytest.raises(SchemaNotStrict, match="b missing"):
        assert_strict(bad)


def test_nested_object_in_items_is_checked():
    bad = {
        "type": "object",
        "properties": {"xs": {"type": "array", "items": {"type": "object", "properties": {"a": {"type": "string"}}, "required": []}}},
        "required": ["xs"],
        "additionalProperties": False,
    }
    with pytest.raises(SchemaNotStrict, match=r"xs\.items"):
        assert_strict(bad)


def test_nested_object_in_anyof_and_defs_is_checked():
    inner = {"type": "object", "properties": {"a": {"type": "string"}}, "required": ["a"]}
    in_anyof = {"type": "object", "properties": {"u": {"anyOf": [inner, {"type": "null"}]}}, "required": ["u"], "additionalProperties": False}
    with pytest.raises(SchemaNotStrict, match="anyOf"):
        assert_strict(in_anyof)
    in_defs = {"type": "object", "properties": {"u": {"$ref": "#/$defs/x"}}, "required": ["u"], "additionalProperties": False, "$defs": {"x": inner}}
    with pytest.raises(SchemaNotStrict, match=r"\$defs"):
        assert_strict(in_defs)


def test_oneof_and_limits_refused():
    for extra in ({"oneOf": [{"type": "string"}]}, {"maximum": 5}, {"minLength": 1}):
        schema = {"type": "object", "properties": {"a": {"type": "integer", **extra}}, "required": ["a"], "additionalProperties": False}
        with pytest.raises(SchemaNotStrict):
            assert_strict(schema)


def test_top_level_must_be_object():
    with pytest.raises(SchemaNotStrict):
        assert_strict({"type": "array", "items": {"type": "string"}})
