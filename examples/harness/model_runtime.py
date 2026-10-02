"""Model provider registry, deterministic provider, and DeepSeek SSE adapter."""

import json


class ModelMessage:
    """Provider-neutral model message."""

    def __init__(
        self,
        role: str,
        content: str,
        call_id: str = "",
        name: str = "",
        arguments: str = "",
        tool_calls=None,
        reasoning_content: str = "",
    ) -> None:
        self.role = role
        self.content = content
        self.call_id = call_id
        self.name = name
        self.arguments = arguments
        self.tool_calls = [] if tool_calls is None else tool_calls
        self.reasoning_content = reasoning_content


class ModelRequest:
    """One resolved provider request."""

    def __init__(
        self,
        provider: str,
        model: str,
        system: str,
        messages,
        tools,
        max_tokens: int = 4096,
        temperature: float = 0.0,
        cancellation=None,
        on_chunk=None,
    ) -> None:
        if provider == "":
            raise ValueError("model provider must not be empty")
        if model == "":
            raise ValueError("model id must not be empty")
        if max_tokens <= 0:
            raise ValueError("max_tokens must be positive")
        self.provider = provider
        self.model = model
        self.system = system
        self.messages = messages
        self.tools = tools
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.cancellation = cancellation
        self.on_chunk = on_chunk
        self.published_chunks = 0

    def publish_chunk(self, chunk) -> None:
        """Deliver one accepted stream delta to the request's session owner."""
        if self.cancellation is not None:
            self.cancellation.require_active()
        if self.on_chunk is not None:
            self.on_chunk(chunk)
            self.published_chunks += 1


class ToolCall:
    """One complete model-requested tool call."""

    def __init__(self, call_id: str, name: str, arguments: str, index: int = -1) -> None:
        self.call_id = call_id
        self.name = name
        self.arguments = arguments
        self.index = index


class ModelChunk:
    """One replayable streamed model delta."""

    def __init__(
        self,
        kind: str,
        text: str = "",
        call_id: str = "",
        name: str = "",
        arguments: str = "",
        input_tokens: int = -1,
        output_tokens: int = -1,
        tool_index: int = -1,
    ) -> None:
        self.kind = kind
        self.text = text
        self.call_id = call_id
        self.name = name
        self.arguments = arguments
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.tool_index = tool_index


class ModelResult:
    """Assembled result and its original stream chunks."""

    def __init__(
        self,
        text: str,
        tool_calls,
        chunks,
        stop_reason: str = "stop",
        input_tokens: int = -1,
        output_tokens: int = -1,
        reasoning_content: str = "",
    ) -> None:
        if input_tokens < -1 or output_tokens < -1:
            raise ValueError("model token usage must be non-negative or absent")
        self.text = text
        self.tool_calls = tool_calls
        self.chunks = chunks
        self.stop_reason = stop_reason
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.reasoning_content = reasoning_content


class ProviderRegistration:
    """Idempotent provider disposer."""

    def __init__(self, registry, name: str, registration_id: int) -> None:
        self.registry = registry
        self.name = name
        self.registration_id = registration_id
        self.active = True

    def dispose(self) -> None:
        if not self.active:
            return
        self.active = False
        self.registry._unregister_registration(self.name, self.registration_id)


class ModelProviderRegistry:
    """Validated registry of model transport providers."""

    def __init__(self) -> None:
        self.names = []
        self.providers = []
        self.registration_ids = []
        self.next_registration_id = 1

    def register(self, name: str, provider) -> ProviderRegistration:
        if name == "":
            raise ValueError("provider name must not be empty")
        if self.index_of(name) >= 0:
            raise ValueError("model provider already registered: " + name)
        registration_id = self.next_registration_id
        self.next_registration_id += 1
        registration = ProviderRegistration(self, name, registration_id)
        self.names.append(name)
        self.providers.append(provider)
        self.registration_ids.append(registration_id)
        return registration

    def unregister(self, name: str) -> None:
        index = self.index_of(name)
        if index < 0:
            return
        self.registration_ids.pop(index)
        self.names.pop(index)
        self.providers.pop(index)

    def _unregister_registration(self, name: str, registration_id: int) -> None:
        index = self.index_of(name)
        if index >= 0 and self.registration_ids[index] == registration_id:
            self.unregister(name)

    def resolve(self, name: str):
        index = self.index_of(name)
        if index < 0:
            raise KeyError("model provider is not registered: " + name)
        return self.providers[index]

    def complete(self, request: ModelRequest) -> ModelResult:
        return self.resolve(request.provider).complete(request)

    def index_of(self, name: str) -> int:
        i = 0
        while i < len(self.names):
            if self.names[i] == name:
                return i
            i += 1
        return -1


