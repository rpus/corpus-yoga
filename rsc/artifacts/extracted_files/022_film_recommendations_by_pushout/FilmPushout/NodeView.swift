import SwiftUI

enum NodeRole {
    case spanC, filmA, filmB, pushout
}

struct NodeView: View {
    let role: NodeRole
    @Binding var text: String
    var label: String
    var sublabel: String? = nil
    var isResolved: Bool = false
    var isLoading: Bool = false

    private var accentColor: Color {
        switch role {
        case .spanC:   return Color(.systemGray4)
        case .filmA:   return Color.purple.opacity(0.8)
        case .filmB:   return Color.orange.opacity(0.8)
        case .pushout: return Color.teal
        }
    }

    private var bgColor: Color {
        switch role {
        case .spanC:   return Color(.systemGray6)
        case .filmA:   return Color.purple.opacity(0.07)
        case .filmB:   return Color.orange.opacity(0.07)
        case .pushout: return isResolved ? Color.teal.opacity(0.1) : Color(.systemGray6).opacity(0.5)
        }
    }

    var body: some View {
        VStack(spacing: 4) {
            Text(label)
                .font(.system(size: 10, weight: .medium))
                .foregroundStyle(accentColor)
                .textCase(.uppercase)
                .tracking(0.8)

            if role == .pushout {
                pushoutContent
            } else {
                inputContent
            }
        }
        .padding(12)
        .frame(width: nodeWidth, minHeight: 80)
        .background(bgColor)
        .clipShape(RoundedRectangle(cornerRadius: 12))
        .overlay(
            RoundedRectangle(cornerRadius: 12)
                .stroke(accentColor.opacity(role == .pushout && isResolved ? 0.9 : 0.3),
                        lineWidth: role == .pushout && isResolved ? 1.5 : 0.8)
        )
    }

    private var nodeWidth: CGFloat {
        switch role {
        case .spanC:   return 180
        case .filmA:   return 155
        case .filmB:   return 155
        case .pushout: return 200
        }
    }

    @ViewBuilder
    private var inputContent: some View {
        if role == .spanC {
            TextField("shared substructure…", text: $text, axis: .vertical)
                .font(.system(size: 13))
                .lineLimit(2...4)
                .multilineTextAlignment(.center)
                .foregroundStyle(.primary)
        } else {
            TextField("film title…", text: $text)
                .font(.system(size: 13, weight: .medium))
                .multilineTextAlignment(.center)
                .foregroundStyle(.primary)
        }
    }

    @ViewBuilder
    private var pushoutContent: some View {
        if isLoading {
            ProgressView()
                .tint(.teal)
                .padding(.vertical, 8)
        } else if !text.isEmpty {
            Text(text)
                .font(.system(size: 14, weight: .semibold))
                .multilineTextAlignment(.center)
                .foregroundStyle(Color.teal)
            if let sub = sublabel {
                Text(sub)
                    .font(.system(size: 11))
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
            }
        } else {
            Text("A ⊔_C B")
                .font(.system(size: 18, weight: .light))
                .foregroundStyle(Color(.systemGray4))
                .padding(.vertical, 4)
        }
    }
}
