import SwiftUI

struct ExportSheet: View {
    let csv: String
    let entryCount: Int
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            VStack(spacing: 20) {
                Spacer()

                Image(systemName: "tablecells")
                    .font(.system(size: 48))
                    .foregroundStyle(Color.teal)

                VStack(spacing: 6) {
                    Text("\(entryCount) \(entryCount == 1 ? "entry" : "entries")")
                        .font(.system(size: 22, weight: .semibold))
                    Text("hull log")
                        .font(.system(size: 15))
                        .foregroundStyle(.secondary)
                }

                ShareLink(
                    item: csv,
                    preview: SharePreview("hull_log.csv",
                                          image: Image(systemName: "tablecells"))
                ) {
                    Text("Export CSV")
                        .font(.system(size: 16, weight: .medium))
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 14)
                        .background(Color.teal)
                        .foregroundStyle(.white)
                        .clipShape(RoundedRectangle(cornerRadius: 12))
                }
                .padding(.horizontal, 32)

                Spacer()
            }
            .navigationTitle("Export")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Done") { dismiss() }
                }
            }
        }
    }
}
