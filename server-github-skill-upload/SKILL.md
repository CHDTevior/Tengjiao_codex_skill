---
name: server-github-skill-upload
description: Sync one or more local Codex skill folders from this server to a GitHub repository with incremental commit and push. Use when user asks to upload/update skills, keep remote skill repo in sync, or troubleshoot skill publishing issues (SSH auth, git identity, remote URL rewrite).
---

# Server GitHub Skill Upload

Use this skill to publish local skills from the server to a GitHub repo in a repeatable way.

## Workflow

1. Confirm prerequisites before pushing.
- Use SSH remote (`git@github.com:<owner>/<repo>.git`) to avoid HTTPS rewrite issues.
- Confirm auth: `ssh -T git@github.com`
- Confirm git identity:
  - `git config --global --get user.name`
  - `git config --global --get user.email`

2. Run the upload script for the target skill.

```bash
scripts/sync_skill_to_github.sh \
  --skill markdown-mermaid-support \
  --repo-path /vepfs-cnbja62d5d769987/suntengjiao/Tengjiao_codex_skill \
  --remote-url git@github.com:CHDTevior/Tengjiao_codex_skill.git \
  --target-branch main \
  --clone-if-missing
```

3. Validate result.
- Check local status is clean: `git -C <repo-path> status --short --branch`
- Check latest commit: `git -C <repo-path> log --oneline -n 1`
- Optionally verify on GitHub web UI.

## Multi-Skill Sync

Pass `--skill` multiple times to submit several skills in one commit:

```bash
scripts/sync_skill_to_github.sh \
  --skill markdown-mermaid-support \
  --skill server-github-skill-upload \
  --repo-path /vepfs-cnbja62d5d769987/suntengjiao/Tengjiao_codex_skill \
  --remote-url git@github.com:CHDTevior/Tengjiao_codex_skill.git \
  --target-branch main \
  --clone-if-missing
```

## Notes

- Script uses `rsync --delete` to keep repo copy identical to source skill folder.
- If no staged diff is found, script exits without commit.
- For auth/config failures, use `references/troubleshooting.md`.
