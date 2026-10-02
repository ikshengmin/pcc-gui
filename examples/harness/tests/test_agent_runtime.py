import pytest

from agent_runtime import AgentConfig, AgentLoop, PromptRuntime
from model_runtime import (
    DeterministicModelProvider,
    ModelChunk,
    ModelProviderRegistry,
    ModelResult,
)
from session_runtime import Session, SessionHeader
from tool_runtime import ToolRuntime, create_default_tools


def create_agent(provider=None):
    session = Session(SessionHeader("main", 0))
    prompt = PromptRuntime()
    prompt.register("tools", 200, "Use tools when needed.")
    prompt.register("persona", 0, "You are PCC Harness.")
    tools = create_default_tools()
    models = ModelProviderRegistry()
    models.register("local", provider or DeterministicModelProvider())
    agent = AgentLoop(session, prompt, tools, models, AgentConfig("local", "test"))
    return agent


def test_assistant_turn_logs_request_chunks_message_and_lifecycle():
    agent = create_agent()

    response = agent.run_turn("hello")

    assert response == "PCC harness is running. You said: hello"
    types = [event.event_type for event in agent.session.events]
    assert types == [
        "turn/start",
        "user/message",
        "step/start",
        "request/header",
        "assistant/chunk",
        "assistant/message",
        "step/end",
        "turn/end",
    ]
    projection = agent.session.projection()
    assert projection.request_system == "You are PCC Harness.\n\nUse tools when needed."


def test_agent_constructor_declares_concrete_capability_dependencies():
    annotations = AgentLoop.__init__.__annotations__

    assert annotations["session"] is Session
    assert annotations["prompt"] is PromptRuntime
    assert annotations["tools"] is ToolRuntime
    assert annotations["models"] is ModelProviderRegistry
    assert annotations["config"] is AgentConfig


def test_prompt_order_is_stable_without_dynamic_sort_callbacks():
    prompt = PromptRuntime()
    prompt.register("late-a", 10, "A")
    prompt.register("first", 0, "First")
    prompt.register("late-b", 10, "B")

    assert prompt.assemble() == "First\n\nA\n\nB"


def test_tool_turn_runs_second_model_step_and_replays_call_pair():
    agent = create_agent()

    response = agent.run_turn("/tool echo native pcc")

    assert response == "Tool returned: native pcc"
    projection = agent.session.projection()
    assert [(message.role, message.content) for message in projection.messages] == [
        ("user", "/tool echo native pcc"),
        ("assistant-tool-call", ""),
        ("tool", "native pcc"),
        ("assistant", "Tool returned: native pcc"),
    ]
    assert [event.step for event in agent.session.events if event.event_type == "step/start"] == [1, 2]


def test_cancel_before_model_call_closes_turn_as_aborted():
    agent = create_agent()
    agent.cancel()

    assert agent.run_turn("hello") == ""
    assert agent.session.events[-1].reason == "aborted"


class BrokenProvider:
    def complete(self, request):
        raise RuntimeError("provider failed")


def test_provider_failure_closes_step_and_turn_before_propagating():
    agent = create_agent(BrokenProvider())

    with pytest.raises(RuntimeError, match="provider failed"):
        agent.run_turn("hello")

    assert [event.event_type for event in agent.session.events[-2:]] == [
        "step/end",
        "turn/end",
    ]
    assert agent.session.events[-1].reason == "error"


class UsageProvider:
    def complete(self, request):
        return ModelResult(
            "measured",
            [],
            [ModelChunk("text", "measured")],
            input_tokens=7,
            output_tokens=11,
        )


def test_agent_logs_provider_usage_for_replayable_session_stats():
    agent = create_agent(UsageProvider())

    assert agent.run_turn("measure") == "measured"

    messages = [
        event
        for event in agent.session.events
        if event.event_type == "assistant/message"
    ]
    assert len(messages) == 1
    assert messages[0].input_tokens == 7
    assert messages[0].output_tokens == 11
    assert agent.session.projection().session_stats.decode_tokens == 11


