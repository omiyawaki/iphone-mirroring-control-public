import tempfile
import unittest
from pathlib import Path

from iphone_mirroring_control.automation import DesktopControlError, WindowInfo
from iphone_mirroring_control.vision import TextObservation
from iphone_mirroring_control.visual import VisualControlError, VisualDesktopSession


class FakeController:
    def __init__(self, window=None, capture_failures: int = 0) -> None:
        self.window = window
        self.capture_failures = capture_failures
        self.activated_apps: list[str] = []
        self.captured_paths: list[Path] = []
        self.clicks: list[tuple[int, int]] = []
        self.drags: list[tuple[int, int, int, int]] = []
        self.scrolls: list[tuple[int, int, int, int, int]] = []
        self.tap_drags: list[tuple[int, int, int, int, int, int, int, int, int, int]] = []
        self.pause_drag_resumes: list[tuple[int, int, int, int, int, int, int, int, int, int, int]] = []
        self.select_all_count = 0
        self.typed_text: list[str] = []

    def find_iphone_mirroring_window(self):
        return self.window

    def activate_app(self, app_name: str) -> None:
        self.activated_apps.append(app_name)

    def capture_window(self, window: WindowInfo, output_path: Path) -> Path:
        self.captured_paths.append(output_path)
        if self.capture_failures > 0:
            self.capture_failures -= 1
            raise DesktopControlError("could not create image from rect")
        return output_path

    def click(self, x: int, y: int) -> None:
        self.clicks.append((x, y))

    def drag(self, start_x: int, start_y: int, end_x: int, end_y: int) -> None:
        self.drags.append((start_x, start_y, end_x, end_y))

    def scroll(self, x: int, y: int, delta_y: int, delta_x: int = 0, repeats: int = 1) -> None:
        self.scrolls.append((x, y, delta_y, delta_x, repeats))

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
        self.tap_drags.append(
            (
                reveal_x,
                reveal_y,
                start_x,
                start_y,
                end_x,
                end_y,
                reveal_delay_ms,
                hold_ms,
                steps,
                step_delay_ms,
            )
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
        self.pause_drag_resumes.append(
            (
                play_x,
                play_y,
                start_x,
                start_y,
                end_x,
                end_y,
                pause_delay_ms,
                resume_delay_ms,
                hold_ms,
                steps,
                step_delay_ms,
            )
        )

    def select_all(self) -> None:
        self.select_all_count += 1

    def type_text(self, text: str) -> None:
        self.typed_text.append(text)


class FakeRecognizer:
    def __init__(self, observations: list[TextObservation]) -> None:
        self.observations = observations
        self.image_paths: list[Path] = []

    def recognize_observations(self, image_path: Path) -> list[TextObservation]:
        self.image_paths.append(image_path)
        return self.observations


class VisualDesktopSessionTests(unittest.TestCase):
    def test_snapshot_captures_mirrored_phone_window_and_ocr_observations(self) -> None:
        controller = FakeController(WindowInfo("iPhone Mirroring", "Home", 74, 30, 340, 750))
        recognizer = FakeRecognizer([
            TextObservation("Track", 200, 400, 40, 20, image_width=680, image_height=1500)
        ])
        session = VisualDesktopSession(controller, recognizer)

        snapshot = session.snapshot()

        self.assertEqual(snapshot.window, controller.window)
        self.assertEqual(snapshot.observations, recognizer.observations)
        self.assertEqual(controller.activated_apps, ["iPhone Mirroring"])
        self.assertEqual(len(controller.captured_paths), 1)
        self.assertEqual(recognizer.image_paths, controller.captured_paths)

    def test_snapshot_retries_window_capture_after_transient_capture_failure(self) -> None:
        controller = FakeController(
            WindowInfo("iPhone Mirroring", "Home", 74, 30, 340, 750),
            capture_failures=1,
        )
        recognizer = FakeRecognizer([
            TextObservation("Track", 200, 400, 40, 20, image_width=680, image_height=1500)
        ])
        session = VisualDesktopSession(controller, recognizer, pause=lambda _: None)

        snapshot = session.snapshot()

        self.assertEqual(snapshot.observations, recognizer.observations)
        self.assertEqual(controller.activated_apps, ["iPhone Mirroring", "iPhone Mirroring"])
        self.assertEqual(len(controller.captured_paths), 2)

    def test_click_text_clicks_center_of_matching_observation_in_desktop_coordinates(self) -> None:
        controller = FakeController(WindowInfo("iPhone Mirroring", "Home", 74, 30, 340, 750))
        recognizer = FakeRecognizer([
            TextObservation("Track", 200, 400, 40, 20, image_width=680, image_height=1500)
        ])
        session = VisualDesktopSession(controller, recognizer)

        clicked = session.click_text("track")

        self.assertEqual(clicked, (184, 235))
        self.assertEqual(controller.clicks, [(184, 235)])

    def test_click_text_can_choose_later_occurrence(self) -> None:
        controller = FakeController(WindowInfo("iPhone Mirroring", "Home", 74, 30, 340, 750))
        recognizer = FakeRecognizer([
            TextObservation("Track", 100, 200, 40, 20, image_width=680, image_height=1500),
            TextObservation("Track", 200, 400, 40, 20, image_width=680, image_height=1500),
        ])
        session = VisualDesktopSession(controller, recognizer)

        clicked = session.click_text("Track", occurrence=2)

        self.assertEqual(clicked, (184, 235))
        self.assertEqual(controller.clicks, [(184, 235)])

    def test_click_text_occurrence_uses_reading_order_even_when_vision_output_is_unsorted(self) -> None:
        controller = FakeController(WindowInfo("iPhone Mirroring", "Home", 74, 30, 340, 750))
        recognizer = FakeRecognizer([
            TextObservation("Track", 200, 400, 40, 20, image_width=680, image_height=1500),
            TextObservation("Track", 100, 200, 40, 20, image_width=680, image_height=1500),
        ])
        session = VisualDesktopSession(controller, recognizer)

        clicked = session.click_text("Track", occurrence=1)

        self.assertEqual(clicked, (134, 135))
        self.assertEqual(controller.clicks, [(134, 135)])

    def test_click_text_matches_ios_chevron_back_label_when_ascii_label_is_requested(self) -> None:
        controller = FakeController(WindowInfo("iPhone Mirroring", "Home", 74, 30, 340, 750))
        recognizer = FakeRecognizer([
            TextObservation("‹ Stats", 100, 200, 80, 20, image_width=680, image_height=1500),
        ])
        session = VisualDesktopSession(controller, recognizer)

        clicked = session.click_text("< Stats")

        self.assertEqual(clicked, (144, 135))
        self.assertEqual(controller.clicks, [(144, 135)])

    def test_click_text_matches_compact_back_label_when_spaced_label_is_requested(self) -> None:
        controller = FakeController(WindowInfo("iPhone Mirroring", "Home", 74, 30, 340, 750))
        recognizer = FakeRecognizer([
            TextObservation("<Stats", 100, 200, 80, 20, image_width=680, image_height=1500),
        ])
        session = VisualDesktopSession(controller, recognizer)

        clicked = session.click_text("< Stats")

        self.assertEqual(clicked, (144, 135))
        self.assertEqual(controller.clicks, [(144, 135)])

    def test_snapshot_requires_iphone_mirroring_window(self) -> None:
        session = VisualDesktopSession(FakeController(window=None), FakeRecognizer([]))

        with self.assertRaisesRegex(VisualControlError, "iPhone Mirroring window not found"):
            session.snapshot()

    def test_visible_text_returns_desktop_centers_in_reading_order(self) -> None:
        controller = FakeController(WindowInfo("iPhone Mirroring", "Home", 74, 30, 340, 750))
        recognizer = FakeRecognizer([
            TextObservation("Steps", 40, 300, 80, 24, image_width=680, image_height=1500),
            TextObservation("Track", 200, 200, 40, 20, image_width=680, image_height=1500),
        ])
        session = VisualDesktopSession(controller, recognizer)

        visible_text = session.visible_text()

        self.assertEqual(
            [(item.text, item.x, item.y) for item in visible_text],
            [("Track", 184, 135), ("Steps", 114, 186)],
        )

    def test_drag_relative_uses_current_window_bounds(self) -> None:
        controller = FakeController(WindowInfo("iPhone Mirroring", "Home", 100, 200, 400, 800))
        session = VisualDesktopSession(controller, FakeRecognizer([]))

        dragged = session.drag_relative(0.25, 0.50, 0.75, 0.25)

        self.assertEqual(dragged, (200, 600, 400, 400))
        self.assertEqual(controller.drags, [(200, 600, 400, 400)])

    def test_scroll_relative_uses_current_window_bounds(self) -> None:
        controller = FakeController(WindowInfo("iPhone Mirroring", "Home", 100, 200, 400, 800))
        session = VisualDesktopSession(controller, FakeRecognizer([]))

        scrolled = session.scroll_relative(0.50, 0.70, -10, repeats=18)

        self.assertEqual(scrolled, (300, 760))
        self.assertEqual(controller.scrolls, [(300, 760, -10, 0, 18)])

    def test_tap_relative_uses_current_window_bounds(self) -> None:
        controller = FakeController(WindowInfo("iPhone Mirroring", "Home", 74, 30, 340, 750))
        session = VisualDesktopSession(controller, FakeRecognizer([]))

        tapped = session.tap_relative(0.500, 0.307)

        self.assertEqual(tapped, (244, 260))
        self.assertEqual(controller.activated_apps, ["iPhone Mirroring"])
        self.assertEqual(controller.clicks, [(244, 260)])

    def test_reveal_and_drag_relative_uses_single_transient_control_gesture(self) -> None:
        controller = FakeController(WindowInfo("iPhone Mirroring", "Home", 74, 30, 340, 750))
        session = VisualDesktopSession(controller, FakeRecognizer([]))

        dragged = session.reveal_and_drag_relative(
            0.500,
            0.307,
            0.224,
            0.365,
            0.714,
            0.365,
            reveal_delay_ms=120,
            hold_ms=100,
            steps=44,
            step_delay_ms=18,
        )

        self.assertEqual(dragged, (244, 260, 150, 304, 317, 304))
        self.assertEqual(controller.activated_apps, ["iPhone Mirroring"])
        self.assertEqual(
            controller.tap_drags,
            [(244, 260, 150, 304, 317, 304, 120, 100, 44, 18)],
        )

    def test_pause_drag_resume_relative_uses_single_media_gesture(self) -> None:
        controller = FakeController(WindowInfo("iPhone Mirroring", "Home", 74, 30, 340, 750))
        session = VisualDesktopSession(controller, FakeRecognizer([]))

        dragged = session.pause_drag_resume_relative(
            0.500,
            0.307,
            0.224,
            0.365,
            0.714,
            0.365,
            pause_delay_ms=180,
            resume_delay_ms=300,
            hold_ms=100,
            steps=44,
            step_delay_ms=18,
        )

        self.assertEqual(dragged, (244, 260, 150, 304, 317, 304))
        self.assertEqual(controller.activated_apps, ["iPhone Mirroring"])
        self.assertEqual(
            controller.pause_drag_resumes,
            [(244, 260, 150, 304, 317, 304, 180, 300, 100, 44, 18)],
        )

    def test_pause_drag_relative_leaves_media_paused_after_drag(self) -> None:
        controller = FakeController(WindowInfo("iPhone Mirroring", "Home", 74, 30, 340, 750))
        pauses: list[float] = []
        session = VisualDesktopSession(controller, FakeRecognizer([]), pause=pauses.append)

        dragged = session.pause_drag_relative(
            0.500,
            0.307,
            0.224,
            0.365,
            0.714,
            0.365,
            pause_delay_ms=180,
        )

        self.assertEqual(dragged, (244, 260, 150, 304, 317, 304))
        self.assertEqual(controller.activated_apps, ["iPhone Mirroring"])
        self.assertEqual(controller.clicks, [(244, 260)])
        self.assertEqual(controller.drags, [(150, 304, 317, 304)])
        self.assertEqual(pauses, [0.18])

    def test_click_text_reports_missing_text(self) -> None:
        controller = FakeController(WindowInfo("iPhone Mirroring", "Home", 74, 30, 340, 750))
        session = VisualDesktopSession(controller, FakeRecognizer([]))

        with self.assertRaisesRegex(VisualControlError, "Visible text not found: Save"):
            session.click_text("Save")

    def test_click_field_value_below_label_chooses_nearest_lower_observation(self) -> None:
        controller = FakeController(WindowInfo("iPhone Mirroring", "Home", 74, 30, 340, 750))
        recognizer = FakeRecognizer([
            TextObservation("Time", 46, 366, 68, 26, image_width=680, image_height=1500),
            TextObservation("30 minutes", 61, 426, 133, 29, image_width=680, image_height=1500),
            TextObservation("Cannot exceed 480 total minutes", 46, 484, 300, 26, image_width=680, image_height=1500),
        ])
        session = VisualDesktopSession(controller, recognizer)

        clicked = session.click_field_value_below_label("Time")

        self.assertEqual(clicked, (138, 250))
        self.assertEqual(controller.clicks, [(138, 250)])

    def test_click_below_label_uses_label_center_with_vertical_offset(self) -> None:
        controller = FakeController(WindowInfo("iPhone Mirroring", "Home", 74, 30, 340, 750))
        recognizer = FakeRecognizer([
            TextObservation("Steps", 45, 332, 79, 30, image_width=680, image_height=1500),
        ])
        session = VisualDesktopSession(controller, recognizer)

        clicked = session.click_below_label("Steps", y_offset=30)

        self.assertEqual(clicked, (116, 234))
        self.assertEqual(controller.clicks, [(116, 234)])

    def test_replace_field_value_below_label_selects_and_types(self) -> None:
        controller = FakeController(WindowInfo("iPhone Mirroring", "Home", 74, 30, 340, 750))
        recognizer = FakeRecognizer([
            TextObservation("Steps", 45, 555, 79, 30, image_width=680, image_height=1500),
            TextObservation("3000", 59, 615, 70, 26, image_width=680, image_height=1500),
        ])
        session = VisualDesktopSession(controller, recognizer)

        clicked = session.replace_field_value_below_label("Steps", "20000")

        self.assertEqual(clicked, (121, 344))
        self.assertEqual(controller.clicks, [(121, 344)])
        self.assertEqual(controller.select_all_count, 1)
        self.assertEqual(controller.typed_text, ["20000"])

    def test_click_field_value_below_label_reports_missing_label(self) -> None:
        controller = FakeController(WindowInfo("iPhone Mirroring", "Home", 74, 30, 340, 750))
        session = VisualDesktopSession(controller, FakeRecognizer([]))

        with self.assertRaisesRegex(VisualControlError, "Visible label not found: Time"):
            session.click_field_value_below_label("Time")

    def test_click_field_value_below_label_reports_missing_value(self) -> None:
        controller = FakeController(WindowInfo("iPhone Mirroring", "Home", 74, 30, 340, 750))
        recognizer = FakeRecognizer([
            TextObservation("Time", 46, 366, 68, 26, image_width=680, image_height=1500),
        ])
        session = VisualDesktopSession(controller, recognizer)

        with self.assertRaisesRegex(VisualControlError, "Visible value below label not found: Time"):
            session.click_field_value_below_label("Time")


if __name__ == "__main__":
    unittest.main()
