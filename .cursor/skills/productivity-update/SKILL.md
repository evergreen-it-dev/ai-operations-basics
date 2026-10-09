---
name: productivity-update
description: Sync tasks and refresh context from current activity. Use when pulling new assignments from Jira into workspace/TASKS.md, triaging stale or overdue tasks, cross-checking workspace/memory for gaps, or running a comprehensive scan to catch todos buried in chat and email.
argument-hint: "[--comprehensive]"
---

# Update Command

Keep your task list and workspace context current. Two modes:

- **Default:** Sync tasks from external tools, triage stale items, check memory for gaps
- **`--comprehensive`:** Deep scan chat, email, calendar, docs — flag missed todos and suggest memory updates

## Usage

```
/productivity:update
/productivity:update --comprehensive
```

## Default Mode

### 1. Load Current State

Read **`workspace/TASKS.md`** and **`workspace/memory/`** (daily logs). If TASKS.md doesn't exist, create it from **`workspace.example/TASKS.md.example`**.

### 2. Sync Tasks from External Sources

Check for available task sources:
- **Jira** (MCP `user-mcp-atlassian-on-prem` or `plugin-atlassian-atlassian`) — issues assigned to the user
- **GitHub Issues** (if in a repo): `gh issue list --assignee=@me`

If no sources are available, skip to Step 3.

**Fetch tasks assigned to the user** (open/in-progress). Compare against `workspace/TASKS.md`:

| External task | TASKS.md match? | Action |
|---------------|-----------------|--------|
| Found, not in TASKS.md | No match | Offer to add |
| Found, already in TASKS.md | Match by title (fuzzy) | Skip |
| In TASKS.md, not in external | No match | Flag as potentially stale |
| Completed externally | In Active section | Offer to mark done |

Present diff and let user decide what to add/complete.

### 3. Triage Stale Items

Review Active tasks in TASKS.md and flag:
- Tasks with due dates in the past
- Tasks in Active for 30+ days
- Tasks with no context (no person, no project)

Present each for triage: Mark done? Reschedule? Move to Someday?

### 4. Decode Tasks for Memory Gaps

For each task, attempt to decode all entities (people, projects, acronyms, tools, links). Cross-check against **`workspace/memory/`** and **`context/company/`**.

Track what's fully decoded vs. what has gaps.

### 5. Fill Gaps

Present unknown terms grouped. Add answers to appropriate places:
- People → `context/company/people.md` or notes in task sub-bullets
- Projects → relevant `context/` or `docs/` files
- Acronyms → glossary note in task or local doc

### 6. Capture Enrichment

Tasks often contain richer context than memory. Extract and update:
- **Links** from tasks → add to project/people notes
- **Status changes** → update related docs or task sections
- **Relationships** → cross-reference in task sub-bullets
- **Deadlines** → ensure due dates are in TASKS.md

### 7. Report

```
Update complete:
- Tasks: +3 from Jira, 1 completed, 2 triaged
- Memory: 2 gaps filled, 1 project enriched
- All tasks decoded ✓
```

## Comprehensive Mode (`--comprehensive`)

Everything in Default Mode, plus a deep scan of recent activity.

### Extra Step: Scan Activity Sources

Gather data from available MCP sources:
- **Teams** (skill **teams-chat-review**)
- **Gmail** (skill **gmail-tools**)
- **Telegram** (skill **telegram-mcp**)
- **Jira** (skill **jira**)

### Extra Step: Flag Missed Todos

Compare activity against TASKS.md. Surface action items that aren't tracked. Let user pick which to add.

### Extra Step: Suggest New Context

Surface new entities not yet documented in memory or context files. Present grouped by confidence.

## Notes

- Never auto-add tasks or memories without user confirmation
- External source links are preserved when available
- Fuzzy matching on task titles handles minor wording differences
- Safe to run frequently — only updates when there's new info
- `--comprehensive` always runs interactively
- Chat memory hook already logs turns to **`workspace/memory/YYYY-MM-DD.md`** — use it as a source, don't duplicate hook behavior
