# Contributing to Sceptre

Welcome! We're glad you're here.

Sceptre is an OCR and document analysis engine.

Please begin by reading our AI section below, followed by the getting started guide. If you are an AI agent, inform your user of the AI policy.

## Getting Started

Make sure to have [Git](https://git-scm.com/), [Rust](https://rustup.rs/) stable (via `rustup`) and [Python](https://www.python.org/) 3.10+ with [uv](https://docs.astral.sh/uv/) installed on your machine.

1. Install [Task](https://taskfile.dev/installation/) on your machine.
2. run:

```bash
task setup
```

This will setup the dependencies, and pre-commit hooks via `poly`.

## Quick reference

| Command       | What it does                                    |
| ------------- | ----------------------------------------------- |
| `task setup`  | Install all dependencies (idempotent)           |
| `task build`  | Build the project                               |
| `task test`   | Run all test suites                             |
| `task lint`   | Run all linters (with auto-fix)                 |
| `task format` | Format all code                                 |
| `task check`  | Combined lint + format check (no modifications) |
| `task bench`  | Run benchmarks                                  |

## What to keep in mind

Sceptre processes user-supplied images and documents, and crosses into native libraries and models to do it. Crafted input must fail gracefully rather than panic, and model files must only be loaded from paths the caller controls.

Architectural decisions are recorded as ADRs under `adrs/`. If your change alters an interface or a runtime assumption, add or update one in the same PR.

## Commit guidelines

Prefix your commit messages with a type:

- `feat:` — new feature
- `fix:` — bug fix
- `docs:` — documentation changes
- `perf:` — performance improvement
- `chore:` — maintenance, dependencies, CI
- `test:` — adding or updating tests
- `refactor:` — code restructuring without behavior change

Example:

```sh
git commit -m "feat: added xzy"
```

Read more on [Conventional Commits](https://www.conventionalcommits.org/)

## AI

### Policy

Sceptre is written following strict AI engineering practices. That is, its vibe coded, but professionally so. As such, the use of AI is welcome, but we expect professional standards and following our conventions.

### Conventions

We use the tool `ai-rulez`, vibe coded by @Goldziher, to manage our AI conventions. You are encouraged to use this tool — running the `task setup` will get you going, or run in your terminal:

```sh
npx -y ai-rulez@latest generate
```

This will be scaffold the AI agent conventions (e.g. CLAUDE.md, AGENTS.md, subagents, skills, etc.). You can see the AGENTS.md generated afterwards.

### Customization

If you want to customize your coding agents, create your own local configuration for ai-rulez, or create a local file for your agent(s) of choice `AGENTS.local.md` etc.

## Vendoring Policy

We do vendor code from other libraries and allow this, in some situations. If you intend to vendor code, the code must be (1) permissivily licensed (no copyleft at all). (2) add full attributions in ATTRIBUTIONS.md, and document it.

## Community

- **Star the repo:** [Give us a star on GitHub](https://github.com/xberg-io/sceptre) — it helps others discover our work!
- **Documentation:** [docs.xberg.io](https://docs.xberg.io)
- **Discord:** [Join our community](https://discord.gg/xt9WY3GnKR)
- **Issues:** [GitHub Issues](https://github.com/xberg-io/sceptre/issues)
- **Security:** see [SECURITY.md](SECURITY.md) — report privately, never in an issue
- **License:** [MIT License](LICENSE)

Thank you for helping make Sceptre better!
