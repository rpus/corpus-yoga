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
    var categoryName: String = "Film"
    @Binding var known: Bool

    private var accentColor: Color {
        switch role {
        case .spanC:   return Color(.systemGray4)
        case .filmA:   return known ? Color.green.opacity(0.9)  : Color.red.opacity(0.7)
        case .filmB:   return known ? Color.green.opacity(0.9)  : Color.red.opacity(0.7)
        case .pushout: return known ? Color.green.opacity(0.9)  : Color.teal
        }
    }

    private var bgColor: Color {
        switch role {
        case .spanC:   return Color(.systemGray6)
        case .filmA:   return known ? Color.green.opacity(0.07) : Color.red.opacity(0.05)
        case .filmB:   return known ? Color.green.opacity(0.07) : Color.red.opacity(0.05)
        case .pushout:
            if known    { return Color.green.opacity(0.07) }
            if isResolved { return Color.teal.opacity(0.1) }
            return Color(.systemGray6).opacity(0.5)
        }
    }

    var body: some View {
        ZStack(alignment: .topTrailing) {
            VStack(spacing: 4) {
                Text(label)
                    .font(.system(size: 10, weight: .medium))
                    .foregroundStyle(role == .spanC ? Color(.systemGray4) : accentColor)
                    .textCase(.uppercase)
                    .tracking(0.8)

                if role == .pushout {
                    pushoutContent
                } else {
                    inputContent
                }
            }
            .padding(12)
            .frame(width: nodeWidth)
            .frame(minHeight: 80)
            .background(bgColor)
            .clipShape(RoundedRectangle(cornerRadius: 12))
            .overlay(
                RoundedRectangle(cornerRadius: 12)
                    .stroke(accentColor.opacity(0.4), lineWidth: role == .pushout && isResolved ? 1.5 : 0.8)
            )

            // "known" toggle — only on A, B, and resolved pushout
            if role != .spanC && (role != .pushout || isResolved) {
                Button {
                    withAnimation(.easeInOut(duration: 0.2)) { known.toggle() }
                } label: {
                    Text("known")
                        .font(.system(size: 9, weight: .medium))
                        .tracking(0.4)
                        .padding(.horizontal, 6)
                        .padding(.vertical, 3)
                        .background(known ? Color.green.opacity(0.2) : Color(.systemGray5))
                        .foregroundStyle(known ? Color.green : Color(.systemGray2))
                        .clipShape(Capsule())
                }
                .padding(6)
            }
        }
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
            TextField("\(categoryName.lowercased()) title…", text: $text)
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
                .foregroundStyle(known ? Color.green : Color.teal)
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