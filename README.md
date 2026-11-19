# iPhone Mirroring Control

Mac-side Python primitives for scripting iOS apps through macOS iPhone Mirroring.

## Why

iPhone Mirroring puts a phone on the Mac screen, but there is no API behind it.
This package wraps the pieces needed to drive it from a script: finding and
activating the window, taking screenshots, reading text on screen with Apple
Vision OCR, and sending clicks, drags and scrolls. It also recovers from the
common "iPhone is locked or unavailable" screens, so longer scripts can keep
going.

## What it provides

- iPhone Mirroring window discovery and activation
- window and full-screen screenshots
- Apple Vision OCR over mirrored screenshots
- click, drag, scroll and relative tap helpers
- clicking on visible text
- basic recovery for iPhone Mirroring connection screens
- opening a named iOS app through Spotlight

## Requirements

- macOS with iPhone Mirroring set up (macOS 15 or later) and a paired iPhone
- [Pixi](https://pixi.sh) for the Python environment (Python 3.14)
- Swift command-line tools (`swift` on your PATH), used for the input and OCR helpers
- Accessibility and Screen Recording permission for the terminal or app that runs your script

## Setup

```bash
pixi install --locked
pixi run python -c 'import iphone_mirroring_control'
```

## Usage

```python
from pathlib import Path

from iphone_mirroring_control import MacDesktopController

controller = MacDesktopController()
window = controller.find_iphone_mirroring_window()
if window is None:
    controller.open_iphone_mirroring()
else:
    controller.capture_window(window, Path("screen.png"))
```

Run `controller.diagnose()` first if something does not work. It returns a list of checks
that shows which permission or window is missing.

## Tests

```bash
pixi run pytest
```

## License

MIT. See `LICENSE`.
