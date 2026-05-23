from iphone_mirroring_control.recovery import IPhoneMirroringRecovery, classify_mirroring_screen, first_visible_text
from iphone_mirroring_control.visual import VisibleText


class FakeController:
    def __init__(self):
        self.window = None
        self.open_count = 0

    def find_iphone_mirroring_window(self):
        return self.window

    def open_iphone_mirroring(self):
        self.open_count += 1
        self.window = object()


class FakeSession:
    def visible_text(self):
        return []


def test_classify_paused_mirroring_screen():
    assert classify_mirroring_screen(["iPhone Mirroring", "Resume"]) == "iphone_mirroring_paused"


def test_classify_unavailable_screen():
    assert classify_mirroring_screen(["iPhone Not Found", "Try Again"]) == "iphone_mirroring_unavailable"


def test_classify_home_screen():
    assert classify_mirroring_screen(["Search", "App Library", "Home"]) == "iphone_home"


def test_first_visible_text_matches_case_insensitively():
    visible = [VisibleText(" Resume ", 10, 20)]

    assert first_visible_text(visible, {"resume"}) == " Resume "


def test_ensure_window_opens_iphone_mirroring_when_missing():
    controller = FakeController()
    recovery = IPhoneMirroringRecovery(FakeSession(), controller, pause=lambda _: None)

    assert recovery.ensure_window() == ["Opened iPhone Mirroring because no window was found"]
    assert controller.open_count == 1
