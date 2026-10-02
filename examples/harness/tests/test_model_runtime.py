import json

import pytest

from model_runtime import (
    DeepSeekSseProvider,
    DeterministicModelProvider,
    ModelMessage,
    ModelProviderRegistry,
    ModelRequest,
    SseDecoder,
)


class FakeTransport:
    def __init__(self, chunks):
        self.chunks = chunks
        self.calls = []

    def post_sse(self, url, headers, body, cancellation=None):
        self.calls.append((url, headers, body))
        return self.chunks


def request(messages=None):
    return ModelRequest(
        "deepseek", "deepseek-chat", "system", messages or [], [], 100
    )


def test_provider_registration_is_duplicate_safe_and_reversible():
    registry = ModelProviderRegistry()
    registration = registry.register("local", DeterministicModelProvider())
    with pytest.raises(ValueError, match="already registered"):
        registry.register("local", DeterministicModelProvider())
    registration.dispose()
    with pytest.raises(KeyError, match="not registered"):
        registry.resolve("local")


def test_disposed_provider_registration_cannot_remove_its_replacement():
    registry = ModelProviderRegistry()
    provider = DeterministicModelProvider()
    old_registration = registry.register("local", provider)
    registry.unregister("local")
    replacement = registry.register("local", provider)

    old_registration.dispose()
    old_registration.dispose()

    assert registry.resolve("local") is provider
    assert old_registration.active is False
    assert replacement.active is True
    replacement.dispose()
    with pytest.raises(KeyError, match="not registered"):
        registry.resolve("local")


def test_sse_decoder_handles_arbitrary_chunk_boundaries_and_multiline_data():
    decoder = SseDecoder()
    assert decoder.feed("data: one\ndata:") == []
    assert decoder.feed(" two\n\n") == ["one\ntwo"]
    assert decoder.feed("data: final") == []
    assert decoder.finish() == ["final"]


def test_sse_decoder_does_not_split_multiline_event_at_fragmented_crlf():
    decoder = SseDecoder()
    assert decoder.feed("data: one\r") == []
    assert decoder.feed("") == []
    assert decoder.feed("\ndata: two\r\n\r\n") == ["one\ntwo"]
    assert decoder.finish() == []


@pytest.mark.parametrize("newline", ["\n", "\r", "\r\n"])
def test_sse_decoder_preserves_events_at_every_transport_split(newline):
    stream = newline.join(
        [": keepalive", "data: one", "data: two", "", "data: final", "", ""]
    )
    for split in range(len(stream) + 1):
        decoder = SseDecoder()
        payloads = decoder.feed(stream[:split])
        payloads += decoder.feed("")
        payloads += decoder.feed(stream[split:])
        payloads += decoder.finish()
        assert payloads == ["one\ntwo", "final"], split

    decoder = SseDecoder()
    payloads = []
    for character in stream:
        payloads += decoder.feed(character)
    assert payloads + decoder.finish() == ["one\ntwo", "final"]


@pytest.mark.parametrize("ending", ["", "\n", "\r", "\r\n"])
def test_sse_decoder_final_flush_is_once_only(ending):
    decoder = SseDecoder()
    assert decoder.feed("data: final" + ending) == []
    assert decoder.finish() == ["final"]
    assert decoder.finish() == []


def test_deepseek_provider_accepts_fragmented_multiline_json_event():
    stream = (
        'data: {"choices":\r\n'
        'data: [{"delta":{"content":"hello"}}]}\r\n\r\n'
        "data: [DONE]\r\n\r\n"
    )
    for split in range(len(stream) + 1):
        provider = DeepSeekSseProvider(
            FakeTransport([stream[:split], "", stream[split:]]),
            "secret",
            "https://api.deepseek.com",
        )
        assert provider.complete(request()).text == "hello", split


def test_deepseek_provider_rejects_invalid_json_at_fragmented_eof():
    provider = DeepSeekSseProvider(
        FakeTransport(['data: {"choices":\r', "\n"]),
        "secret",
        "https://api.deepseek.com",
    )
    with pytest.raises(ValueError, match="invalid DeepSeek SSE JSON"):
        provider.complete(request())


def test_deepseek_provider_assembles_text_stream_and_request():
    transport = FakeTransport(
        [
            'data: {"choices":[{"delta":{"content":"hel"}}]}\n\n',
            'data: {"choices":[{"delta":{"content":"lo"}}]}\n\n',
            "data: [DONE]\n\n",
        ]
    )
    provider = DeepSeekSseProvider(transport, "secret", "https://api.deepseek.com/")

    result = provider.complete(request([ModelMessage("user", "say hello")]))

    assert result.text == "hello"
    assert [chunk.text for chunk in result.chunks] == ["hel", "lo"]
    url, headers, body = transport.calls[0]
    assert url == "https://api.deepseek.com/chat/completions"
    assert ["authorization", "Bearer secret"] in headers
    decoded = json.loads(body)
    assert decoded["model"] == "deepseek-chat"
    assert decoded["stream"] is True
    assert decoded["messages"][-1] == {"role": "user", "content": "say hello"}


