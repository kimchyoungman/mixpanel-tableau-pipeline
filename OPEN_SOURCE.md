# Open Source Publishing Guide

This repository was originally developed as a private project. Before making it
public, publish from a clean history or a fresh public snapshot so private logs
and organization-specific defaults from older commits are not exposed.

## Current Public-Safe Defaults

The working tree is configured to avoid project-specific defaults:

- `TABLEAU_PROJECT_NAME` defaults to `Default`.
- `MIXPANEL_TIMEZONE` defaults to `UTC`.
- `.env.example` contains empty placeholders instead of credentials.
- The GitHub Actions workflow is manual by default.
- Generated outputs, logs, state files, and `.env.*` files are ignored.

## Recommended Path: Fresh Public Snapshot

Use this path if you do not need to preserve the old private commit history.
It is the safest option because old commits containing generated logs never
become part of the public repository.

```bash
# From the sanitized working tree
git switch --orphan public-main
git add .
git commit -m "chore: prepare open-source release"

# Push this branch to a new public repository or replace the public default branch.
git remote add public https://github.com/<owner>/<public-repo>.git
git push public public-main:main
```

After pushing, verify the public repository:

```bash
git clone https://github.com/<owner>/<public-repo>.git /tmp/mixpanel-tableau-public-check
cd /tmp/mixpanel-tableau-public-check
rg -n "PRIVATE KEY|TOKEN_VALUE|<org-specific-name>|<legacy-user-property>"
python -m py_compile main.py src/*.py config/*.py
python main.py --help
```

## Alternative: Rewrite The Private History

Use this path only if preserving the commit history matters. It rewrites commit
IDs, so coordinate with anyone who already cloned the private repository.

```bash
git branch backup/pre-open-source-main main
git filter-repo --path hyperd.log --invert-paths
```

If `git filter-repo` is unavailable, install it first or use a clean public
snapshot instead. After rewriting, scan the whole history before publishing:

```bash
git grep -n -I -E "PRIVATE KEY|AKIA|AIza|xox[baprs]-|gh[pousr]_|<org-specific-name>" $(git rev-list --all)
```

## Credential Rotation

Rotate credentials before publication if they were ever used in local runs,
CI logs, or deployment logs:

- Mixpanel API secret
- Tableau personal access token
- GCP service account credentials used by Cloud Build, Cloud Run, or GCS state

## Data Review

Do not publish generated `.hyper` files or logs. Mixpanel exports can include
user identifiers, URLs, marketing parameters, or other event properties that are
not appropriate for a public repository.
