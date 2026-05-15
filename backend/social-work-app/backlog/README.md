# Backlog

This directory holds **ticket JSON files** for breaking down large initiatives into smaller, commit-sized work items. Agents (or developers) can reference a single ticket file when implementing a task to keep changes focused and commits manageable.

## Ticket format

Each ticket is a JSON file with:

- **id**: Short unique identifier (e.g. `RP-001`).
- **title**: One-line summary.
- **description**: What to do and why (can reference the parent plan).
- **parent_plan**: Path or name of the overarching plan (e.g. runtime privilege generation).
- **files**: Main file paths to touch (relative to repo or `backend/cosmetology-app`).
- **acceptance_criteria**: List of conditions that must hold when the ticket is done.
- **dependencies**: Optional list of ticket ids that should be completed first.

## Implementation order

Tickets that list **dependencies** must be implemented after those dependencies. Within the same initiative, tickets are intended to be implemented in numerical order unless dependencies say otherwise.

## Initiative: Runtime Privilege Generation

Tickets are in `runtime-privilege-generation/`. Implement in order **RP-001** through **RP-011**. The parent plan is:

`/Users/landon/.cursor/plans/runtime_privilege_generation_85d68513.plan.md`
