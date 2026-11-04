# Post-beta acceptance matrix

## Must pass

- Home loads real vault data without technical identifiers.
- Every visible control has a deterministic action or is styled as informational.
- Course navigation preserves course context and separates own notes from official resources.
- Source viewer renders Markdown, tables, code, Obsidian image embeds, and LaTeX.
- Missing resources show an explicit unavailable state; no random redirects.
- User-owned note editing requires explicit save and never touches official sources.
- Study session start, attempt, feedback, calibration, review, PHS validation, and completion are resumable.
- API errors produce a visible Spanish explanation and recovery action.
- TypeScript build and Python test suite pass.
- No secrets, tokens, cookies, or personal paths are published by the UI.

## Nice-to-have after release

- Rich editor toolbar.
- PDF/DOCX page-aware viewer.
- Offline cache.
- Desktop plugin integration.

## Release gate

The release is not post-beta until every Must pass item has an automated or reproducible manual check recorded in the QA report.
