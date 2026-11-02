# SOP — Development workflow

Abdullah Ahmed owns product decisions and reviews the requested pull requests. Quentin Koch approves audit criteria, findings and report wording. Coding agents read the code and applicable repository instructions, then implement small slices.

1. Read AGENTS.md, CLAUDE.md, PRODUCT.md, DESIGN.md, the frontend inventory and the relevant architecture, data, security, testing and knowledge-base documents.
2. Work on one branch and one PR per slice, stacked in the requested order. Preserve unrelated work.
3. Keep API shapes typed; enforce firm ownership and engagement assignment server-side. Add cross-tenant denial coverage to every new API path. Keep rubric placeholders empty.
4. Run appropriate checks from [Testing](../TESTING.md). Report exact commands/results. UI changes need before/after desktop light, desktop dark and phone screenshots.
5. Commit as `abdullah-kynetic <211030198+abdullah-kynetic@users.noreply.github.com>`, push the branch and open the PR. If PR creation is unavailable, report the pushed branch.
6. Report changes, checks, screenshots, limitations, Decisions needed and Needs Quentin / attorney. Continue authorized slices without waiting for review unless explicitly told to stop.

Use real merge commits only; no rebase, squash, force-push or direct main push. This task does not authorize merging, deployment, production migrations, server operations or external messages. Preview deployment requires an explicit step, and no such step appears in the current scope. Keep work synthetic and model calls out of the workflow application. Do not change paid services or make product/spending decisions for the owner.