def test_provider_tool_turn_round_trips_indexed_calls_and_replayed_reasoning():
    import json
    from model_runtime import DeepSeekSseProvider

    def data(delta, reason=None):
        return "data: " + json.dumps({"choices": [{"delta": delta, "finish_reason": reason}]}) + "\n\n"

    class Transport:
        def __init__(self):
            self.bodies = []
            self.tokens = []
            self.closed = 0

        def post_sse(self, url, headers, body, cancellation):
            self.bodies.append(json.loads(body))
            self.tokens.append(cancellation)
            try:
                if len(self.bodies) == 1:
                    yield data({"reasoning_content": "check both", "content": "Using tools"})
                    yield data({"tool_calls": [
                        {"index": 0, "id": "a", "function": {"name": "echo", "arguments": "A"}},
                        {"index": 1, "id": "b", "function": {"name": "echo", "arguments": "B"}},
                    ]})
                    yield data({"tool_calls": [
                        {"index": 1, "function": {"arguments": "1"}},
                        {"index": 0, "function": {"arguments": "0"}},
                    ]}, "tool_calls")
                else:
                    yield data({"content": "finished"}, "stop")
                yield "data: [DONE]\n\n"
            finally:
                self.closed += 1

    transport = Transport()
    agent = create_agent(DeepSeekSseProvider(transport, "secret", "https://api.deepseek.com"))
    assert agent.run_turn("two tools") == "finished"
    messages = transport.bodies[1]["messages"]
    assert [message["role"] for message in messages] == ["system", "user", "assistant", "tool", "tool"]
    assert messages[2] == {
        "role": "assistant", "content": "Using tools", "reasoning_content": "check both",
        "tool_calls": [
            {"id": "a", "type": "function", "function": {"name": "echo", "arguments": "A0"}},
            {"id": "b", "type": "function", "function": {"name": "echo", "arguments": "B1"}},
        ],
    }
    assert [(message["tool_call_id"], message["content"]) for message in messages[3:]] == [("a", "A0"), ("b", "B1")]
    assert transport.tokens == [agent.cancellation, agent.cancellation]
    assert transport.closed == 2
    # Replay remains the single source of model history, including reasoning.
    restored = Session(agent.session.header, agent.session.events)
    agent.session = restored
    history = agent._model_messages()
    assert history[1].reasoning_content == "check both"
    assert [call.call_id for call in history[1].tool_calls] == ["a", "b"]
    chunks = [event for event in restored.events if event.event_type == "assistant/chunk"]
    assert len(chunks) == 9  # no second append of already published live deltas


def test_stream_cancellation_logs_partial_delta_and_aborts_before_tools():
    from model_runtime import DeepSeekSseProvider

    class Transport:
        def __init__(self):
            self.closed = 0

        def post_sse(self, url, headers, body, cancellation):
            try:
                yield 'data: {"choices":[{"delta":{"content":"partial"}}]}\n\n'
                # The first delta must already be in the log before next read.
                assert agent.session.events[-1].text == "partial"
                cancellation.cancel("user")
                yield 'data: {"choices":[{"delta":{"tool_calls":[{"index":0,"id":"late","function":{"name":"echo","arguments":"never"}}]}}]}\n\n'
            finally:
                self.closed += 1

    transport = Transport()
    agent = create_agent(DeepSeekSseProvider(transport, "secret", "https://api.deepseek.com"))
    assert agent.run_turn("cancel streaming") == ""
    assert agent.session.events[-1].reason == "aborted"
    assert agent.session.active_step == 0 and agent.session.active_turn == 0
    assert not any(event.event_type == "tool/call" for event in agent.session.events)
    assert [event.text for event in agent.session.events if event.event_type == "assistant/chunk"] == ["partial"]
    assert transport.closed == 1


def test_max_token_finish_does_not_execute_truncated_tool_call():
    from model_runtime import ToolCall

    class TruncatedProvider:
        def complete(self, request):
            return ModelResult("partial", [ToolCall("bad", "echo", "incomplete")], [], "length")

    agent = create_agent(TruncatedProvider())
    assert agent.run_turn("truncated") == "partial"
    assert agent.session.events[-1].reason == "max-tokens"
    assert not any(event.event_type == "tool/call" for event in agent.session.events)
    assert agent.session.active_turn == 0 and agent.session.active_step == 0


def test_session_replacement_cancels_old_agent_before_late_model_result():
    from harness_runtime import HarnessRuntime

    runtime = HarnessRuntime()
    old_agent = runtime.agent

    class SwitchProvider:
        def complete(self, request):
            runtime.new_session("new", 1)
            return ModelResult("stale", [], [ModelChunk("text", "stale")])

    runtime.models.register("switch", SwitchProvider())
    runtime.config.provider = "switch"
    assert old_agent.run_turn("old request") == ""
    assert old_agent.session.events[-1].reason == "aborted"
    assert runtime.session.header.session_id == "new"
    assert runtime.session.events == []
    assert not any(event.text == "stale" for event in old_agent.session.events)
    runtime.dispose()