def test_deepseek_provider_preserves_usage_from_choice_less_final_payload():
    transport = FakeTransport(
        [
            'data: {"choices":[{"delta":{"content":"answer"}}]}\n\n',
            'data: {"choices":[],"usage":{"prompt_tokens":7,"completion_tokens":11}}\n\n',
            "data: [DONE]\n\n",
        ]
    )
    provider = DeepSeekSseProvider(transport, "secret", "https://api.deepseek.com")

    result = provider.complete(request())

    assert result.text == "answer"
    assert result.input_tokens == 7
    assert result.output_tokens == 11
    assert [chunk.kind for chunk in result.chunks] == ["text", "usage"]


def test_deepseek_provider_merges_streamed_tool_call_deltas():
    transport = FakeTransport(
        [
            'data: {"choices":[{"delta":{"tool_calls":[{"id":"call-7","function":{"name":"ec","arguments":"nat"}}]}}]}\n\n',
            'data: {"choices":[{"delta":{"tool_calls":[{"function":{"name":"ho","arguments":"ive"}}]}}]}\n\n',
            "data: [DONE]\n\n",
        ]
    )
    provider = DeepSeekSseProvider(transport, "secret", "https://api.deepseek.com")

    result = provider.complete(request([ModelMessage("user", "use tool")]))

    assert result.stop_reason == "tool_calls"
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].call_id == "call-7"
    assert result.tool_calls[0].name == "echo"
    assert result.tool_calls[0].arguments == "native"


def test_invalid_sse_json_fails_loudly():
    provider = DeepSeekSseProvider(
        FakeTransport(["data: not-json\n\n"]),
        "secret",
        "https://api.deepseek.com",
    )
    with pytest.raises(ValueError, match="invalid DeepSeek SSE JSON"):
        provider.complete(request())


def wire_event(delta=None, finish_reason=None, **extra):
    record = {"choices": [{"index": 0, "delta": delta or {}, "finish_reason": finish_reason}]}
    record.update(extra)
    return "data: " + json.dumps(record) + "\n\n"


def call_delta(index, call_id="", name="", arguments=""):
    return {"index": index, "id": call_id, "type": "function", "function": {"name": name, "arguments": arguments}}


def test_interleaved_tool_indices_keep_each_call_identity_at_every_split():
    stream = (
        wire_event({"tool_calls": [call_delta(1, "b", "ec", "B"), call_delta(0, "a", "ec", "A")]})
        + wire_event({"tool_calls": [call_delta(0, name="ho", arguments="0"), call_delta(1, name="ho", arguments="1")]})
        + wire_event(finish_reason="tool_calls")
        + "data: [DONE]\n\n"
    )
    for split in range(len(stream) + 1):
        provider = DeepSeekSseProvider(FakeTransport([stream[:split], stream[split:]]), "secret", "https://api.deepseek.com")
        result = provider.complete(request())
        assert [(call.call_id, call.name, call.arguments, call.index) for call in result.tool_calls] == [
            ("b", "echo", "B1", 1), ("a", "echo", "A0", 0)
        ]
        assert [chunk.tool_index for chunk in result.chunks if chunk.kind == "tool-call-delta"] == [1, 0, 0, 1]


def test_assistant_tool_request_round_trips_arguments_and_reasoning():
    from model_runtime import ToolCall, encode_request

    message = ModelMessage("assistant", "I'll check", tool_calls=[ToolCall("a", "echo", '{"text":"hello"}')], reasoning_content="compare")
    body = json.loads(encode_request(request([message, ModelMessage("tool", "hello", "a", "echo")])))
    assert body["messages"][1] == {
        "role": "assistant", "content": "I'll check", "reasoning_content": "compare",
        "tool_calls": [{"id": "a", "type": "function", "function": {"name": "echo", "arguments": '{"text":"hello"}'}}],
    }
    assert body["messages"][2]["tool_call_id"] == "a"
    assert body["stream_options"] == {"include_usage": True}
    singleton = json.loads(encode_request(request([ModelMessage("assistant", "", "b", "echo", "{}")])))
    assert singleton["messages"][1]["tool_calls"][0]["id"] == "b"
    assert "tool_call_id" not in singleton["messages"][1]


@pytest.mark.parametrize("index", [True, "0", -1, -2, None, 0.5])
def test_provider_rejects_non_integer_or_negative_wire_indices(index):
    stream = wire_event({"tool_calls": [call_delta(index, "a", "echo", "{}")]}) + "data: [DONE]\n\n"
    provider = DeepSeekSseProvider(FakeTransport([stream]), "secret", "https://api.deepseek.com")
    with pytest.raises(ValueError, match="tool-call index"):
        provider.complete(request())


