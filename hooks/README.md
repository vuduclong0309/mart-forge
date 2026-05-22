# hooks/

Claude Code hooks that orient agents when a session starts inside a mart-forge project.

## hooks.json schema

```jsonc
{
  "hooks": {
    "SessionStart": [
      {
        "command": "...",          // shell command executed on session start
        "description": "..."      // human-readable purpose
      }
    ]
  }
}
```

The top-level key is the lifecycle event; currently only `SessionStart` is used.
Each entry runs its `command` in the user's shell when the event fires.

## SessionStart lifecycle

When a Claude Code session opens inside a directory containing
`.claude/settings.json` that references this hooks file, the runtime:

1. Reads `hooks.json` and iterates the `SessionStart` array.
2. Executes each `command` in order, streaming stdout to the agent's context.
3. The agent sees the output as initial orientation before any user prompt.

The mart-forge SessionStart hook prints:
- Framework identity and Kimball lifecycle phases (BRD -> TDD -> Scaffold -> DQC -> Presentation).
- The list of available skills.
- Key constraints (no SELECT \*, provenance on every ODS, all 8 DQC controls).

## How `/using-mart-forge` routes to skills

The SessionStart output tells the agent to run `/using-mart-forge` first.
That skill inspects the current project state (which files exist, what phase
the mart is in) and routes to the appropriate next skill:

| Project state                        | Routed skill       |
|--------------------------------------|--------------------|
| No `mart.yml` present               | `/mart-bootstrap`  |
| Models exist but DQC incomplete      | `/dqc-audit`       |
| Schema change detected               | `/schema-evolve`   |
| Ready for production review          | `/mart-review`     |

This routing is automatic — the agent does not need to pick the right skill
manually; `/using-mart-forge` handles detection and delegation.
