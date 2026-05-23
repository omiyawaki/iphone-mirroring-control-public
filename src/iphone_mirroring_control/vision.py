from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional


Runner = Callable[[list[str]], subprocess.CompletedProcess]


class VisionError(RuntimeError):
    pass


@dataclass(frozen=True)
class TextObservation:
    text: str
    x: int
    y: int
    width: int
    height: int
    image_width: Optional[int] = None
    image_height: Optional[int] = None

    @classmethod
    def from_dict(cls, data: dict) -> "TextObservation":
        return cls(
            text=str(data["text"]),
            x=int(data["x"]),
            y=int(data["y"]),
            width=int(data["width"]),
            height=int(data["height"]),
            image_width=int(data["image_width"]) if "image_width" in data else None,
            image_height=int(data["image_height"]) if "image_height" in data else None,
        )

    @property
    def center(self) -> tuple[int, int]:
        return (self.x + round(self.width / 2), self.y + round(self.height / 2))

    def desktop_center(
        self,
        window_x: int,
        window_y: int,
        window_width: int,
        window_height: int,
    ) -> tuple[int, int]:
        if self.image_width is None or self.image_height is None:
            raise ValueError("image dimensions are required to convert OCR pixels to desktop coordinates")
        center_x, center_y = self.center
        scale_x = self.image_width / window_width
        scale_y = self.image_height / window_height
        return (
            window_x + int(round(center_x / scale_x)),
            window_y + int(round(center_y / scale_y)),
        )


class AppleVisionTextRecognizer:
    def __init__(
        self,
        runner: Optional[Runner] = None,
        script_path: Optional[Path] = None,
    ) -> None:
        self._runner = runner or self._run
        self._script_path = script_path or Path(__file__).with_name("ocr.swift")

    def recognize_text(self, image_path: Path) -> list[str]:
        result = self._runner(["swift", str(self._script_path), str(image_path)])
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "Apple Vision OCR failed.").strip()
            raise VisionError(detail)
        return [line.strip() for line in result.stdout.splitlines() if line.strip()]

    def recognize_observations(self, image_path: Path) -> list[TextObservation]:
        result = self._runner(["swift", str(self._script_path), "--json", str(image_path)])
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "Apple Vision OCR failed.").strip()
            raise VisionError(detail)
        observations: list[TextObservation] = []
        for line in result.stdout.splitlines():
            if not line.strip():
                continue
            observations.append(TextObservation.from_dict(json.loads(line)))
        return observations

    @staticmethod
    def _run(command: list[str]) -> subprocess.CompletedProcess:
        return subprocess.run(command, capture_output=True, text=True)


def extract_current_steps(lines: list[str]) -> Optional[int]:
    for index, line in enumerate(lines):
        if _is_exact_steps_label(line):
            nearby_numbers = _nearby_numbers(lines, index)
            if nearby_numbers:
                return nearby_numbers[0]

    for line in lines:
        if _is_step_metric_line(line):
            number = _first_number(line)
            if number is not None:
                return number

    return None


def find_text_observation(
    observations: list[TextObservation],
    text: str,
) -> Optional[TextObservation]:
    expected = text.casefold()
    for observation in observations:
        if observation.text.casefold() == expected:
            return observation
    return None


def _is_exact_steps_label(line: str) -> bool:
    return line.strip().lower() == "steps"


def _is_step_metric_line(line: str) -> bool:
    normalized = line.strip().lower()
    if "steps" not in normalized:
        return False
    if _is_non_current_metric_line(line):
        return False
    return _first_number(line) is not None


def _nearby_numbers(lines: list[str], index: int) -> list[int]:
    numbers: list[int] = []
    for offset in (-1, 1, -2, 2):
        neighbor_index = index + offset
        if neighbor_index < 0 or neighbor_index >= len(lines):
            continue
        line = lines[neighbor_index]
        if _is_non_current_metric_line(line):
            continue
        number = _first_number(line)
        if number is not None:
            numbers.append(number)
    return numbers


def _is_non_current_metric_line(line: str) -> bool:
    normalized = line.strip().lower()
    return (
        normalized.startswith("take ")
        or " in a day" in normalized
        or normalized.startswith("daily goal")
    )


def _first_number(line: str) -> Optional[int]:
    match = re.search(r"\b\d[\d,]*\b", line)
    if match is None:
        return None
    return int(match.group(0).replace(",", ""))
