# Troubleshooting

## SSH authentication fails

Symptom:
- `Permission denied (publickey)` on clone/push.

Fix:
1. Generate key if needed: `ssh-keygen -t ed25519 -C "<github-email>"`
2. Add key to agent: `eval "$(ssh-agent -s)" && ssh-add ~/.ssh/id_ed25519`
3. Add public key to GitHub: `cat ~/.ssh/id_ed25519.pub`
4. Test: `ssh -T git@github.com`

## Git identity not configured

Symptom:
- Commit fails with `Please tell me who you are`.

Fix:
- `git config --global user.name "<name>"`
- `git config --global user.email "<email>"`

Tip:
- Use straight ASCII quotes (`"`), not Chinese quotes (`“”`).

## HTTPS rewritten to githubfast

Symptom:
- URL is rewritten from `https://github.com/...` to `https://githubfast.com/...`
- Clone/push returns 403.

Fix:
1. Prefer SSH remote: `git@github.com:<owner>/<repo>.git`
2. Inspect rewrite rule:
   - `git config --global --get-regexp '^url\\..*insteadof$'`
3. If needed, remove rewrite:
   - `git config --global --unset-all url.https://githubfast.com/.insteadof`
