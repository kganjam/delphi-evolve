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

## File ownership and the integrated source

The user's ownership clarification and the director's 07:21 update to `messages/director-to-dx-submit.md` fix this split:

| Owner | Paths / responsibility |
|---|---|
| Codex API | `site/review/`, its scientific computation/labels, `scripts/check_review_walkthrough.py`, scientific review receipts and claim-ledger review |
| dx-submit | Main landing page in `site/delphi/`, deck, blog, script and storyboard in `presentation/delphi/`, with their generated assets; reuse/link the existing walkthrough |
| Director | Integrate both reviewed branches, select the final exact pushed source SHA, and own the single canonical publication request |
| Primary | Native Sites publication and the separate `site-hosting` checkout; reuse the existing Site and audience |

Do not rewrite the walkthrough in the submit checkout or have Codex edit dx-submit's presentation files. A presentation summary may cite its source receipts and link `../review/index.html` from `site/delphi/index.html`. Changes to scientific statements return to the API reviewer/director; changes to presentation sources return to dx-submit. The integrator reads both branches before merging.

The ownership check is recorded in `artifacts/integration/codex-api/site-component-integrity.json`. At the inspected pushed revisions:

- Walkthrough implementation: `7f9035ac3a92aa33d829f6e528d1481bfdd3c289`; current scientific review/ledger: `8db96d6e0b94d26f2d32e9da460c47d7d0fc6b73` on `work/codex-api`.
- Presentation candidate: `47590e9530d42a8e79033f4c618853cb0625eec3` on `work/submit`. Its checkout was clean; it contains the original walkthrough, test script and browser receipt byte-for-byte and links to that walkthrough.
- Current director integration/provisional request: `ecad28a2a09c69eb3e201912f71f86e5d7833398`. The canonical `site-publish-request.json` explicitly describes a **provisional walkthrough**. The separate `site-publish-request-dx-submit.json` explicitly identifies itself as a **candidate**, not a competing canonical request.

The final integrated source SHA is **not selected by this ownership check**. It must include the presentation candidate and the latest reviewed scientific constraints, then pass final content and navigation checks. The existing walkthrough receipt may be carried forward with its original source attribution because its checked files match exactly; that does not approve the new landing/deck/blog or replace testing of their integrated links. The latest pre-run review at `9daeb117371a4adbe31e6b519c4d62004ab0ddf2` leaves evaluation results pending and rejects unsupported accuracy, abstention and robustness claims.

Package the full **`site/`** tree: landing entry `site/delphi/index.html`, walkthrough `site/review/index.html`, and existing linked routes. Packaging only `site/delphi/` would break the walkthrough link. At these snapshots, `site/index.html` still serves the preserved baseline; dx-submit/director own any final default-entry navigation change. The handoff must name the intended landing route explicitly and verify it in the integrated source. This worker neither changes the root landing page nor manufactures a final integration SHA.

Only the primary edits `/data/worktrees/delphi-evolve/site-hosting` or calls the native Sites connector. The hosting handoff records the existing Site at `https://delphi-evolve.lefthill1.chatgpt.site`, active version 3, owner-private. Those are the primary's checked hosting facts, not a new deployment by this worker. Preserve that audience and reuse that Site.

Once reviewed integrated static content is ready, the **director** writes or supersedes `/data/artifacts/delphi-evolve-rethink/messages/site-publish-request.json` containing:

- the scientific repository worktree and exact pushed source commit SHA;
- the static site/build-output path rooted in that commit and intended landing route;
- the claim ledger and executed validation receipts;
- a short description of the demonstration and remaining limitations.

Notify the primary or leave that concrete request for the active primary goal to inspect. This is an artifact handoff, not a new user-permission request. The primary synchronizes, packages and publishes the exact reviewed source through its connector, then records the returned result. Do not invent deployment metadata, duplicate the Site, or claim publication from a prepared request. A publish request is not created until those concrete content and validation requirements are met.
