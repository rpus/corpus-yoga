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
    @Published var filmA: String = ""
    @Published var filmB: String = ""
    @Published var spanC: String = ""
    @Published var state: ComputeState = .idle

    var canCompute: Bool {
        !filmA.trimmingCharacters(in: .whitespaces).isEmpty &&
        !filmB.trimmingCharacters(in: .whitespaces).isEmpty &&
        !spanC.trimmingCharacters(in: .whitespaces).isEmpty
    }

    var categoryName: String {
        category.trimmingCharacters(in: .whitespaces).isEmpty ? "Film" : category
    }

    func compute() async {
        state = .loading
        do {
            let result = try await AnthropicService.computePushout(
                category: categoryName,
                itemA: filmA,
                itemB: filmB,
                spanC: spanC
            )
            withAnimation(.spring(response: 0.5, dampingFraction: 0.8)) {
                state = .result(result)
            }
        } catch {
            state = .error(error.localizedDescription)
        }
    }

    func reset() {
        withAnimation(.easeOut(duration: 0.3)) {
            state = .idle
        }
    }
}
