# UI Design: Memo Workspace

Date: 2026-09-13
Stage: Construction
Status: Implemented; visual acceptance pending

## Product Decision

The main object on screen is a work memo. Keep writing and reading comfortable
while the linked email and extracted context remain available. The user's
feedback rejected the initial generic, AI-demo-style presentation.

## Layout and Visual Rules

- Desktop: 222-248px library, flexible document, 272-320px context inspector.
- Below 1021px: context follows the document in a single scrollable workspace.
- Below 681px: the library becomes a collapsible navigation panel.
- White and cool neutral surfaces, charcoal text, thin separators, small blue
  action accents, and muted deadline/review colors. No gradients or hero area.
- Use native editable text, Lucide icons, labeled icon buttons, and short
  Japanese labels. Keep secondary metadata quieter than the memo.
- Sections are unframed; only actual inputs and commands have small corners.
- No confidence percentage, promotional feature copy, or oversized AI badge.

## Interaction Rules

- Search by title, memo, or email subject; filters use actual loaded records.
- Preserve drafts when switching notes within the open page.
- Require an explicit save and show whether the current document is unsaved.
- Repeated saves update the existing record, rather than create duplicates.
- Editing clears stale extracted context. Re-extraction is unsaved until save.
- Review is available only for saved content. Content changes reset review.
- Network errors leave editor text intact; actions recover from failure.
- The email can be folded, edited inline, linked, or unlinked.
- Textarea height follows its content. Narrow layouts do not horizontally
  scroll. Respect reduced-motion preferences and show keyboard focus.

## Verification

- TypeScript check and production web build succeeded.
- Five API tests passed, including stable identity on update, refreshed
  extraction, review invalidation, 404 handling, and validation preserving data.
- Real-browser verification: render, extraction, create/save, update/save,
  review filter, search match/no match, and email edit-panel opening.
- Desktop screenshot inspected at the actual 1205px viewport.
- Mobile screenshot inspected at 390x844; document scroll width equals 390px.
- Mobile library open/close and Escape dismissal passed; normal viewport
  restored after verification. Re-extraction correctly enables Save and
  disables Review until the new result is saved. Browser error log was empty.
- Sample content used for browser testing is synthetic. The review-button
  test is not a human approval; sample review state was reset by editing.

## Current Storage Boundary

The API still stores saved notes in process memory. Drafts live in the open
page. This UI change does not implement persistent cloud storage, Gmail OAuth,
or Bedrock calls. Those remain separate MVP work items.
