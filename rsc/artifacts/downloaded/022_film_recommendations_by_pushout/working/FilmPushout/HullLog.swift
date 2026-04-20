import Foundation

struct HullEntry {
    let category: String
    let itemA: String
    let itemB: String
    let spanC: String
    let pushout: String
    let creator: String
    let year: String
    let knownA: Bool
    let knownB: Bool
    let knownP: Bool
    let date: Date
}

class HullLog: ObservableObject {
    static let shared = HullLog()
    @Published private(set) var entries: [HullEntry] = []

    private let key = "hull_log_v1"

    init() { load() }

    func append(_ entry: HullEntry) {
        entries.append(entry)
        save()
    }

    // MARK: - CSV

    var csvString: String {
        let schema = "date,category,itemA,knownA,itemB,knownB,spanC,pushout,creator,year,knownP"
        let rows = entries.map { e in
            [
                iso(e.date), e.category,
                escaped(e.itemA), e.knownA ? "1" : "0",
                escaped(e.itemB), e.knownB ? "1" : "0",
                escaped(e.spanC),
                escaped(e.pushout), escaped(e.creator), e.year,
                e.knownP ? "1" : "0"
            ].joined(separator: ",")
        }
        return ([schema] + rows).joined(separator: "\n")
    }

    private func escaped(_ s: String) -> String {
        let needs = s.contains(",") || s.contains("\"") || s.contains("\n")
        if needs { return "\"" + s.replacingOccurrences(of: "\"", with: "\"\"") + "\"" }
        return s
    }

    private func iso(_ d: Date) -> String {
        ISO8601DateFormatter().string(from: d)
    }

    // MARK: - Persistence (simple JSON via UserDefaults)

    private func save() {
        let raw = entries.map { e -> [String: Any] in
            ["category": e.category, "itemA": e.itemA, "itemB": e.itemB,
             "spanC": e.spanC, "pushout": e.pushout, "creator": e.creator,
             "year": e.year, "knownA": e.knownA, "knownB": e.knownB,
             "knownP": e.knownP, "date": e.date.timeIntervalSince1970]
        }
        UserDefaults.standard.set(raw, forKey: key)
    }

    private func load() {
        guard let raw = UserDefaults.standard.array(forKey: key) as? [[String: Any]] else { return }
        entries = raw.compactMap { d in
            guard let cat  = d["category"] as? String,
                  let a    = d["itemA"]    as? String,
                  let b    = d["itemB"]    as? String,
                  let c    = d["spanC"]    as? String,
                  let p    = d["pushout"]  as? String,
                  let cr   = d["creator"]  as? String,
                  let yr   = d["year"]     as? String,
                  let ka   = d["knownA"]   as? Bool,
                  let kb   = d["knownB"]   as? Bool,
                  let kp   = d["knownP"]   as? Bool,
                  let ts   = d["date"]     as? Double
            else { return nil }
            return HullEntry(category: cat, itemA: a, itemB: b, spanC: c,
                             pushout: p, creator: cr, year: yr,
                             knownA: ka, knownB: kb, knownP: kp,
                             date: Date(timeIntervalSince1970: ts))
        }
    }
}