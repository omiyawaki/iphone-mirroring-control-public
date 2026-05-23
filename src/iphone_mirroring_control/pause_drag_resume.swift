import CoreGraphics
import Foundation

if CommandLine.arguments.count != 12 {
    fputs(
        "usage: pause_drag_resume.swift PLAY_X PLAY_Y START_X START_Y END_X END_Y PAUSE_DELAY_MS RESUME_DELAY_MS HOLD_MS STEPS STEP_DELAY_MS\n",
        stderr
    )
    exit(64)
}

guard let playX = Double(CommandLine.arguments[1]),
      let playY = Double(CommandLine.arguments[2]),
      let startX = Double(CommandLine.arguments[3]),
      let startY = Double(CommandLine.arguments[4]),
      let endX = Double(CommandLine.arguments[5]),
      let endY = Double(CommandLine.arguments[6]),
      let pauseDelayMs = UInt32(CommandLine.arguments[7]),
      let resumeDelayMs = UInt32(CommandLine.arguments[8]),
      let holdMs = UInt32(CommandLine.arguments[9]),
      let steps = Int(CommandLine.arguments[10]),
      let stepDelayMs = UInt32(CommandLine.arguments[11]),
      steps > 0 else {
    fputs("coordinates and timing values must be numeric, and STEPS must be positive\n", stderr)
    exit(64)
}

let source = CGEventSource(stateID: .hidSystemState)
let play = CGPoint(x: playX, y: playY)
let start = CGPoint(x: startX, y: startY)
let end = CGPoint(x: endX, y: endY)

func postMouse(_ type: CGEventType, at point: CGPoint) {
    CGEvent(
        mouseEventSource: source,
        mouseType: type,
        mouseCursorPosition: point,
        mouseButton: .left
    )?.post(tap: .cghidEventTap)
}

func click(_ point: CGPoint) {
    postMouse(.mouseMoved, at: point)
    usleep(30_000)
    postMouse(.leftMouseDown, at: point)
    usleep(40_000)
    postMouse(.leftMouseUp, at: point)
}

click(play)
usleep(pauseDelayMs * 1_000)

postMouse(.mouseMoved, at: start)
usleep(30_000)
postMouse(.leftMouseDown, at: start)
usleep(holdMs * 1_000)

for step in 1...steps {
    let progress = Double(step) / Double(steps)
    let point = CGPoint(
        x: start.x + (end.x - start.x) * progress,
        y: start.y + (end.y - start.y) * progress
    )
    postMouse(.leftMouseDragged, at: point)
    usleep(stepDelayMs * 1_000)
}

postMouse(.leftMouseUp, at: end)
usleep(resumeDelayMs * 1_000)
click(play)
