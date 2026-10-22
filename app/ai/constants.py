"""The ai package constants."""

CAN_SUGGEST_TODO_SUBTASKS = "can_suggest_todo_subtasks"

AI_REQUESTS_RATE_LIMIT = "ai_requests"

# Why: room for the thinking and a structured answer of a few hundred words;
# requests are not streamed, so the answer must arrive well within the timeout.
MAX_TOKENS = 16000
# Why: Claude Opus 5.5 runs at medium by default; set explicitly, a change of the
# default can never change the cost unnoticed.
EFFORT = "medium"
# Why: when a safety classifier declines a request, the API runs it again on
# the model Anthropic recommends for that kind of refusal.
FALLBACK_BETA = "server-side-fallback-2026-07-01"

MIN_SUBTASKS = 2
MAX_SUBTASKS = 8
