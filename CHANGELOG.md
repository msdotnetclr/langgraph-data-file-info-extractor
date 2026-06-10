# Changelog

## [Unreleased] — `web-ui-v2`

### Web Application

- **React web UI** with 8 pages: Dashboard, Domains, Sessions, Extraction Progress, Review, Output Store, and more
- **Collapsible sidebar** with emoji-labeled navigation and tooltips
- **Dashboard** with live counts of domains, sources, and sessions by status

### Human-in-the-Loop Review

- **Review workflow** — approve extraction results or re-run with written feedback
- **Feedback accumulation** — repeated feedback is summarized into domain-specific instructions to improve future extractions

### Extraction

- **Live extraction progress** via real-time SSE streaming
- **Workflow visualizer** — a flow chart of the full extraction pipeline, showing which steps are active, completed, or pending; can be hidden or shown with a toggle

### Output Versioning

- **Versioned output store** — every approved extraction is saved as a numbered version
- **Version chain browser** — see how versions relate to each other
- **Diff viewer** — compare any two versions side by side for metadata, fields, and warnings

### UX Improvements

- Double-click rows to navigate into detail views
- Auto-redirect after creating domains and sessions
- One-step source setup with file upload
- Re-run failed extractions directly from the session detail page
- "Submit Feedback & Re-run" button shows "Submitting..." → "Re-processing..." → done transition
- **Identity-based field diff** — output version comparison matches fields by `(group, name)`, so index-only changes show as "reordered" (blue) instead of false remove+add
