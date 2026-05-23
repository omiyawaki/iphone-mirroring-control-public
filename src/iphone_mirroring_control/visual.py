from __future__ import annotations

import time
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from iphone_mirroring_control.automation import DesktopControlError, MacDesktopController, WindowInfo
from iphone_mirroring_control.vision import AppleVisionTextRecognizer, TextObservation


class VisualControlError(RuntimeError):
    pass


class PhoneUnavailableError(VisualControlError):
    pass


@dataclass(frozen=True)
class VisualSnapshot:
    window: WindowInfo
    observations: list[TextObservation]


@dataclass(frozen=True)
class VisibleText:
    text: str
    x: int
    y: int


class VisualDesktopSession:
    def __init__(
        self,
        controller: MacDesktopController,
        text_recognizer: AppleVisionTextRecognizer,
        pause: Callable[[float], None] = time.sleep,
        capture_attempts: int = 2,
    ) -> None:
        if capture_attempts <= 0:
            raise ValueError("capture_attempts must be greater than 0")
        self._controller = controller
        self._text_recognizer = text_recognizer
        self._pause = pause
        self._capture_attempts = capture_attempts

    def snapshot(self) -> VisualSnapshot:
        last_error: DesktopControlError | None = None
        for attempt in range(self._capture_attempts):
            window = self._controller.find_iphone_mirroring_window()
            if window is None:
                raise VisualControlError("iPhone Mirroring window not found")

            self._controller.activate_app(window.app_name)
            with tempfile.TemporaryDirectory() as tmpdir:
                try:
                    screenshot_path = self._controller.capture_window(window, Path(tmpdir) / "iphone.png")
                except DesktopControlError as exc:
                    last_error = exc
                    if attempt + 1 >= self._capture_attempts:
                        break
                    self._pause(1.0)
                    continue
                observations = self._text_recognizer.recognize_observations(screenshot_path)
                return VisualSnapshot(window=window, observations=observations)

        raise VisualControlError(
            f"Could not capture iPhone Mirroring window after {self._capture_attempts} attempts: {last_error}"
        )

    def visible_text(self) -> list[VisibleText]:
        snapshot = self.snapshot()
        items = []
        for observation in snapshot.observations:
            x, y = observation.desktop_center(
                window_x=snapshot.window.x,
                window_y=snapshot.window.y,
                window_width=snapshot.window.width,
                window_height=snapshot.window.height,
            )
            items.append(VisibleText(text=observation.text, x=x, y=y))
        return sorted(items, key=lambda item: (item.y, item.x, item.text.casefold()))

    def click_text(self, text: str, occurrence: int = 1) -> tuple[int, int]:
        if occurrence < 1:
            raise ValueError("occurrence must be greater than or equal to 1")

        snapshot = self.snapshot()
        matches = []
        for observation in snapshot.observations:
            if _click_text_key(observation.text) != _click_text_key(text):
                continue
            x, y = observation.desktop_center(
                window_x=snapshot.window.x,
                window_y=snapshot.window.y,
                window_width=snapshot.window.width,
                window_height=snapshot.window.height,
            )
            matches.append((y, x, observation.text.casefold(), x, y))
        if len(matches) < occurrence:
            raise VisualControlError(f"Visible text not found: {text}")

        _, _, _, x, y = sorted(matches)[occurrence - 1]
        self._controller.click(x, y)
        return (x, y)

    def drag_relative(
        self,
        start_x_fraction: float,
        start_y_fraction: float,
        end_x_fraction: float,
        end_y_fraction: float,
    ) -> tuple[int, int, int, int]:
        window = self._controller.find_iphone_mirroring_window()
        if window is None:
            raise VisualControlError("iPhone Mirroring window not found")

        self._controller.activate_app(window.app_name)
        start_x = window.x + round(window.width * start_x_fraction)
        start_y = window.y + round(window.height * start_y_fraction)
        end_x = window.x + round(window.width * end_x_fraction)
        end_y = window.y + round(window.height * end_y_fraction)
        self._controller.drag(start_x, start_y, end_x, end_y)
        return (start_x, start_y, end_x, end_y)

    def scroll_relative(
        self,
        x_fraction: float,
        y_fraction: float,
        delta_y: int,
        delta_x: int = 0,
        repeats: int = 1,
    ) -> tuple[int, int]:
        window = self._controller.find_iphone_mirroring_window()
        if window is None:
            raise VisualControlError("iPhone Mirroring window not found")

        self._controller.activate_app(window.app_name)
        x = window.x + round(window.width * x_fraction)
        y = window.y + round(window.height * y_fraction)
        self._controller.scroll(x, y, delta_y, delta_x=delta_x, repeats=repeats)
        return (x, y)

    def tap_relative(
        self,
        x_fraction: float,
        y_fraction: float,
    ) -> tuple[int, int]:
        window = self._controller.find_iphone_mirroring_window()
        if window is None:
            raise VisualControlError("iPhone Mirroring window not found")

        self._controller.activate_app(window.app_name)
        x = window.x + round(window.width * x_fraction)
        y = window.y + round(window.height * y_fraction)
        self._controller.click(x, y)
        return (x, y)

    def drag_points(self, start_x: int, start_y: int, end_x: int, end_y: int) -> tuple[int, int, int, int]:
        window = self._controller.find_iphone_mirroring_window()
        if window is None:
            raise VisualControlError("iPhone Mirroring window not found")

        self._controller.activate_app(window.app_name)
        self._controller.drag(start_x, start_y, end_x, end_y)
        return (start_x, start_y, end_x, end_y)

    def reveal_and_drag_relative(
        self,
        reveal_x_fraction: float,
        reveal_y_fraction: float,
        start_x_fraction: float,
        start_y_fraction: float,
        end_x_fraction: float,
        end_y_fraction: float,
        reveal_delay_ms: int = 120,
        hold_ms: int = 80,
        steps: int = 40,
        step_delay_ms: int = 20,
    ) -> tuple[int, int, int, int, int, int]:
        window = self._controller.find_iphone_mirroring_window()
        if window is None:
            raise VisualControlError("iPhone Mirroring window not found")

        self._controller.activate_app(window.app_name)
        reveal_x = window.x + round(window.width * reveal_x_fraction)
        reveal_y = window.y + round(window.height * reveal_y_fraction)
        start_x = window.x + round(window.width * start_x_fraction)
        start_y = window.y + round(window.height * start_y_fraction)
        end_x = window.x + round(window.width * end_x_fraction)
        end_y = window.y + round(window.height * end_y_fraction)
        self._controller.tap_then_drag(
            reveal_x,
            reveal_y,
            start_x,
            start_y,
            end_x,
            end_y,
            reveal_delay_ms=reveal_delay_ms,
            hold_ms=hold_ms,
            steps=steps,
            step_delay_ms=step_delay_ms,
        )
        return (reveal_x, reveal_y, start_x, start_y, end_x, end_y)

    def pause_drag_resume_relative(
        self,
        play_x_fraction: float,
        play_y_fraction: float,
        start_x_fraction: float,
        start_y_fraction: float,
        end_x_fraction: float,
        end_y_fraction: float,
        pause_delay_ms: int = 180,
        resume_delay_ms: int = 300,
        hold_ms: int = 80,
        steps: int = 40,
        step_delay_ms: int = 20,
    ) -> tuple[int, int, int, int, int, int]:
        window = self._controller.find_iphone_mirroring_window()
        if window is None:
            raise VisualControlError("iPhone Mirroring window not found")

        self._controller.activate_app(window.app_name)
        play_x = window.x + round(window.width * play_x_fraction)
        play_y = window.y + round(window.height * play_y_fraction)
        start_x = window.x + round(window.width * start_x_fraction)
        start_y = window.y + round(window.height * start_y_fraction)
        end_x = window.x + round(window.width * end_x_fraction)
        end_y = window.y + round(window.height * end_y_fraction)
        self._controller.pause_drag_resume(
            play_x,
            play_y,
            start_x,
            start_y,
            end_x,
            end_y,
            pause_delay_ms=pause_delay_ms,
            resume_delay_ms=resume_delay_ms,
            hold_ms=hold_ms,
            steps=steps,
            step_delay_ms=step_delay_ms,
        )
        return (play_x, play_y, start_x, start_y, end_x, end_y)

    def pause_drag_relative(
        self,
        play_x_fraction: float,
        play_y_fraction: float,
        start_x_fraction: float,
        start_y_fraction: float,
        end_x_fraction: float,
        end_y_fraction: float,
        pause_delay_ms: int = 180,
    ) -> tuple[int, int, int, int, int, int]:
        window = self._controller.find_iphone_mirroring_window()
        if window is None:
            raise VisualControlError("iPhone Mirroring window not found")

        self._controller.activate_app(window.app_name)
        play_x = window.x + round(window.width * play_x_fraction)
        play_y = window.y + round(window.height * play_y_fraction)
        start_x = window.x + round(window.width * start_x_fraction)
        start_y = window.y + round(window.height * start_y_fraction)
        end_x = window.x + round(window.width * end_x_fraction)
        end_y = window.y + round(window.height * end_y_fraction)
        self._controller.click(play_x, play_y)
        self._pause(pause_delay_ms / 1000)
        self._controller.drag(start_x, start_y, end_x, end_y)
        return (play_x, play_y, start_x, start_y, end_x, end_y)

    def click_field_value_below_label(self, label: str) -> tuple[int, int]:
        snapshot = self.snapshot()
        label_observation = _first_exact_text(snapshot.observations, label)
        if label_observation is None:
            raise VisualControlError(f"Visible label not found: {label}")

        value_observation = _nearest_value_below_label(snapshot.observations, label_observation)
        if value_observation is None:
            raise VisualControlError(f"Visible value below label not found: {label}")

        x, y = value_observation.desktop_center(
            window_x=snapshot.window.x,
            window_y=snapshot.window.y,
            window_width=snapshot.window.width,
            window_height=snapshot.window.height,
        )
        self._controller.click(x, y)
        return (x, y)

    def click_below_label(self, label: str, y_offset: int) -> tuple[int, int]:
        snapshot = self.snapshot()
        label_observation = _first_exact_text(snapshot.observations, label)
        if label_observation is None:
            raise VisualControlError(f"Visible label not found: {label}")

        x, y = label_observation.desktop_center(
            window_x=snapshot.window.x,
            window_y=snapshot.window.y,
            window_width=snapshot.window.width,
            window_height=snapshot.window.height,
        )
        click_point = (x, y + y_offset)
        self._controller.click(*click_point)
        return click_point

    def replace_field_value_below_label(self, label: str, text: str) -> tuple[int, int]:
        clicked = self.click_field_value_below_label(label)
        self._controller.select_all()
        self._controller.type_text(text)
        return clicked


def _first_exact_text(
    observations: list[TextObservation],
    text: str,
) -> TextObservation | None:
    expected = text.casefold()
    for observation in observations:
        if observation.text.casefold() == expected:
            return observation
    return None


def _click_text_key(text: str) -> str:
    normalized = text.casefold().replace("‹", "<").strip()
    if normalized.startswith("<"):
        return normalized.replace(" ", "")
    return normalized


def _nearest_value_below_label(
    observations: list[TextObservation],
    label: TextObservation,
) -> TextObservation | None:
    lower_observations = [
        observation
        for observation in observations
        if observation.y > label.y and observation.text != label.text
    ]
    if not lower_observations:
        return None
    return min(lower_observations, key=lambda observation: (observation.y - label.y, abs(observation.x - label.x)))
