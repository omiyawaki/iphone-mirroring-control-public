import CoreGraphics
import Foundation

if CommandLine.arguments.count != 3 {
    fputs("usage: click.swift X Y\n", stderr)
    exit(64)
}

guard let x = Double(CommandLine.arguments[1]),
      let y = Double(CommandLine.arguments[2]) else {
    fputs("X and Y must be numeric coordinates\n", stderr)
    exit(64)
}

let point = CGPoint(x: x, y: y)

CGEvent(
    mouseEventSource: nil,
    mouseType: .mouseMoved,
    mouseCursorPosition: point,
    mouseButton: .left
)?.post(tap: .cghidEventTap)

usleep(50_000)

CGEvent(
    mouseEventSource: nil,
    mouseType: .leftMouseDown,
    mouseCursorPosition: point,
    mouseButton: .left
)?.post(tap: .cghidEventTap)

usleep(50_000)

CGEvent(
    mouseEventSource: nil,
    mouseType: .leftMouseUp,
    mouseCursorPosition: point,
    mouseButton: .left
)?.post(tap: .cghidEventTap)
