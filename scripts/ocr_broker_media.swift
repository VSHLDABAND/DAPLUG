import Foundation
import Vision
import AppKit
import PDFKit

struct OCRRow: Codable {
    let path: String
    let text: String
}

func recognise(_ cgImage: CGImage) throws -> String {
    let request = VNRecognizeTextRequest()
    request.recognitionLevel = .accurate
    request.usesLanguageCorrection = true
    let handler = VNImageRequestHandler(cgImage: cgImage, options: [:])
    try handler.perform([request])
    return (request.results ?? [])
        .compactMap { $0.topCandidates(1).first?.string }
        .joined(separator: "\n")
}

func imageCG(_ url: URL) -> CGImage? {
    guard let image = NSImage(contentsOf: url) else { return nil }
    var rect = CGRect(origin: .zero, size: image.size)
    return image.cgImage(forProposedRect: &rect, context: nil, hints: nil)
}

func process(_ path: String) -> OCRRow {
    let url = URL(fileURLWithPath: path)
    do {
        if url.pathExtension.lowercased() == "pdf" {
            guard let pdf = PDFDocument(url: url) else {
                return OCRRow(path: path, text: "")
            }
            var pages: [String] = []
            for index in 0..<min(pdf.pageCount, 8) {
                guard let page = pdf.page(at: index) else { continue }
                let image = page.thumbnail(of: CGSize(width: 1800, height: 1800), for: .mediaBox)
                var rect = CGRect(origin: .zero, size: image.size)
                guard let cgImage = image.cgImage(forProposedRect: &rect, context: nil, hints: nil) else { continue }
                let text = try recognise(cgImage)
                if !text.isEmpty { pages.append(text) }
            }
            return OCRRow(path: path, text: pages.joined(separator: "\n"))
        }
        guard let cgImage = imageCG(url) else { return OCRRow(path: path, text: "") }
        return OCRRow(path: path, text: try recognise(cgImage))
    } catch {
        return OCRRow(path: path, text: "")
    }
}

let rows = CommandLine.arguments.dropFirst().map { process($0) }
let output = try JSONEncoder().encode(rows)
print(String(data: output, encoding: .utf8) ?? "[]")
