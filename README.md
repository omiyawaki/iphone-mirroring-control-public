# iPhone Mirroring Control

Shared Mac-side primitives for tools that control iOS apps through iPhone Mirroring.

The package provides:

- iPhone Mirroring window discovery and activation
- window and full-screen screenshots
- Apple Vision OCR over mirrored screenshots
- click, drag, scroll, and relative tap helpers
- visible-text clicking
- basic recovery for iPhone Mirroring connection screens
- Spotlight launching for a named iOS app

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

The Swift helpers use macOS Accessibility for input events and Screen Recording for screenshots.
Grant those permissions to the terminal, runner app, or scheduler identity that executes the tool.
