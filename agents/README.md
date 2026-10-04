This skill is for coding agents that can read SKILL.md and run Bash, Python 3 and curl.

It is not an Agent Harness. Install it as its own skill, then pass a search, image, or System One decision prompt.

Primary install:

```bash
bunx skills add Barrierml/tako-skill -g -y
```

Claude Code can also clone into `.claude/skills/tako-skill`.

Codex does not auto-load that folder; paste the prompt from README.md / SKILL.md.
