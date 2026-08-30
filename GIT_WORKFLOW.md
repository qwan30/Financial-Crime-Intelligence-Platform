# Git Workflow Policy

## Scope and protected branches

Use a short-lived branch and a pull request for every change. Target the repository's protected default branch (`main` on the remote); do not push directly to `main` or `master`, force-push either, or delete either branch. Rebase your own branch onto the current target branch before merge; never rebase or force-push a branch shared by others.

## Branch names

Use lowercase kebab-case names in this form:

```text
<type>/<short-purpose>
```

Allowed types: `feat`, `fix`, `docs`, `test`, `chore`, `ci`, `hotfix`, and `experiment`. Examples: `docs/git-workflow`, `feat/evidence-ingest`, `fix/replay-idempotency`. Use opaque ticket IDs if available; never put customer, case, account, or SAR identifiers in a branch name.

## Commits

Use Conventional Commits:

```text
<type>(<scope>): <imperative summary>
```

Keep the subject at 72 characters or fewer, no final period, and make each commit one logical change. Examples: `docs(workflow): define pull request policy` and `fix(replay): reject conflicting events`. Do not merge `WIP`, vague (`update`, `fix stuff`), generated-only, or secret-containing commits. Use a body to explain risk, rationale, breaking changes, or issue references when needed.

## Pull requests and size

One PR should solve one problem. Use the same format for its title and include: summary, reason/risk, linked spec or issue, validation actually run, migration/rollback impact, and screenshots only for UI changes.

Aim for fewer than 400 changed non-generated lines and 15 files. A 400–800-line PR needs a short justification; split a larger PR unless the change is inseparable (for example, a migration, lockfile, or generated artifact). This is a review threshold, not a mechanical cap.

## Checks, merging, and security

Before a documentation commit, run `git diff --check` and `git status --short`. Once the application exists, also run the documented test, lint, and type-check gates. Squash merge by default, delete the merged branch, and keep the PR description accurate.

Never commit secrets, `.env` files, production logs, real customer/account/case/SAR data, evidence excerpts, or unredacted screenshots. If exposed, revoke/rotate the secret, remove access, and open a follow-up security issue. For urgent hotfixes, document the exception and create follow-up work for skipped checks.

## GitHub settings to configure

When GitHub protections and CI are added, require PRs, one approval, resolved conversations, passing tests/lint/type checks and secret scanning, no force pushes, and stale-approval dismissal on the default branch. Add code-owner review for auth, evidence, model, and infrastructure changes when ownership is defined.
