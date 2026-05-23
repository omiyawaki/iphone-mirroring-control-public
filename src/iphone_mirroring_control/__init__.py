"""Reusable control primitives for iPhone Mirroring automation."""

from iphone_mirroring_control.automation import DesktopControlError, MacDesktopController, WindowInfo
from iphone_mirroring_control.recovery import (
    IPhoneMirroringRecovery,
    MirroringRecoveryResult,
    classify_mirroring_screen,
)
from iphone_mirroring_control.visual import PhoneUnavailableError, VisualControlError, VisualDesktopSession

__all__ = [
    "DesktopControlError",
    "IPhoneMirroringRecovery",
    "MacDesktopController",
    "MirroringRecoveryResult",
    "PhoneUnavailableError",
    "VisualControlError",
    "VisualDesktopSession",
    "WindowInfo",
    "classify_mirroring_screen",
]
