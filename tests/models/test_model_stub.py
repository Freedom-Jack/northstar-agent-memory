import pytest

import model_fakes as f
from northstar_agent_memory.models.port import ModelError, ModelPort, ModelResult, Usage
from northstar_agent_memory.models.stub import StubModel, scripted


def test_default_stub_answers_stub():
    stub = StubModel()
    assert isinstance(stub, ModelPort)
    r = stub.complete(f.make_req(family="stub", role="answerer"))
    assert r.text == "stub" and r.cost_usd == 0
    assert r.model == r.served_model == "stub-answerer" and r.family == "stub"
    assert r.usage.input_tokens > 0 and r.usage.output_tokens == 1


def test_dict_reply_becomes_parsed_and_text():
    stub = StubModel(lambda req: {"verdict": "ok"})
    r = stub.complete(f.make_req(family="stub", schema=f.SCHEMA))
    assert r.parsed == {"verdict": "ok"} and '"verdict"' in r.text


def test_string_reply_to_schema_request_is_parsed_or_an_error():
    assert StubModel(lambda req: '{"verdict": "a"}').complete(f.make_req(schema=f.SCHEMA)).parsed == {"verdict": "a"}
    with pytest.raises(ModelError):
        StubModel().complete(f.make_req(schema=f.SCHEMA))


def test_handler_may_return_a_model_result():
    mine = ModelResult("t", None, Usage(), 1.5, 0.0, "stub", "m", "m", "end_turn")
    assert StubModel(lambda req: mine).complete(f.make_req(family="stub")) is mine


def test_scripted_by_purpose_in_order():
    stub = StubModel(scripted({"a": ["one", {"x": 1}], "b": ["bee"]}, default="dflt"))
    got = [stub.complete(f.make_req(purpose=p)).text for p in ("a", "b", "a", "a", "c")]
    assert got[0] == "one" and got[1] == "bee" and '"x"' in got[2] and got[3:] == ["dflt", "dflt"]
    assert len(stub.calls) == 5


def test_scripted_exception_is_raised():
    stub = StubModel(scripted({"a": [ModelError("boom")]}))
    with pytest.raises(ModelError, match="boom"):
        stub.complete(f.make_req(purpose="a"))


def test_schema_aware_handler_answers_any_strict_schema():
    from northstar_agent_memory.eval import baselines as B
    from northstar_agent_memory.models.stub import schema_aware

    stub = StubModel(schema_aware)
    for schema in (B.ANSWER_SCHEMA, B.ACTION_SCHEMA, B.FINAL_SCHEMA, B.OBSERVE_SCHEMA):
        parsed = stub.complete(f.make_req(schema=schema)).parsed
        assert set(schema["required"]) <= set(parsed)
    assert stub.complete(f.make_req()).text == "stub"
