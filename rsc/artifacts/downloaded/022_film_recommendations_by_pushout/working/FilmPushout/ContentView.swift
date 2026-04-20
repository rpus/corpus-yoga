import SwiftUI

struct ContentView: View {
    @StateObject private var vm = PushoutViewModel()
    @StateObject private var log = HullLog.shared
    @FocusState private var focusedField: Field?
    @State private var showingExport = false

    enum Field { case category, c, a, b }

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 0) {

                    // Editable category name
                    HStack(spacing: 6) {
                        TextField("Film", text: $vm.category)
                            .font(.system(size: 15, weight: .medium))
                            .multilineTextAlignment(.center)
                            .focused($focusedField, equals: .category)
                            .frame(maxWidth: 140)
                            .padding(.vertical, 6)
                            .padding(.horizontal, 10)
                            .background(Color(.secondarySystemBackground))
                            .clipShape(RoundedRectangle(cornerRadius: 8))
                        Text("Pushout")
                            .font(.system(size: 15, weight: .regular))
                            .foregroundStyle(.secondary)
                    }
                    .padding(.top, 8)

                    diagramView
                        .padding(.top, 16)

                    // Compute button
                    Button {
                        focusedField = nil
                        Task { await vm.compute() }
                    } label: {
                        HStack {
                            if case .loading = vm.state {
                                ProgressView().tint(.white)
                            }
                            Text(buttonLabel)
                                .font(.system(size: 16, weight: .medium))
                        }
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 14)
                        .background(vm.canCompute ? Color.teal : Color(.systemGray4))
                        .foregroundStyle(.white)
                        .clipShape(RoundedRectangle(cornerRadius: 12))
                    }
                    .disabled(!vm.canCompute || isLoading)
                    .padding(.horizontal, 24)
                    .padding(.top, 24)
                    .animation(.easeInOut(duration: 0.2), value: vm.canCompute)

                    // Error
                    if case .error(let msg) = vm.state {
                        Text(msg)
                            .font(.system(size: 13))
                            .foregroundStyle(.red)
                            .padding(.horizontal, 24)
                            .padding(.top, 12)
                    }

                    // Verdict card
                    if case .result(let r) = vm.state {
                        VerdictCard(result: r, category: vm.categoryName)
                            .padding(.top, 28)
                            .transition(.move(edge: .bottom).combined(with: .opacity))

                        Button("Reset") { vm.reset() }
                            .font(.system(size: 14))
                            .foregroundStyle(.secondary)
                            .padding(.top, 16)
                    }

                    Spacer(minLength: 40)
                }
            }
            .navigationTitle("Pushout")
            .navigationBarTitleDisplayMode(.inline)
            .scrollDismissesKeyboard(.interactively)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    if !log.entries.isEmpty {
                        Button {
                            showingExport = true
                        } label: {
                            Image(systemName: "square.and.arrow.up")
                                .font(.system(size: 14))
                        }
                    }
                }
            }
            .sheet(isPresented: $showingExport) {
                ExportSheet(csv: log.csvString, entryCount: log.entries.count)
            }
        }
    }

    // MARK: - Diagram

    private var diagramView: some View {
        GeometryReader { geo in
            let w = geo.size.width
            let cX  = w * 0.5,  cY:  CGFloat = 80
            let aX  = w * 0.18, aY:  CGFloat = 230
            let bX  = w * 0.82, bY:  CGFloat = 230
            let pX  = w * 0.5,  pY:  CGFloat = 380

            ZStack {
                ArrowLayer(geometry: geo, result: resolvedResult)

                if let r = resolvedResult {
                    ArrowCaption(text: r.morphism_from_A,
                                 from: CGPoint(x: cX, y: cY),
                                 to:   CGPoint(x: aX, y: aY),
                                 offset: -30)
                    ArrowCaption(text: r.morphism_from_B,
                                 from: CGPoint(x: cX, y: cY),
                                 to:   CGPoint(x: bX, y: bY),
                                 offset: 30)
                    ArrowCaption(text: r.universality,
                                 from: CGPoint(x: aX, y: aY),
                                 to:   CGPoint(x: pX, y: pY),
                                 offset: -30)
                }

                // C node (no known toggle)
                NodeView(role: .spanC, text: $vm.spanC,
                         label: "C — shared substructure",
                         categoryName: vm.categoryName,
                         known: .constant(false))
                    .focused($focusedField, equals: .c)
                    .position(x: cX, y: cY)

                // A node
                NodeView(role: .filmA, text: $vm.itemA,
                         label: "A",
                         categoryName: vm.categoryName,
                         known: $vm.knownA)
                    .focused($focusedField, equals: .a)
                    .position(x: aX, y: aY)

                // B node
                NodeView(role: .filmB, text: $vm.itemB,
                         label: "B",
                         categoryName: vm.categoryName,
                         known: $vm.knownB)
                    .focused($focusedField, equals: .b)
                    .position(x: bX, y: bY)

                // Pushout node
                NodeView(
                    role: .pushout,
                    text: .constant(resolvedResult?.pushout_title ?? ""),
                    label: "A ⊔_C B",
                    sublabel: resolvedResult.map { "\($0.creator), \($0.year)" },
                    isResolved: resolvedResult != nil,
                    isLoading: isLoading,
                    categoryName: vm.categoryName,
                    known: $vm.knownP
                )
                .position(x: pX, y: pY)
            }
        }
        .frame(height: 460)
    }

    // MARK: - Helpers

    private var resolvedResult: PushoutResult? {
        if case .result(let r) = vm.state { return r }
        return nil
    }

    private var isLoading: Bool {
        if case .loading = vm.state { return true }
        return false
    }

    private var buttonLabel: String {
        if case .loading = vm.state { return "Computing…" }
        if case .result  = vm.state { return "Recompute" }
        return "Compute pushout"
    }
}

#Preview {
    ContentView()
}