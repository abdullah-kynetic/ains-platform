# Stage 2 prompt: security-skill audit in Claude Code

Paste this into Claude Code, opened on a fresh clone of `abdullah-kynetic/ains-platform` at `main`. **Use it only after Stage 1 (G1) is reported green.** Stage 1 code lanes ran in OpenAI Codex cloud; Slave Kien operates the VPS at `135.148.219.175`. You still have no SSH access.

```
You are running Kien's Stage 2 security audit. Repo: abdullah-kynetic/ains-platform (main). The live site is a single environment: web at https://auditor.kiensolutions.com plus the synthetic pilot firm hosts listed in web/wrangler.jsonc env.production, and the API at https://api.kiensolutions.com. Synthetic data only. Read CLAUDE.md, AGENTS.md, docs/BUILD-PLAN.md (Parts 4.5, 5, 6 and 7), docs/security/** and docs/inventory/PRODUCT-INVENTORY.md first.

1) Install the skills (free and open source). Before enabling any of them, read each SKILL.md, or run Sentry's skill-scanner on it. Don't enable a skill that runs network calls you can't explain.
   /plugin marketplace add trailofbits/skills      (then enable: static-analysis, insecure-defaults, sharp-edges, differential-review, supply-chain-risk-auditor, agentic-actions-auditor, entry-point-analyzer, audit-context-building, variant-analysis, fp-check)
   claude plugin marketplace add getsentry/skills  then  claude plugin install sentry-skills@sentry-skills   (use: security-review, gha-security-review, security-model, skill-scanner, find-bugs)
   /plugin marketplace add agamm/claude-code-owasp  then  /plugin install owasp-security@agamm
   npx skills add semgrep/skills                   (code-security, llm-security, semgrep)
   /plugin marketplace add cloudflare/skills        (use workers-best-practices and wrangler, for Workers config, secrets and headers)
   Reference checklists: OWASP ASVS 5.0 Level 2 (github.com/OWASP/ASVS), OWASP Cheat Sheet Series (github.com/OWASP/CheatSheetSeries), OWASP WSTG (github.com/OWASP/wstg).

2) Run, writing every result to docs/security/stage2/<tool>.md (tool, version, command, findings with file:line, severity):
   a) /security-review (built-in Claude Code command; the customizable version is at github.com/anthropics/claude-code-security-review .claude/commands/security-review.md) over the whole repo, not just pending changes. Do this by reviewing against an empty base branch or path by path: app/, ai_adapter/, web/src/, deploy/, .github/.
   b) Each enabled Trail of Bits, Sentry, OWASP and Semgrep skill over the same paths. Cloudflare workers-best-practices over web/ and the wrangler configs.
   c) CLI scanners: semgrep scan --config p/python --config p/typescript --config p/owasp-top-ten --config p/secrets; bandit -r app ai_adapter -ll; uvx pip-audit; (web) npm audit --omit=dev; gitleaks git --redact .; trufflehog git file://. --only-verified; trivy fs --scanners vuln,secret,misconfig .; uvx zizmor .github/workflows.
   d) Live, read-only, against the synthetic pilot only: docker run --rm -t ghcr.io/zaproxy/zaproxy:stable zap-baseline.py -t https://auditor.kiensolutions.com (and one firm host); curl -sI for headers on every host; testssl.sh on api.kiensolutions.com. No brute force, no denial-of-service, and no scanning of any host other than these. Never scan 40.160.150.91.
   e) Map every ASVS 5.0 Level 2 requirement that applies to docs/security/stage2/asvs-l2.md, as Met / Partial / Not met, with evidence (a test, file or command).

3) Triage into docs/security/stage2/FINDINGS.md: ID, source tool, severity (Critical/High/Medium/Low), file:line or URL, a description, the fix, and a status. Mark false positives with a reason. Use the fp-check skill.

4) Fix loop, one finding or a small group per PR:
   - branch sec/<id> from origin/main; make the smallest fix, plus a regression test that would have caught it
   - run uv sync --frozen && uv run ruff check . && uv run pytest -q, and in web: npm ci && npm run lint && npm run typecheck && npm run test:unit && npm run build:cloudflare:production && npm run test:e2e && npm run test:e2e:live
   - at most 3 attempts per failure; an independent review pass of the diff (max 2 rounds); merge on green with a merge commit (no rebase, squash or force-push)
   - re-run the tool that reported the finding and confirm it's gone
   - when blocked: record DECISION or BLOCKED(owner) in FINDINGS.md and continue
   Slave Kien (not you) deploys fixes to the live server. List the commits that need deploying.

5) Repeat steps 2–4 until there are zero open Critical/High findings, and every Medium is fixed or accepted in docs/security/accepted-risks.md with a reason and an expiry date. Then write docs/security/stage2/SUMMARY.md: the tools run, the counts before and after, what's accepted, and what Abdullah must check.

Hard limits: no secrets in files, PRs or chat; synthetic data only; never touch 40.160.150.91; no SAR material to any model; no AI model calls in app/; no engine (audit_engine) work, since Stage 3 starts only after Abdullah signs off; neutral black-and-white design; clients never see findings; never claim a scan or test ran unless it did. Commit as abdullah-kynetic <211030198+abdullah-kynetic@users.noreply.github.com>.

Finish by telling Abdullah, in plain English: what was checked, what was found and fixed, what's accepted and why, and the exact list he should verify before he says "Stage 2 signed off".
```

**Optional:** the GitHub Action `anthropics/claude-code-security-review@main` (MIT) reviews every PR, but it needs an Anthropic API key, which is paid usage. Only add it if Abdullah approves the cost.