@pytest.mark.parametrize("second", [call_delta(0, "b", arguments="x"), call_delta(1, "a", arguments="x")])
def test_provider_rejects_changed_tool_identity(second):
    stream = wire_event({"tool_calls": [call_delta(0, "a", "echo", "{}")]}) + wire_event({"tool_calls": [second]}) + "data: [DONE]\n\n"
    with pytest.raises(ValueError, match="changed"):
        DeepSeekSseProvider(FakeTransport([stream]), "secret", "https://api.deepseek.com").complete(request())


def test_provider_rejects_ambiguous_unindexed_continuation():
    stream = wire_event({"tool_calls": [call_delta(0, "a", "echo", "A"), call_delta(1, "b", "echo", "B")]})
    stream += wire_event({"tool_calls": [{"function": {"arguments": "bad"}}]}) + "data: [DONE]\n\n"
    with pytest.raises(ValueError, match="ambiguous"):
        DeepSeekSseProvider(FakeTransport([stream]), "secret", "https://api.deepseek.com").complete(request())


class OwnedStreamingTransport:
    def __init__(self, pieces, cancel_at=-1):
        self.pieces = pieces
        self.cancel_at = cancel_at
        self.reads = 0
        self.closed = 0
        self.cancellation = None

    def post_sse(self, url, headers, body, cancellation):
        self.cancellation = cancellation
        try:
            for piece in self.pieces:
                if self.reads == self.cancel_at:
                    cancellation.cancel("stream cancelled")
                self.reads += 1
                yield piece
        finally:
            self.closed += 1


def test_stream_iterator_stops_at_done_and_closes_without_reading_late_data():
    transport = OwnedStreamingTransport([wire_event({"content": "ok"}) + "data: [DONE]\n\n", "data: bad\n\n"])
    result = DeepSeekSseProvider(transport, "secret", "https://api.deepseek.com").complete(request())
    assert result.text == "ok"
    assert transport.reads == 1
    assert transport.closed == 1


@pytest.mark.parametrize("pieces,match", [
    ([wire_event({"content": "partial"})], "before \\[DONE\\]"),
    (["data: []\n\n"], "record"),
    (["data: {\"error\":{\"message\":\"secret must not leak\"}}\n\n"], "provider error"),
    (["data: not-json\n\n"], "JSON"),
    (["data: [DONE]\n\n"], "empty"),
])
def test_failed_stream_closes_and_never_returns_partial_success(pieces, match):
    transport = OwnedStreamingTransport(pieces)
    with pytest.raises(ValueError, match=match) as error:
        DeepSeekSseProvider(transport, "secret", "https://api.deepseek.com").complete(request())
    assert "secret must not leak" not in str(error.value)
    assert transport.closed == 1


def test_stream_cancellation_reaches_transport_and_closes_response():
    from tool_runtime import Cancellation, OperationCancelled

    cancellation = Cancellation()
    value = request()
    value.cancellation = cancellation
    transport = OwnedStreamingTransport([wire_event({"content": "part"}), "data: [DONE]\n\n"], cancel_at=1)
    with pytest.raises(OperationCancelled, match="stream cancelled"):
        DeepSeekSseProvider(transport, "secret", "https://api.deepseek.com").complete(value)
    assert transport.cancellation is cancellation
    assert transport.closed == 1


def test_cancelled_request_never_opens_transport():
    from tool_runtime import Cancellation, OperationCancelled

    transport = FakeTransport([])
    value = request()
    value.cancellation = Cancellation()
    value.cancellation.cancel("already closed")
    with pytest.raises(OperationCancelled):
        DeepSeekSseProvider(transport, "secret", "https://api.deepseek.com").complete(value)
    assert transport.calls == []


def test_finish_reason_and_trailing_usage_are_preserved():
    stream = wire_event({"reasoning_content": "think", "content": "partial"}, "length")
    stream += 'data: {"choices":[],"usage":{"prompt_tokens":8,"completion_tokens":9}}\n\n'
    stream += "data: [DONE]\n\n"
    result = DeepSeekSseProvider(FakeTransport([stream]), "secret", "https://api.deepseek.com").complete(request())
    assert (result.stop_reason, result.reasoning_content, result.input_tokens, result.output_tokens) == ("length", "think", 8, 9)


def test_stop_finish_cannot_authorize_pending_tool_calls():
    stream = wire_event({"tool_calls": [call_delta(0, "a", "echo", "{}") ]}, "stop") + "data: [DONE]\n\n"
    with pytest.raises(ValueError, match="tool-call finish"):
        DeepSeekSseProvider(FakeTransport([stream]), "secret", "https://api.deepseek.com").complete(request())
