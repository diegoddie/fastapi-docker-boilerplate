"""
The ai package: features built on Claude, through LangChain.

A feature is a service method that asks the chat model (``ChatModelDep``) for
an answer in a Pydantic schema with ``generate``, which maps the failures of
the model to HTTP errors and logs the tokens spent; Langfuse traces the calls
when its keys are set. Without ``FASTAPI_ANTHROPIC_API_KEY`` the AI routes
answer 404.
"""
