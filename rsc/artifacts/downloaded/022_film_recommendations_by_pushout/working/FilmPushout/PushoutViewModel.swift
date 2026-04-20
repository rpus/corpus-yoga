import SwiftUI
import Combine

enum ComputeState {
    case idle
    case loading
    case result(PushoutResult)
    case error(String)
}

@MainActor
class PushoutViewModel: ObservableObject {
    @Published var category: String = "Film"
    @Published var itemA: String = ""
    @Published var itemB: String = ""
    @Published var spanC: String = ""
    @Published var knownA: Bool = true
    @Published var knownB: Bool = true
    @Published var knownP: Bool = false
    @Published var state: ComputeState = .idle

    var canCompute: Bool {
        !itemA.trimmingCharacters(in: .whitespaces).isEmpty &&
        !itemB.trimmingCharacters(in: .whitespaces).isEmpty &&
        !spanC.trimmingCharacters(in: .whitespaces).isEmpty
    }

    var categoryName: String {
        category.trimmingCharacters(in: .whitespaces).isEmpty ? "Film" : category
    }

    func compute() async {
        state = .loading
        knownP = false
        do {
            let result = try await AnthropicService.computePushout(
                category: categoryName,
                itemA: itemA,
                itemB: itemB,
                spanC: spanC
            )
            withAnimation(.spring(response: 0.5, dampingFraction: 0.8)) {
                state = .result(result)
            }
            // Silent, inevitable logging
            HullLog.shared.append(HullEntry(
                category: categoryName,
                itemA: itemA, itemB: itemB, spanC: spanC,
                pushout: result.pushout_title,
                creator: result.creator, year: result.year,
                knownA: knownA, knownB: knownB, knownP: false,
                date: Date()
            ))
        } catch {
            state = .error(error.localizedDescription)
        }
    }

    func reset() {
        withAnimation(.easeOut(duration: 0.3)) {
            state = .idle
            knownP = false
        }
    }
}