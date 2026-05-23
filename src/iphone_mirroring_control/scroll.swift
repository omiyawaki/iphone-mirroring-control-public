import CoreGraphics
import Foundation

if CommandLine.arguments.count != 6 {
    fputs("usage: scroll.swift X Y DELTA_Y DELTA_X REPEATS\n", stderr)
    exit(64)
}

guard let x = Double(CommandLine.arguments[1]),
      let y = Double(CommandLine.arguments[2]),
      let deltaY = Int32(CommandLine.arguments[3]),
      let deltaX = Int32(CommandLine.arguments[4]),
      let repeats = Int(CommandLine.arguments[5]),
      repeats > 0 else {
    fputs("coordinates, deltas, and repeat count must be numeric; repeats must be positive\n", stderr)
    exit(64)
}

let source = CGEventSource(stateID: .hidSystemState)
let point = CGPoint(x: x, y: y)

CGEvent(
    mouseEventSource: source,
    mouseType: .mouseMoved,
    mouseCursorPosition: point,
    mouseButton: .left
)?.post(tap: .cghidEventTap)

usleep(50_000)

for _ in 0..<repeats {
    CGEvent(
        scrollWheelEvent2Source: source,
        units: .line,
        wheelCount: 2,
        wheel1: deltaY,
        wheel2: deltaX,
        wheel3: 0
    )?.post(tap: .cghidEventTap)
    usleep(40_000)
}
