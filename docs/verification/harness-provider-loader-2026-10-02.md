# Harness provider and Loader qualification

## Implemented source paths

The model adapter now keeps the provider's tool-call index while assembling
interleaved deltas. It rejects conflicting index/id mappings, ambiguous
unindexed continuations and incomplete successful-call identities. Legacy
single-call unindexed fixtures remain supported; they cannot silently merge
multiple pending calls. Assistant history encodes grouped `tool_calls` with
exact argument strings and corresponding tool-result ids. Text and reasoning
from tool-call responses are reconstructed from the logged chunks on replay.

`post_sse(url, headers, body, cancellation)` returns an iterable of decoded
text chunks. The adapter reads lazily, stops at `[DONE]`, closes a closeable
response on success/error/cancellation, and rejects truncated, malformed and
empty responses. Accepted deltas reach the session event log before the next
transport read. Finish reasons and trailing usage are retained; a truncated
or non-tool-call finish does not authorize tool execution.

One cancellation token is shared across the agent, model transport and tools.
Session replacement and runtime disposal cancel the prior agent before
withdrawing services, preventing late results from executing tools. Disposal
continues root/kernel cleanup after a Loader cleanup error and preserves the
first failure. The native entrypoint now propagates `main`'s exit status.

The synchronous Loader snapshots nested configuration and catalog identity.
Explicit `PluginCatalog.replace` changes the implementation generation even
when the declarative entry is unchanged. Old registration disposers cannot
remove replacements. Failed candidate setup remounts the captured prior
implementation/configuration rather than resolving the failed catalog entry
again. Failed old cleanup retires the actual unmounted suffix records before
propagating its error, so later reconciliation can remount the original desired
tree instead of mistaking missing resources for a committed prefix. This is
not asynchronous setup or automatic module-watcher reload.

## Source comparison

The upstream pin remains `47f943859bef60e4160492346772ded9b24f765a`.
The [pinned translator](https://github.com/deepseek-ai/deepseek-harness/blob/47f943859bef60e4160492346772ded9b24f765a/packages/llm/llm-deepseek/src/translate.ts)
and [serializer](https://github.com/deepseek-ai/deepseek-harness/blob/47f943859bef60e4160492346772ded9b24f765a/packages/llm/llm-deepseek/src/serialize.ts)
were inspected for indexed calls, response termination and grouped assistant
history. The [official wire schema](https://api-docs.deepseek.com/api/create-chat-completion/)
defines streamed indices and `[DONE]`; the
[tool-call guide](https://api-docs.deepseek.com/guides/tool_calls/)
shows assistant/tool history pairing. These source comparisons informed the
fixtures; the upstream TypeScript implementation was not executed, so this
is not full upstream or live-provider parity.

## Executed evidence

The final host-only `examples/harness/tests` selection passed **100 tests** on
2026-10-02, using qualified CPython 3.15 development tooling with native
provisioning disabled. Relative to the prior 70 Harness checks, the 30 added
cases comprise 21 provider-protocol cases, four agent tool/stream/replay/
cancellation cases, four synchronous Loader replacement/recovery cases and one
cleanup-error continuation case. Parameterized cases are counted separately;
the interleaved-call case also checks every two-piece transport split.

The same final run included **three** emission cases, compiling the actual
`model_runtime.py`, `agent_runtime.py` and `loader_runtime.py` unchanged to
Linux IR and PCC-owned ELF objects. All **103 cases** completed in 10.21
seconds. The 120-second, 1-GiB process-tree watchdog observed 187,109,376 bytes
peak RSS. Harness and core Python source hashes matched before and after the
run; source identities, IR and objects were retained. This checks the current
development compiler's lowering/emission path and host behavior. It does not
link or execute a native Harness program or qualify an installed self-hosted
compiler. No HTTP request, credential use, local Mac operation or upstream
execution was part of this gate.

## Native and transport boundaries

`tests/test_harness_gui.py::test_current_pcc1_native_harness_headless` is a new
opt-in integration gate. It compiles the actual `examples/harness/app.py`,
runs its runtime self-check plus assistant/tool CLI turns, and checks failure
exit status. It does not invoke `build.sh`, build a bridge/archive or rewrite
the application. It remains pending the qualified compiler/runtime freeze.

A real streaming HTTP/TLS client is still missing from the selected native
owners. Gateway supplies nonblocking socket/DNS primitives and an HTTP/1
upstream response codec, but its current TLS provider is server/listener-only
(`SSL_set_accept_state`). Outbound TLS requires client mode, emitted SNI,
certificate-chain and hostname verification, and cancellation/deadline/close
ownership. The relay-specific `ProxyExchange` is not an application-client
API. Buffered system-libcurl/host HTTP is not substituted for PCC virtual-thread
streaming. The adapter's tested injected stream is deliberately not claimed as
a live network transport.

Asynchronous Loader/effect completion, automatic module-watcher HMR, the
remaining capability families, and real AppKit/Metal interactions/pixels
remain separate acceptance work. No migration commit or upstream-pin change
was made; the imported ledger's existing pending identity is preserved.
