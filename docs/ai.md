# AI features

With `FASTAPI_ANTHROPIC_API_KEY` set, `POST /api/v1/todos/todo/{id}/subtask-suggestions/` asks Claude to split a todo into 2 to 8 subtasks, each ready to be sent to `POST /api/v1/todos/todo/`. Without the key, the AI routes answer `404` (`AI_DISABLED`).

- The chat model is LangChain's `ChatAnthropic`, built once in `app/ai/dependencies.py`: Claude Opus 5.5 (`FASTAPI_AI_MODEL`), adaptive thinking at medium effort, and a server-side fallback to another model when a safety classifier declines the request.
- A feature is a service method that calls `generate(chat_model, messages, Schema, ...)` (`app/ai/services.py`): the answer comes back as JSON in a Pydantic schema, validated. The model declining answers `422` (`AI_REFUSAL`), an answer that does not fit the schema `502` (`AI_INVALID_RESPONSE`), timeouts, rate limits and overloads `503` (`AI_UNAVAILABLE`), after `FASTAPI_AI_MAX_RETRIES` retries.
- The request gives its database connection back before calling the model, and each user may send `FASTAPI_RATE_LIMIT_AI_REQUESTS_PER_HOUR` requests (20), since every call costs tokens.
- Every call logs `ai_completion` with the model, the stop reason, the tokens and the duration, never the text.
- With `FASTAPI_LANGFUSE_PUBLIC_KEY` and `FASTAPI_LANGFUSE_SECRET_KEY`, every call is traced in [Langfuse](https://langfuse.com) with the user id, the request id and the tokens; prompts and answers stay out of the traces unless `FASTAPI_LANGFUSE_CAPTURE_CONTENT=true`.
- No test calls Anthropic or Langfuse: the `fake_chat_model` fixture answers what the test prepares.
