"""External-model bridges: Gemini API client and Nebius Scientific AI MCP client.

Credentials are read only from env files at call time, only into request headers, and
every string that is persisted passes through ``common.redact``.
"""
