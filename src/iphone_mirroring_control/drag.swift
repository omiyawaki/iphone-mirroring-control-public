import CoreGraphics
import Foundation

if CommandLine.arguments.count != 5 {
    fputs("usage: drag.swift START_X START_Y END_X END_Y\n", stderr)
    exit(64)
}

guard let startX = Double(CommandLine.arguments[1]),
      let startY = Double(CommandLine.arguments[2]),
      let endX = Double(CommandLine.arguments[3]),
      let endY = Double(CommandLine.arguments[4]) else {
    fputs("coordinates must be numeric\n", stderr)
    exit(64)
}

let start = CGPoint(x: startX, y: startY)
let end = CGPoint(x: endX, y: endY)

CGEvent(
    mouseEventSource: nil,
    mouseType: .mouseMoved,
    mouseCursorPosition: start,
    mouseButton: .left
)?.post(tap: .cghidEventTap)

usleep(50_000)

CGEvent(
    mouseEventSource: nil,
    mouseType: .leftMouseDown,
    mouseCursorPosition: start,
    mouseButton: .left
)?.post(tap: .cghidEventTap)

let steps = 16
for step in 1...steps {
    let progress = Double(step) / Double(steps)
    let point = CGPoint(
        x: start.x + (end.x - start.x) * progress,
        y: start.y + (end.y - start.y) * progress
    )
    CGEvent(
        mouseEventSource: nil,
        mouseType: .leftMouseDragged,
        mouseCursorPosition: point,
        mouseButton: .left
    )?.post(tap: .cghidEventTap)
    usleep(15_000)
}

CGEvent(
    mouseEventSource: nil,
    mouseType: .leftMouseUp,
    mouseCursorPosition: end,
    mouseButton: .left
)?.post(tap: .cghidEventTap)
