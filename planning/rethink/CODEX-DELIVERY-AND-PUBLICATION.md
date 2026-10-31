# Codex delivery and native Site publication

Operational handoff read on October 31, 2026. Sources: `/data/artifacts/delphi-evolve-rethink/codex-api/MESSAGING.md` and `HOSTING-HANDOFF.md`. This records the existing bridge; it does not create a new service or deployment.

For instructions to this active API worker, use the documented native durable queue:

```sh
env CODEX_HOME=/home/ubuntu/.codex-api-delphi codex queue \
  --thread 01a1923a-6fe0-7e71-bbf3-a9cc8bd3f244 \
  --message 'Concise coordinator instruction'
```

The primary's messaging receipt says this command was tested with exit 0 and an explicit queue receipt. Do not add `--resume` while this worker is live. Do not rely on tmux Enter to submit composer text. For complex messages, pass text as an argument array or through a quoted heredoc wrapper, never unsafe shell interpolation. Never include credentials. Shared director/message files remain a durable coordination channel; this worker reads them directly. No self-queued duplicate of completed work is needed.

Science ownership remains with Codex API and the director. The director coordinates existing owners; each edits only its own checkout. The broader native goal remains paused; the explicitly assigned scientific reviews continue as targeted work.

Only the primary edits `/data/worktrees/delphi-evolve/site-hosting` or calls the native Sites connector. The hosting handoff records the existing Site at `https://delphi-evolve.lefthill1.chatgpt.site`, active version 3, owner-private. Those are the primary's checked hosting facts, not a new deployment by this worker. Preserve that audience and reuse that Site.

Once reviewed static content is ready, write `/data/artifacts/delphi-evolve-rethink/messages/site-publish-request.json` containing:

- the scientific repository worktree and exact pushed source commit SHA;
- the static site/build-output path rooted in that commit;
- the claim ledger and executed validation receipts;
- a short description of the demonstration and remaining limitations.

Notify the primary or leave that concrete request for the active primary goal to inspect. This is an artifact handoff, not a new user-permission request. The primary synchronizes, packages and publishes the exact reviewed source through its connector, then records the returned result. Do not invent deployment metadata, duplicate the Site, or claim publication from a prepared request. A publish request is not created until those concrete content and validation requirements are met.
