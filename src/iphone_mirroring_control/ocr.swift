import AppKit
import Foundation
import Vision

let jsonMode = CommandLine.arguments.count == 3 && CommandLine.arguments[1] == "--json"
let imagePathArgument: String

if jsonMode {
    imagePathArgument = CommandLine.arguments[2]
} else if CommandLine.arguments.count == 2 {
    imagePathArgument = CommandLine.arguments[1]
} else {
    fputs("usage: ocr.swift [--json] IMAGE_PATH\n", stderr)
    exit(64)
}

let imageURL = URL(fileURLWithPath: imagePathArgument)
guard let image = NSImage(contentsOf: imageURL) else {
    fputs("could not open image: \(imageURL.path)\n", stderr)
    exit(66)
}

guard let cgImage = image.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
    fputs("could not create CGImage from: \(imageURL.path)\n", stderr)
    exit(65)
}

let request = VNRecognizeTextRequest()
request.recognitionLevel = .accurate
request.usesLanguageCorrection = false

let handler = VNImageRequestHandler(cgImage: cgImage, options: [:])

do {
    try handler.perform([request])
} catch {
    fputs("text recognition failed: \(error)\n", stderr)
    exit(1)
}

let observations = request.results ?? []
for observation in observations {
    guard let candidate = observation.topCandidates(1).first else {
        continue
    }
    if jsonMode {
        let bounds = observation.boundingBox
        let imageWidth = Double(cgImage.width)
        let imageHeight = Double(cgImage.height)
        let payload: [String: Any] = [
            "text": candidate.string,
            "x": Int((Double(bounds.minX) * imageWidth).rounded()),
            "y": Int(((1.0 - Double(bounds.maxY)) * imageHeight).rounded()),
            "width": Int((Double(bounds.width) * imageWidth).rounded()),
            "height": Int((Double(bounds.height) * imageHeight).rounded()),
            "image_width": cgImage.width,
            "image_height": cgImage.height
        ]
        if let data = try? JSONSerialization.data(withJSONObject: payload, options: []),
           let line = String(data: data, encoding: .utf8) {
            print(line)
        }
    } else {
        print(candidate.string)
    }
}