class DeterministicModelProvider:
    """Keyless provider for native tests, snapshots, and offline startup."""

    def complete(self, request: ModelRequest) -> ModelResult:
        if len(request.messages) == 0:
            return text_result("PCC Harness is ready.")
        last = request.messages[len(request.messages) - 1]
        if last.role == "tool":
            return text_result("Tool returned: " + last.content)
        prompt = last.content
        if prompt.startswith("/tool echo "):
            call = ToolCall("call-1", "echo", prompt[11:])
            chunk = ModelChunk(
                "tool-call", "", call.call_id, call.name, call.arguments
            )
            return ModelResult("", [call], [chunk], "tool_calls")
        if prompt == "/about":
            return text_result(
                "PCC-native DeepSeek Harness; session format 0"
            )
        return text_result("PCC harness is running. You said: " + prompt)


class DeepSeekSseProvider:
    """DeepSeek-compatible streaming provider over a PCC-owned HTTP transport.

    The injected transport owns DNS, TLS, proxying, pooling, cancellation, and
    virtual-thread I/O. ``post_sse(url, headers, body, cancellation)`` returns
    an iterable of arbitrary text chunks. A closeable iterable is closed on
    success, cancellation and error; no complete response list is required.
    This provider owns request JSON and SSE response parsing.
    """

    def __init__(self, transport, api_key: str, base_url: str) -> None:
        if api_key == "":
            raise ValueError("DeepSeek credential reference resolved empty")
        if base_url == "":
            raise ValueError("DeepSeek base URL must not be empty")
        self.transport = transport
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def complete(self, request: ModelRequest) -> ModelResult:
        if request.cancellation is not None:
            request.cancellation.require_active()
        body = encode_request(request)
        headers = [
            ["authorization", "Bearer " + self.api_key],
            ["content-type", "application/json"],
            ["accept", "text/event-stream"],
        ]
        pieces = self.transport.post_sse(
            self.base_url + "/chat/completions", headers, body, request.cancellation
        )
        decoder = SseDecoder()
        chunks = []
        done = False
        published = 0
        try:
            for piece in pieces:
                if request.cancellation is not None:
                    request.cancellation.require_active()
                if not isinstance(piece, str):
                    raise ValueError("DeepSeek transport must yield decoded text")
                done = append_payload_chunks(decoder.feed(piece), chunks)
                while published < len(chunks):
                    request.publish_chunk(chunks[published])
                    published += 1
                if done:
                    break
            if request.cancellation is not None:
                request.cancellation.require_active()
            if not done:
                done = append_payload_chunks(decoder.finish(), chunks)
                while published < len(chunks):
                    request.publish_chunk(chunks[published])
                    published += 1
            if not done:
                raise ValueError("DeepSeek SSE stream ended before [DONE]")
        finally:
            close = getattr(pieces, "close", None)
            if close is not None:
                close()
        return assemble_chunks(chunks)


class SseDecoder:
    """Incremental SSE decoder tolerant of transport chunk boundaries."""

    def __init__(self) -> None:
        self.buffer = ""
        self.data_lines = []
        self.skip_lf = False

    def feed(self, text: str):
        if text == "":
            return []
        # CR is already a line ending. Suppress its optional LF even when the
        # transport delivers it in the next non-empty chunk.
        if self.skip_lf and text.startswith("\n"):
            text = text[1:]
        self.skip_lf = text.endswith("\r")
        self.buffer += text.replace("\r\n", "\n").replace("\r", "\n")
        payloads = []
        while True:
            index = self.buffer.find("\n")
            if index < 0:
                return payloads
            line = self.buffer[:index]
            self.buffer = self.buffer[index + 1 :]
            self._accept_line(line, payloads)

    def finish(self):
        """Flush the final payload once, including an unterminated final line."""
        payloads = []
        if self.buffer != "":
            self._accept_line(self.buffer, payloads)
            self.buffer = ""
        self._flush(payloads)
        self.skip_lf = False
        return payloads

    def _accept_line(self, line: str, payloads) -> None:
        if line == "":
            self._flush(payloads)
        elif line.startswith("data:"):
            data = line[5:]
            if data.startswith(" "):
                data = data[1:]
            self.data_lines.append(data)

    def _flush(self, payloads) -> None:
        if len(self.data_lines) == 0:
            return
        payloads.append("\n".join(self.data_lines))
        self.data_lines = []


