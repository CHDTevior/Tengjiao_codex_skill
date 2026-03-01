#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  sync_skill_to_github.sh --skill <name> [--skill <name> ...] [options]

Required:
  --skill <name>             Skill folder name under --skill-root

Options:
  --skill-root <path>        Source skills root (default: $HOME/.codex/skills)
  --repo-path <path>         Local git repo path
                             (default: /vepfs-cnbja62d5d769987/suntengjiao/Tengjiao_codex_skill)
  --remote-url <url>         Git remote URL
                             (default: git@github.com:CHDTevior/Tengjiao_codex_skill.git)
  --target-branch <name>     Remote branch to push (default: main)
  --message <text>           Commit message (default: auto-generated)
  --clone-if-missing         Clone repo if --repo-path does not exist
  -h, --help                 Show this help
EOF
}

SKILL_ROOT="${HOME}/.codex/skills"
REPO_PATH="/vepfs-cnbja62d5d769987/suntengjiao/Tengjiao_codex_skill"
REMOTE_URL="git@github.com:CHDTevior/Tengjiao_codex_skill.git"
TARGET_BRANCH="main"
COMMIT_MESSAGE=""
CLONE_IF_MISSING="false"
SKILLS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --skill)
      SKILLS+=("$2")
      shift 2
      ;;
    --skill-root)
      SKILL_ROOT="$2"
      shift 2
      ;;
    --repo-path)
      REPO_PATH="$2"
      shift 2
      ;;
    --remote-url)
      REMOTE_URL="$2"
      shift 2
      ;;
    --target-branch)
      TARGET_BRANCH="$2"
      shift 2
      ;;
    --message)
      COMMIT_MESSAGE="$2"
      shift 2
      ;;
    --clone-if-missing)
      CLONE_IF_MISSING="true"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if [[ ${#SKILLS[@]} -eq 0 ]]; then
  echo "At least one --skill is required." >&2
  usage
  exit 1
fi

if [[ ! -d "$REPO_PATH" ]]; then
  if [[ "$CLONE_IF_MISSING" == "true" ]]; then
    git clone "$REMOTE_URL" "$REPO_PATH"
  else
    echo "Repo path does not exist: $REPO_PATH" >&2
    echo "Use --clone-if-missing to clone automatically." >&2
    exit 1
  fi
fi

if [[ ! -d "$REPO_PATH/.git" ]]; then
  echo "Not a git repository: $REPO_PATH" >&2
  exit 1
fi

if ! git config --global --get user.name >/dev/null 2>&1; then
  echo "Missing git user.name. Run: git config --global user.name \"<name>\"" >&2
  exit 1
fi

if ! git config --global --get user.email >/dev/null 2>&1; then
  echo "Missing git user.email. Run: git config --global user.email \"<email>\"" >&2
  exit 1
fi

for skill in "${SKILLS[@]}"; do
  src="${SKILL_ROOT}/${skill}"
  dst="${REPO_PATH}/${skill}"

  if [[ ! -d "$src" ]]; then
    echo "Skill source not found: $src" >&2
    exit 1
  fi

  mkdir -p "$dst"
  rsync -a --delete "$src/" "$dst/"
  git -C "$REPO_PATH" add "$skill"
done

if git -C "$REPO_PATH" diff --cached --quiet; then
  echo "No changes detected for requested skill(s)."
  exit 0
fi

if [[ -z "$COMMIT_MESSAGE" ]]; then
  COMMIT_MESSAGE="Update skills: ${SKILLS[*]}"
fi

git -C "$REPO_PATH" commit -m "$COMMIT_MESSAGE"
git -C "$REPO_PATH" push origin "HEAD:${TARGET_BRANCH}"

echo "Push complete."
