from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, Iterable

from iphone_mirroring_control.visual import PhoneUnavailableError, VisibleText, VisualControlError


CONNECT_RETRY_ATTEMPTS = 3


@dataclass(frozen=True)
class MirroringRecoveryResult:
    screen: str
    actions: list[str]


def classify_mirroring_screen(lines: Iterable[str]) -> str:
    normalized = {_normalize(line) for line in lines}
    joined = " ".join(sorted(normalized))
    if "iphone not found" in joined:
        return "iphone_mirroring_unavailable"
    if "iphone in use" in joined:
        return "iphone_mirroring_in_use"
    if "timed out" in joined and "connect" in normalized:
        return "iphone_mirroring_timeout"
    if "resume" in normalized and (
        "iphone mirroring" in joined or "connection paused" in joined or "mirroring paused" in joined
    ):
        return "iphone_mirroring_paused"
    if "connecting" in normalized or "connecting..." in normalized:
        return "iphone_mirroring_connecting"
    if "search" in normalized and ("app library" in joined or "home" in normalized):
        return "iphone_home"
    return "app"


class IPhoneMirroringRecovery:
    def __init__(
        self,
        session,
        controller,
        pause: Callable[[float], None] = time.sleep,
    ) -> None:
        self._session = session
        self._controller = controller
        self._pause = pause

    def visible_text(self) -> list[VisibleText]:
        return self._session.visible_text()

    def ensure_window(self) -> list[str]:
        actions: list[str] = []
        window = self._controller.find_iphone_mirroring_window()
        if window is not None:
            return actions
        open_iphone_mirroring = getattr(self._controller, "open_iphone_mirroring", None)
        if not callable(open_iphone_mirroring):
            raise PhoneUnavailableError("iPhone Mirroring window not found")
        open_iphone_mirroring()
        self._pause(2.0)
        actions.append("Opened iPhone Mirroring because no window was found")
        if self._controller.find_iphone_mirroring_window() is None:
            raise PhoneUnavailableError("iPhone Mirroring window not found")
        return actions

    def recover_connection(self, max_attempts: int = 8) -> MirroringRecoveryResult:
        actions = self.ensure_window()
        unavailable_retry_attempts = 0
        attempted_in_use_connect = False
        connecting_seen = False

        for _ in range(max_attempts):
            visible_text = self.visible_text()
            screen = classify_mirroring_screen(item.text for item in visible_text)
            if screen in {"app", "iphone_home"}:
                return MirroringRecoveryResult(screen=screen, actions=actions)

            if screen == "iphone_mirroring_timeout":
                connect_text = first_visible_text(visible_text, {"connect"})
                if connect_text is not None:
                    self._session.click_text(connect_text)
                    self._pause(8.0)
                    actions.append("Tapped Connect on iPhone Mirroring timeout")
                    continue

            if screen == "iphone_mirroring_connecting":
                connecting_seen = True
                self._pause(8.0)
                actions.append("Waited for iPhone Mirroring connection to settle")
                continue

            if screen == "iphone_mirroring_paused":
                resume_text = first_visible_text(visible_text, {"resume"})
                if resume_text is not None:
                    try:
                        self._session.click_text(resume_text)
                    except VisualControlError as exc:
                        if f"Visible text not found: {resume_text}" not in str(exc):
                            raise
                    self._pause(8.0)
                    actions.append("Tapped Resume on iPhone Mirroring paused screen")
                    continue

            if screen == "iphone_mirroring_in_use":
                connect_text = first_visible_text(visible_text, {"connect"})
                if connect_text is not None and not attempted_in_use_connect:
                    attempted_in_use_connect = True
                    self._session.click_text(connect_text)
                    self._pause(8.0)
                    actions.append("Tapped Connect on iPhone Mirroring iPhone in use screen")
                    continue
                raise PhoneUnavailableError(
                    "iPhone Mirroring ended because iPhone is in use; lock iPhone to connect"
                )

            if screen == "iphone_mirroring_unavailable":
                try_again_text = first_visible_text(visible_text, {"try again"})
                if try_again_text is not None and unavailable_retry_attempts < CONNECT_RETRY_ATTEMPTS:
                    unavailable_retry_attempts += 1
                    self._session.click_text(try_again_text)
                    self._pause(8.0)
                    actions.append("Tapped Try Again on iPhone Mirroring unavailable screen")
                    continue
                raise PhoneUnavailableError("iPhone Mirroring reports iPhone Not Found")

            break

        if connecting_seen:
            raise PhoneUnavailableError("iPhone Mirroring did not finish connecting")
        raise VisualControlError("Could not recover iPhone Mirroring from the visible screen")

    def open_ios_app_from_spotlight(self, app_name: str) -> list[str]:
        actions: list[str] = []
        self._controller.choose_iphone_view_menu_item("Spotlight")
        self._pause(0.8)
        actions.append("Opened iPhone Spotlight")
        self._controller.type_text(app_name)
        self._pause(0.8)
        actions.append(f"Searched Spotlight for {app_name}")
        result_labels = {item.text.strip().casefold() for item in self.visible_text()}
        if "app store" in result_labels and "install" in result_labels:
            raise VisualControlError(f"{app_name} app was not found in iPhone Spotlight")
        try:
            self._session.click_text(app_name)
        except VisualControlError:
            self._controller.press_key("return")
        self._pause(1.5)
        actions.append(f"Opened {app_name} from Spotlight")
        return actions


def first_visible_text(visible_text: Iterable[VisibleText], candidates: set[str]) -> str | None:
    wanted = {candidate.casefold() for candidate in candidates}
    for item in visible_text:
        if item.text.strip().casefold() in wanted:
            return item.text
    return None


def _normalize(text: str) -> str:
    return " ".join(text.strip().casefold().split())