def encode_request(request: ModelRequest) -> str:
    messages = []
    if request.system != "":
        messages.append({"role": "system", "content": request.system})
    i = 0
    while i < len(request.messages):
        message = request.messages[i]
        record = {"role": message.role, "content": message.content}
        if message.role == "assistant":
            calls = message.tool_calls
            if message.call_id != "":
                if len(calls) > 0:
                    raise ValueError("assistant message has two tool-call owners")
                calls = [ToolCall(message.call_id, message.name, message.arguments)]
            if len(calls) > 0:
                wire_calls = []
                for call in calls:
                    if call.call_id == "" or call.name == "":
                        raise ValueError("assistant tool call requires id and name")
                    wire_calls.append({
                        "id": call.call_id,
                        "type": "function",
                        "function": {"name": call.name, "arguments": call.arguments},
                    })
                record["tool_calls"] = wire_calls
                if message.reasoning_content != "":
                    record["reasoning_content"] = message.reasoning_content
        elif message.role == "tool":
            if message.call_id == "":
                raise ValueError("tool result requires tool_call_id")
            record["tool_call_id"] = message.call_id
        if message.name != "" and message.role != "assistant":
            record["name"] = message.name
        messages.append(record)
        i += 1
    tools = []
    i = 0
    while i < len(request.tools):
        tool = request.tools[i]
        tools.append(
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                },
            }
        )
        i += 1
    body = {
        "model": request.model,
        "messages": messages,
        "stream": True,
        "stream_options": {"include_usage": True},
        "max_tokens": request.max_tokens,
        "temperature": request.temperature,
    }
    if len(tools) > 0:
        body["tools"] = tools
    return json.dumps(body, ensure_ascii=False, separators=(",", ":"))


def append_payload_chunks(payloads, chunks) -> bool:
    i = 0
    while i < len(payloads):
        payload = payloads[i]
        if payload == "[DONE]":
            return True
        decode_deepseek_payload(payload, chunks)
        i += 1
    return False


def decode_deepseek_payload(payload: str, chunks) -> None:
    try:
        record = json.loads(payload)
    except json.JSONDecodeError as error:
        raise ValueError("invalid DeepSeek SSE JSON: " + str(error)) from error
    if not isinstance(record, dict):
        raise ValueError("invalid DeepSeek SSE record")
    if record.get("error") is not None:
        raise ValueError("DeepSeek SSE provider error")
    usage = record.get("usage")
    if isinstance(usage, dict):
        input_tokens = usage.get("prompt_tokens", -1)
        output_tokens = usage.get("completion_tokens", -1)
        if (
            isinstance(input_tokens, int)
            and not isinstance(input_tokens, bool)
            and input_tokens >= 0
            and isinstance(output_tokens, int)
            and not isinstance(output_tokens, bool)
            and output_tokens >= 0
        ):
            chunks.append(
                ModelChunk(
                    "usage",
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                )
            )
    choices = record.get("choices", [])
    if not isinstance(choices, list):
        raise ValueError("invalid DeepSeek SSE choices")
    if len(choices) == 0:
        return
    if len(choices) != 1 or not isinstance(choices[0], dict):
        raise ValueError("DeepSeek provider requires one response choice")
    delta = choices[0].get("delta", {})
    if not isinstance(delta, dict):
        raise ValueError("invalid DeepSeek SSE delta")
    content = delta.get("content")
    if content is not None and content != "":
        if not isinstance(content, str):
            raise ValueError("invalid DeepSeek text delta")
        chunks.append(ModelChunk("text", content))
    reasoning = delta.get("reasoning_content")
    if reasoning is not None and reasoning != "":
        if not isinstance(reasoning, str):
            raise ValueError("invalid DeepSeek reasoning delta")
        chunks.append(ModelChunk("reasoning", reasoning))
    tool_calls = delta.get("tool_calls", [])
    if not isinstance(tool_calls, list):
        raise ValueError("invalid DeepSeek tool-call deltas")
    i = 0
    while i < len(tool_calls):
        call = tool_calls[i]
        if not isinstance(call, dict):
            raise ValueError("invalid DeepSeek tool-call delta")
        function = call.get("function", {})
        if not isinstance(function, dict):
            raise ValueError("invalid DeepSeek tool function delta")
        index = call.get("index", -1)
        if not isinstance(index, int) or isinstance(index, bool) or index < -1 or ("index" in call and index < 0):
            raise ValueError("invalid DeepSeek tool-call index")
        if call.get("type", "function") != "function":
            raise ValueError("unsupported DeepSeek tool-call type")
        call_id = call.get("id", "")
        name = function.get("name", "")
        arguments = function.get("arguments", "")
        if not isinstance(call_id, str) or not isinstance(name, str) or not isinstance(arguments, str):
            raise ValueError("invalid DeepSeek tool-call fields")
        chunks.append(
            ModelChunk(
                "tool-call-delta",
                "",
                call_id,
                name,
                arguments,
                tool_index=index,
            )
        )
        i += 1
    reason = choices[0].get("finish_reason")
    if reason is not None:
        if not isinstance(reason, str) or reason == "":
            raise ValueError("invalid DeepSeek finish reason")
        chunks.append(ModelChunk("finish", reason))


