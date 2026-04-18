import Foundation

// MARK: - Replace with your key
private let apiKey = "YOUR_ANTHROPIC_API_KEY"

struct PushoutResult: Codable {
    let pushout_title: String
    let year: String
    let creator: String        // generalised from "director"
    let tagline: String
    let morphism_from_A: String
    let morphism_from_B: String
    let universality: String
    let verdict: String
}

struct AnthropicService {
    static func computePushout(
        category: String,
        itemA: String,
        itemB: String,
        spanC: String
    ) async throws -> PushoutResult {

        let cat = category.lowercased()
        let prompt = """
        You are an expert critic and mathematician. The user has set up a pushout diagram in the category of \(cat)s.

        Object C (shared substructure / span): \(spanC)
        \(category) A maps from C by extending in direction: \(itemA)
        \(category) B maps from C by extending in direction: \(itemB)

        The pushout A ⊔_C B is the \(cat) that:
        1. Contains everything in A not already in C
        2. Contains everything in B not already in C
        3. Identifies the shared C-structure
        4. Is universal: any other \(cat) doing this factors uniquely through the pushout

        Respond as valid JSON only, no markdown fences, with exactly these fields:
        {
          "pushout_title": "the recommended \(cat) title",
          "year": "year of publication/release",
          "creator": "director / author / composer / artist as appropriate",
          "tagline": "one sentence: why this is the pushout",
          "morphism_from_A": "what it inherits from A (5-8 words)",
          "morphism_from_B": "what it inherits from B (5-8 words)",
          "universality": "what makes it the minimal/universal such \(cat) (5-8 words)",
          "verdict": "2-3 sentences of informed critical commentary"
        }
        """

        let body: [String: Any] = [
            "model": "claude-sonnet-4-6",
            "max_tokens": 1024,
            "messages": [
                ["role": "user", "content": prompt]
            ]
        ]

        var request = URLRequest(url: URL(string: "https://api.anthropic.com/v1/messages")!)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue(apiKey, forHTTPHeaderField: "x-api-key")
        request.setValue("2023-06-01", forHTTPHeaderField: "anthropic-version")
        request.httpBody = try JSONSerialization.data(withJSONObject: body)

        let (data, response) = try await URLSession.shared.data(for: request)

        guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
            throw URLError(.badServerResponse)
        }

        struct Envelope: Codable {
            struct Content: Codable {
                let type: String
                let text: String?
            }
            let content: [Content]
        }

        let envelope = try JSONDecoder().decode(Envelope.self, from: data)
        guard let text = envelope.content.first(where: { $0.type == "text" })?.text else {
            throw URLError(.cannotParseResponse)
        }

        let clean = text
            .trimmingCharacters(in: .whitespacesAndNewlines)
            .replacingOccurrences(of: "```json", with: "")
            .replacingOccurrences(of: "```", with: "")
            .trimmingCharacters(in: .whitespacesAndNewlines)

        guard let jsonData = clean.data(using: .utf8) else {
            throw URLError(.cannotParseResponse)
        }

        return try JSONDecoder().decode(PushoutResult.self, from: jsonData)
    }
}
