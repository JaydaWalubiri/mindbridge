# Working on MindBridge

Follow [GitHub flow](https://docs.github.com/en/get-started/using-github/github-flow): create an issue, work on a branch, open a pull request, check the changes, then merge.

## Branches

Keep **one permanent branch, `main`**, for reviewed work. Normally, a single developer needs `main` and one branch for the task they are working on. Create branches when work begins and delete them after merging.

Use short names that explain the task:

| Task | Example branch |
| --- | --- |
| Add counselling booking | `session-booking` |
| Fix a login problem | `fix-login` |
| Connect WhatsApp | `whatsapp-connection` |
| Update documentation | `update-readme` |

There is no need for separate backend, frontend or model branches. These are parts of the application, not separate versions of it.

The existing `feat/full-stack-care-workspace` branch contains the first application build in draft PR #1. Keep it until review is complete. `organize-github` contains this repository cleanup and is based on that branch. Review and merge the cleanup into the application branch first, then merge PR #1 into `main`. Delete both completed branches afterwards. Future task branches start from `main`. Set `main` as the repository default in GitHub settings.

## Issues and milestones

Search for an existing issue before creating another. Give each issue a clear title, a short description, a checklist of completion requirements and a way to check the result. Use the labels `bug`, `enhancement` or `documentation` and assign the person doing the work.

Group related issues into the four milestones in [the roadmap](docs/ROADMAP.md). Keep the issue open until its requirements are met. Add due dates only when the project dates are confirmed.

## Making changes

After the first application PR has merged, start a task from a clean checkout:

```powershell
git switch main
git pull --ff-only
git switch -c session-booking
```

Check `git diff`, add only the files for the task, then commit and push:

```powershell
git add care/views.py templates/care/sessions.html
git diff --cached
git commit -m "Add counselling session booking"
git push -u origin session-booking
```

Commit messages should say what changed, for example `Fix overlapping appointments` or `Explain local setup`. Keep each commit focused. Avoid vague messages like `update` or `final`. Do not rewrite published commits just to rename them.

## Pull requests

- Open a pull request for a focused task. Use a draft while it is unfinished.
- Describe the change, link its issue and record how it was checked. Add screenshots for screen changes.
- Write `Closes #12` when merging into `main` completes issue 12. Use `Refs #12` when only part of the work is done or the PR targets another task branch.
- Review the diff and passing checks before merging. A solo developer can review their own changes; ask another contributor to review when available.
- Use squash merge for small task PRs, then delete the finished branch and update local `main`.

For application changes, run:

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe manage.py test
```

## GitHub settings

Set `main` as the default. Require pull requests and the Django `tests` check, and block force pushes and deletion on `main`. Enable squash merging and automatic deletion of merged task branches. For a solo project, do not require another person's approval unless a reviewer is available. Require the CI check after the workflow is present on `main`.

These settings must be configured on GitHub; writing them here does not enable them.

Use fictional records in examples. Do not commit passwords, participant data, local databases, virtual environments or model weights.