def assemble_chunks(chunks) -> ModelResult:
    text = ""
    tool_calls = []
    input_tokens = -1
    output_tokens = -1
    reasoning = ""
    reason = ""
    i = 0
    while i < len(chunks):
        chunk = chunks[i]
        if chunk.kind == "text":
            text += chunk.text
        elif chunk.kind == "reasoning":
            reasoning += chunk.text
        elif chunk.kind == "tool-call" or chunk.kind == "tool-call-delta":
            merge_tool_delta(tool_calls, chunk)
        elif chunk.kind == "usage":
            input_tokens = chunk.input_tokens
            output_tokens = chunk.output_tokens
        elif chunk.kind == "finish":
            if reason != "" and reason != chunk.text:
                raise ValueError("conflicting DeepSeek finish reasons")
            reason = chunk.text
        i += 1
    if reason == "":
        reason = "tool_calls" if len(tool_calls) > 0 else "stop"
    if reason == "stop" and text == "" and reasoning == "" and len(tool_calls) == 0:
        raise ValueError("empty DeepSeek response")
    if reason == "stop" and len(tool_calls) > 0:
        raise ValueError("DeepSeek tool calls require a tool-call finish")
    if reason == "tool_calls":
        for call in tool_calls:
            if call.call_id == "" or call.name == "":
                raise ValueError("incomplete DeepSeek tool-call identity")
        if len(tool_calls) == 0:
            raise ValueError("DeepSeek tool-call finish has no calls")
    return ModelResult(
        text,
        tool_calls,
        chunks,
        reason,
        input_tokens,
        output_tokens,
        reasoning,
    )


def merge_tool_delta(tool_calls, chunk: ModelChunk) -> None:
    selected = -1
    for index in range(len(tool_calls)):
        call = tool_calls[index]
        if chunk.tool_index >= 0 and call.index == chunk.tool_index:
            selected = index
        elif chunk.call_id != "" and call.call_id == chunk.call_id:
            if chunk.tool_index >= 0 and call.index != chunk.tool_index:
                raise ValueError("DeepSeek tool-call id changed index")
            selected = index
    if selected < 0 and chunk.tool_index < 0 and chunk.call_id == "":
        if len(tool_calls) != 1:
            raise ValueError("ambiguous DeepSeek unindexed tool-call delta")
        selected = 0
    if selected < 0:
        tool_calls.append(
            ToolCall(chunk.call_id, chunk.name, chunk.arguments, chunk.tool_index)
        )
        return
    call = tool_calls[selected]
    if chunk.call_id != "":
        if call.call_id != "" and call.call_id != chunk.call_id:
            raise ValueError("DeepSeek tool-call index changed id")
        call.call_id = chunk.call_id
    call.name += chunk.name
    call.arguments += chunk.arguments


def text_result(text: str) -> ModelResult:
    return ModelResult(text, [], [ModelChunk("text", text)])
