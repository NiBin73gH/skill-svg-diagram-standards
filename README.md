# skill-svg-diagram-standards

> Architecture & flowchart diagrams as offline SVG for technical docs

An agent skill that standardizes how architecture diagrams, swimlane overview
charts, and flowcharts are generated inside HTML documentation — fully
offline, self-contained SVG produced by a generator. HTML/SVG is never
hand-edited; Markdown remains the only hand-written source.

Distilled from real-world Android BSP porting documentation (camera & audio
bring-up on a Qualcomm platform), where every layout rule was validated
against rendered output and human review.

## What's inside

```
framework-diagram/
├── SKILL.md                      # trigger conditions, principles, workflow, pitfalls
└── references/
    ├── layout-spec.md            # hard layout numbers & style rules
    └── generator-api.md          # Diagram API, example flows, run/verify commands
```

## Key rules the skill enforces

- **Markdown-first**: ASCII art stays in the source; `<!-- FLOWCHART: name -->`
  markers let a generator swap in SVG (original ASCII kept in a collapsible
  `<details>` block).
- **Three-plane edge semantics** (with a legend, always):
  gray solid = control, blue thick = data, orange dashed = out-of-band/feedback,
  gray dashed = association.
- **Hard layout numbers** for swimlane charts: band title baseline at
  `band_y + 23`, node top at `band_y + 48` (≥25px clearance below the title),
  inter-band gaps 20px (44px where labeled cross-band edges pass through),
  node height auto-computed from line count.
- **Orthogonal routing only**, with endpoints taken from anchor helpers
  (`top/bottom/left/right`) — never hand-computed coordinates.
- **Built-in self-checks**: no external resources (fully offline), valid SVG,
  no text overflow (CJK-aware width estimation), no edge-node crossings.
- **Mandatory visual verification**: render the SVG to PNG (cairosvg) and
  review with a vision model against a checklist before calling it done.

## Install

```bash
git clone https://github.com/NiBin73gH/skill-svg-diagram-standards.git
```

| Harness | Location |
|---------|----------|
| ZCode (user-level) | `cp -r skill-svg-diagram-standards/framework-diagram ~/.zcode/skills/` |
| ZCode (project) | `<project>/.zcode/skills/` or `<project>/.agents/skills/` |
| Claude Code | `~/.claude/skills/` (same skill format) |
| Other tools without a skills mechanism | paste `SKILL.md` + `references/` into your rules file (`AGENTS.md`, `.cursorrules`, system prompt) — the rules are tool-agnostic |

## Usage

The skill triggers automatically when you ask an agent to draw an
architecture/swimlane/flowchart diagram, upgrade ASCII or mermaid blocks to
SVG, generate HTML docs containing diagrams, or fix diagram layout issues
("spacing too small", "labels overlap"). You can also invoke it explicitly:
`/framework-diagram`.

Suggested repo description:

> Architecture & flowchart diagrams as offline SVG for technical docs.
> Agent skill (ZCode / Claude Code compatible) + layout specs & generator workflow.

Suggested topics: `svg` · `diagram` · `technical-writing` · `documentation`
· `agent-skills` · `claude-skills` · `skill`

## Note on examples

The example generator paths in `references/` point to the internal project
this skill was distilled from (they won't exist on your machine). The
specs, API description, self-check list, and verification workflow are fully
portable — use them to write your own generator for your documentation set.
