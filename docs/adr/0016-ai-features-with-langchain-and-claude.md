# 0016. AI features with LangChain and Claude, as an option

- Status: Accepted
- Date: 2026-10-22

## Context

Many backends now need a feature or two built on a language model. Calling one
is easy; doing it well is not: a call takes seconds and costs money, the model
can decline a request or answer out of format, the provider can be overloaded,
prompts and answers can hold personal data, and tests must never reach the
provider. The template shows one feature done end to end, as an option.

## Decision

- Generating a project asks `ai` (no by default). The module lives in
  `app/ai/`; without `FASTAPI_ANTHROPIC_API_KEY` its routes answer `404`
  (`AI_DISABLED`).
- The model is LangChain's `ChatAnthropic` on Claude Opus 5.5 (`AI_MODEL`),
  created once. The routes depend on `BaseChatModel`, the seam that tests
  replace with a fake.
- The requests fit the current models: no `temperature`, `top_p`, `top_k` or
  forced tool choice (they return 400), adaptive thinking at an explicit
  `medium` effort, `max_tokens` 16000 without streaming, and server-side
  `fallbacks: "default"`, so a request declined by a safety classifier runs
  again on the model Anthropic recommends for that kind of refusal.
- A feature asks for a structured answer (`with_structured_output(method=
  "json_schema")`), validated by Pydantic. `generate` maps the failures: a
  refusal is `422 AI_REFUSAL`, an answer out of the schema (or cut off at the
  token limit) `502 AI_INVALID_RESPONSE`, a timeout, a 429, a 5xx or a 529
  `503 AI_UNAVAILABLE` after `AI_MAX_RETRIES` retries of the SDK. Any other
  error of the provider (a bad key, a bad request) is a bug: it reaches the
  500 handler and Sentry.
- The example feature suggests the subtasks of a todo: permission
  `can_suggest_todo_subtasks`, ownership checked like every todo route, the
  database connection released before the call, a per-user limit of
  `RATE_LIMIT_AI_REQUESTS_PER_HOUR` (20), and a `200` with subtasks ready to be
  sent to the create todo route. The answer is used whole, so it is not
  streamed.
- Every call logs `ai_completion` with the model, the stop reason, the tokens
  and the duration, never the text.
- With its keys set, Langfuse traces every call with the user id and the
  request id, on an OpenTelemetry `TracerProvider` of its own; the input and
  output attributes are dropped at export unless `LANGFUSE_CAPTURE_CONTENT` is
  set.

## Consequences

- LangChain and the Anthropic SDK add ~90 MiB to each worker and a few seconds
  to its start (measured: 116 → 208 MiB, 1.9 → 5.6 s to import the app).
  Importing them lazily would not save memory, as every API worker ends up
  serving an AI request.
- The error mapping catches the Anthropic SDK's exceptions: another provider
  needs its own.
- langsmith, a dependency of LangChain, raises a deprecation warning on Python
  3.14; the test configuration ignores that one warning, until it is fixed.
- Prompts are code: they are versioned, reviewed and tested with the rest.

## Alternatives considered

- **The Anthropic SDK directly**: lighter (64 MiB) and closer to the API, but
  LangChain's model interface lets a project change provider, and its callbacks
  give the Langfuse integration for free.
- **Streaming**: right for chat, but a structured answer is only usable whole.
- **Forcing a tool call to get JSON**: rejected by the current models;
  structured outputs constrain the JSON instead.
- **Prompts managed in Langfuse**: edits without deploys, but one more runtime
  dependency on the request path; it can be added on top.
