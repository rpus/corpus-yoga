import SwiftUI

struct VerdictCard: View {
    let result: PushoutResult

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {

            // Header
            VStack(alignment: .leading, spacing: 4) {
                Text("\(result.pushout_title) (\(result.year))")
                    .font(.system(size: 18, weight: .semibold))
                    .foregroundStyle(.primary)
                Text("dir. \(result.director)")
                    .font(.system(size: 13))
                    .foregroundStyle(.secondary)
                Text(result.tagline)
                    .font(.system(size: 13, weight: .regular))
                    .foregroundStyle(.secondary)
                    .italic()
                    .padding(.top, 2)
            }

            Divider()

            // Morphism pills
            VStack(spacing: 8) {
                MorphismPill(label: "from A", text: result.morphism_from_A, color: .purple)
                MorphismPill(label: "from B", text: result.morphism_from_B, color: .orange)
                MorphismPill(label: "universal because", text: result.universality, color: .teal)
            }

            Divider()

            // Verdict
            Text(result.verdict)
                .font(.system(size: 14))
                .foregroundStyle(.primary)
                .lineSpacing(4)
        }
        .padding(20)
        .background(Color(.secondarySystemBackground))
        .clipShape(RoundedRectangle(cornerRadius: 16))
        .overlay(
            RoundedRectangle(cornerRadius: 16)
                .stroke(Color.teal.opacity(0.3), lineWidth: 0.8)
        )
        .padding(.horizontal, 20)
    }
}

struct MorphismPill: View {
    let label: String
    let text: String
    let color: Color

    var body: some View {
        HStack(alignment: .top, spacing: 8) {
            Text(label)
                .font(.system(size: 10, weight: .medium))
                .foregroundStyle(color)
                .textCase(.uppercase)
                .tracking(0.6)
                .frame(width: 90, alignment: .trailing)
            Text(text)
                .font(.system(size: 13))
                .foregroundStyle(.primary)
                .frame(maxWidth: .infinity, alignment: .leading)
        }
    }
}
