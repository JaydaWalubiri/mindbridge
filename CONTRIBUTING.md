# Working with Git

## Branches

- `main`: reviewed, working application. Merge through a pull request after checks pass.
- `feat/<short-topic>`: a new feature, for example `feat/whatsapp-onboarding`.
- `fix/<short-topic>`: a correction, for example `fix/session-double-booking`.
- `docs/<short-topic>`: documentation, for example `docs/review-guide`.

The existing `feat/full-stack-care-workspace` branch continues the current review. Do not rename it while its PR and Windows checkouts use it. Start subsequent focused branches from updated `main` after this PR is merged. This small project does not need a permanent `develop` branch.

## Daily workflow

```powershell
git status -sb
git pull --ff-only
```

Use this on a clean checkout of the branch you intend to update. If Git shows local changes or cannot fast-forward, inspect before pulling again; do not discard changes or force-push to make the error disappear.

For a new task after the current PR is merged:

```powershell
git switch main
git pull --ff-only
git switch -c feat/short-topic
```

Make a focused change, run relevant checks, inspect `git diff`, and stage explicit paths:

```powershell
git add care/views.py templates/care/dashboard.html
git diff --cached
git commit -m "feat: show pending counselling requests"
git push -u origin feat/short-topic
```

Include actual migration and test paths whenever required by the feature. Avoid `git add .` when secrets, notebooks, downloads, or unrelated work may be present.

## Commit messages

Use `type: action and result`, with simple, specific wording:

| Type | Example |
| --- | --- |
| `feat` | `feat: let participants choose counselling times` |
| `fix` | `fix: prevent overlapping counselling appointments` |
| `test` | `test: verify counsellor assignment and booking` |
| `docs` | `docs: explain local setup and project folders` |
| `chore` | `chore: ignore local model checkpoints` |

A commit should form one reviewable change. Avoid `update`, `final`, `stuff`, or version-number filenames. Add a body when the reason or limitation needs explanation. Do not rewrite existing published history merely to improve old messages.

## Pull requests and merging

1. Explain the resulting behavior, relevant validation, migrations and remaining dependencies.
2. Keep unfinished work in a draft PR. Mark ready after review and validation.
3. Require passing checks and review before merging into `main`.
4. Use **Squash and merge** for a focused future PR with incidental intermediate commits. Preserve the current PR's published history until a merge is deliberately chosen.
5. After merge, remove the finished remote task branch and start the next task from updated `main`.
6. Never commit or push runtime databases, private conversations, credentials or model weights.

These are repository workflow conventions. They do not themselves enforce GitHub permissions. For server enforcement, a repository administrator should configure a `main` ruleset requiring PRs and the Django CI check, blocking force pushes and branch deletion. Do not claim protection is active until the actual ruleset is verified.

## Required checks

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe manage.py test
```

Use fictional records for local UI review. Never include credentials or participant data in issue descriptions, test fixtures or screenshots.
