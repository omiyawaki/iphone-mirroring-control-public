from __future__ import annotations

import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional


Runner = Callable[[list[str]], subprocess.CompletedProcess]


@dataclass(frozen=True)
class WindowInfo:
    app_name: str
    title: str
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0


@dataclass(frozen=True)
class DesktopDiagnostic:
    name: str
    ok: bool
    detail: str
    recovery: str


class DesktopControlError(RuntimeError):
    pass


class MacDesktopController:
    def __init__(
        self,
        runner: Optional[Runner] = None,
        click_script_path: Optional[Path] = None,
        drag_script_path: Optional[Path] = None,
        scroll_script_path: Optional[Path] = None,
        tap_drag_script_path: Optional[Path] = None,
        pause_drag_resume_script_path: Optional[Path] = None,
    ) -> None:
        self._runner = runner or self._run
        self._click_script_path = click_script_path or Path(__file__).with_name("click.swift")
        self._drag_script_path = drag_script_path or Path(__file__).with_name("drag.swift")
        self._scroll_script_path = scroll_script_path or Path(__file__).with_name("scroll.swift")
        self._tap_drag_script_path = tap_drag_script_path or Path(__file__).with_name("tap_drag.swift")
        self._pause_drag_resume_script_path = pause_drag_resume_script_path or Path(__file__).with_name(
            "pause_drag_resume.swift"
        )

    def list_windows(self) -> list[WindowInfo]:
        script = """
        tell application "System Events"
            set output to ""
            repeat with proc in application processes
                try
                    repeat with win in windows of proc
                        set winPosition to position of win
                        set winSize to size of win
                        set output to output & name of proc & tab & name of win & tab & ¬
                            item 1 of winPosition & tab & item 2 of winPosition & tab & ¬
                            item 1 of winSize & tab & item 2 of winSize & linefeed
                    end repeat
                end try
            end repeat
            return output
        end tell
        """
        result = self._runner(["osascript", "-e", script])
        return _parse_window_output(result.stdout)

    def find_iphone_mirroring_window(self) -> Optional[WindowInfo]:
        script = """
        tell application "System Events"
            with timeout of 10 seconds
                if not (exists process "iPhone Mirroring") then return ""
                tell process "iPhone Mirroring"
                    set output to ""
                    repeat with win in windows
                        try
                            set winPosition to position of win
                            set winSize to size of win
                            set output to output & "iPhone Mirroring" & tab & name of win & tab & ¬
                                item 1 of winPosition & tab & item 2 of winPosition & tab & ¬
                                item 1 of winSize & tab & item 2 of winSize & linefeed
                        end try
                    end repeat
                    return output
                end tell
            end timeout
        end tell
        """
        result = self._runner(["osascript", "-e", script])
        candidates = [
            window
            for window in _parse_window_output(result.stdout)
            if window.app_name.lower() == "iphone mirroring"
        ]
        preferred = [
            window
            for window in candidates
            if "settings" not in window.title.casefold() and window.height > window.width
        ]
        if preferred:
            return preferred[0]
        non_settings = [
            window for window in candidates if "settings" not in window.title.casefold()
        ]
        if non_settings:
            return non_settings[0]
        if candidates:
            return candidates[0]
        return None

    def diagnose(self) -> list[DesktopDiagnostic]:
        diagnostics = [self._diagnose_system_events_access()]
        if diagnostics[0].ok:
            diagnostics.append(self._diagnose_iphone_mirroring_window())
        else:
            diagnostics.append(
                DesktopDiagnostic(
                    name="iPhone Mirroring window",
                    ok=False,
                    detail="Window check skipped because System Events is unavailable.",
                    recovery="Fix System Events or Accessibility access first, then rerun desktop doctor.",
                )
            )
        diagnostics.append(self._diagnose_screen_capture())
        return diagnostics

    def capture_screen(self, output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        self._runner(["screencapture", "-x", str(output_path)])
        return output_path

    def capture_window(self, window: WindowInfo, output_path: Path) -> Path:
        if window.width <= 0 or window.height <= 0:
            raise DesktopControlError(
                (
                    "invalid iPhone Mirroring capture region: "
                    f"{window.x},{window.y},{window.width},{window.height}"
                )
            )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        region = f"{window.x},{window.y},{window.width},{window.height}"
        try:
            self._runner(["screencapture", "-x", "-R", region, str(output_path)])
        except DesktopControlError as exc:
            raise DesktopControlError(
                f"could not capture iPhone Mirroring window region {region}: {exc}"
            ) from exc
        return output_path

    def activate_app(self, app_name: str) -> None:
        escaped_app_name = app_name.replace("\\", "\\\\").replace('"', '\\"')
        self._runner(["osascript", "-e", f'tell application "{escaped_app_name}" to activate'])

    def open_iphone_mirroring(self) -> None:
        self._runner(["open", "-a", "iPhone Mirroring"])

    def choose_iphone_view_menu_item(self, menu_item: str) -> None:
        escaped_menu_item = menu_item.replace("\\", "\\\\").replace('"', '\\"')
        script = f"""
        tell application "iPhone Mirroring" to activate
        tell application "System Events"
            tell process "iPhone Mirroring"
                click menu item "{escaped_menu_item}" of menu 1 of menu bar item "View" of menu bar 1
            end tell
        end tell
        """
        self._runner(["osascript", "-e", script])

    def click(self, x: int, y: int) -> None:
        self._runner(["swift", str(self._click_script_path), str(x), str(y)])

    def drag(self, start_x: int, start_y: int, end_x: int, end_y: int) -> None:
        self._runner(
            [
                "swift",
                str(self._drag_script_path),
                str(start_x),
                str(start_y),
                str(end_x),
                str(end_y),
            ]
        )

    def scroll(self, x: int, y: int, delta_y: int, delta_x: int = 0, repeats: int = 1) -> None:
        self._runner(
            [
                "swift",
                str(self._scroll_script_path),
                str(x),
                str(y),
                str(delta_y),
                str(delta_x),
                str(repeats),
            ]
        )

    def tap_then_drag(
        self,
        reveal_x: int,
        reveal_y: int,
        start_x: int,
        start_y: int,
        end_x: int,
        end_y: int,
        reveal_delay_ms: int = 120,
        hold_ms: int = 80,
        steps: int = 40,
        step_delay_ms: int = 20,
    ) -> None:
        self._runner(
            [
                "swift",
                str(self._tap_drag_script_path),
                str(reveal_x),
                str(reveal_y),
                str(start_x),
                str(start_y),
                str(end_x),
                str(end_y),
                str(reveal_delay_ms),
                str(hold_ms),
                str(steps),
                str(step_delay_ms),
            ]
        )

    def pause_drag_resume(
        self,
        play_x: int,
        play_y: int,
        start_x: int,
        start_y: int,
        end_x: int,
        end_y: int,
        pause_delay_ms: int = 180,
        resume_delay_ms: int = 300,
        hold_ms: int = 80,
        steps: int = 40,
        step_delay_ms: int = 20,
    ) -> None:
        self._runner(
            [
                "swift",
                str(self._pause_drag_resume_script_path),
                str(play_x),
                str(play_y),
                str(start_x),
                str(start_y),
                str(end_x),
                str(end_y),
                str(pause_delay_ms),
                str(resume_delay_ms),
                str(hold_ms),
                str(steps),
                str(step_delay_ms),
            ]
        )

    def type_text(self, text: str) -> None:
        escaped_text = text.replace("\\", "\\\\").replace('"', '\\"')
        self._runner(["osascript", "-e", f'tell application "System Events" to keystroke "{escaped_text}"'])

    def select_all(self) -> None:
        self._runner(["osascript", "-e", 'tell application "System Events" to keystroke "a" using command down'])

    def press_key(self, key: str) -> None:
        key_codes = {"return": 36, "tab": 48, "escape": 53}
        if key not in key_codes:
            raise ValueError(f"unsupported key: {key}")
        self._runner(["osascript", "-e", f'tell application "System Events" to key code {key_codes[key]}'])

    def _diagnose_system_events_access(self) -> DesktopDiagnostic:
        try:
            result = self._runner(
                ["osascript", "-e", 'tell application "System Events" to return UI elements enabled']
            )
        except DesktopControlError as exc:
            return DesktopDiagnostic(
                name="System Events access",
                ok=False,
                detail=str(exc),
                recovery="Grant Accessibility permission to the terminal or host app, then retry.",
            )
        if result.returncode != 0:
            return DesktopDiagnostic(
                name="System Events access",
                ok=False,
                detail=(result.stderr or result.stdout or "System Events returned a non-zero exit code.").strip(),
                recovery="Grant Accessibility permission to the terminal or host app, then retry.",
            )
        enabled = result.stdout.strip().lower()
        if enabled != "true":
            return DesktopDiagnostic(
                name="System Events access",
                ok=False,
                detail=f"UI elements enabled returned {result.stdout.strip()!r}.",
                recovery="Enable Accessibility access before running click or typing automation.",
            )
        return DesktopDiagnostic(
            name="System Events access",
            ok=True,
            detail="System Events UI scripting is available.",
            recovery="No action needed.",
        )

    def _diagnose_iphone_mirroring_window(self) -> DesktopDiagnostic:
        try:
            window = self.find_iphone_mirroring_window()
        except DesktopControlError as exc:
            return DesktopDiagnostic(
                name="iPhone Mirroring window",
                ok=False,
                detail=str(exc),
                recovery=_desktop_control_recovery(str(exc)),
            )
        if window is None:
            return DesktopDiagnostic(
                name="iPhone Mirroring window",
                ok=False,
                detail="No iPhone Mirroring window was found.",
                recovery="Open iPhone Mirroring and navigate to the target iPhone app before retrying.",
            )
        return DesktopDiagnostic(
            name="iPhone Mirroring window",
            ok=True,
            detail=f"Found window titled {window.title!r}.",
            recovery="No action needed.",
        )

    def _diagnose_screen_capture(self) -> DesktopDiagnostic:
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                self.capture_screen(Path(tmpdir) / "iphone-mirroring-control-doctor.png")
        except DesktopControlError as exc:
            return DesktopDiagnostic(
                name="Screen capture",
                ok=False,
                detail=str(exc),
                recovery=(
                    "Grant Screen Recording permission to the terminal or host app, "
                    "then rerun desktop doctor."
                ),
            )
        return DesktopDiagnostic(
            name="Screen capture",
            ok=True,
            detail="A test screenshot was captured.",
            recovery="No action needed.",
        )

    @staticmethod
    def _run(command: list[str]) -> subprocess.CompletedProcess:
        try:
            return subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as exc:
            raise DesktopControlError(exc.stderr.strip() or str(exc)) from exc


def _parse_window_output(output: str) -> list[WindowInfo]:
    windows: list[WindowInfo] = []
    for raw_line in output.splitlines():
        if not raw_line.strip() or "\t" not in raw_line:
            continue
        parts = raw_line.split("\t")
        if len(parts) >= 6:
            app_name, title, x, y, width, height = parts[:6]
            windows.append(
                WindowInfo(
                    app_name=app_name.strip(),
                    title=title.strip(),
                    x=int(x),
                    y=int(y),
                    width=int(width),
                    height=int(height),
                )
            )
        elif len(parts) == 2:
            app_name, title = parts
            windows.append(WindowInfo(app_name=app_name.strip(), title=title.strip()))
    return windows


def _desktop_control_recovery(detail: str) -> str:
    if "-25211" in detail or "assistive access" in detail.lower():
        return "Grant Accessibility permission to the terminal, host app, and osascript if macOS lists it, then retry."
    return "Open iPhone Mirroring and keep the phone unlocked, then retry."
