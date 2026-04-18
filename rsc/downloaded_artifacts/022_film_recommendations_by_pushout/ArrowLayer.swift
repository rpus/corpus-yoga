import SwiftUI

struct ArrowLayer: View {
    let geometry: GeometryProxy
    let result: PushoutResult?

    // Node centres (fractional coordinates of the diamond)
    // C: top centre, A: mid left, B: mid right, P: bottom centre
    var cCentre:  CGPoint { CGPoint(x: geometry.size.width * 0.5,  y: 80) }
    var aCentre:  CGPoint { CGPoint(x: geometry.size.width * 0.18, y: 230) }
    var bCentre:  CGPoint { CGPoint(x: geometry.size.width * 0.82, y: 230) }
    var pCentre:  CGPoint { CGPoint(x: geometry.size.width * 0.5,  y: 380) }

    var body: some View {
        Canvas { ctx, size in
            let nodeRadius: CGFloat = 10

            func draw(from: CGPoint, to: CGPoint, dashed: Bool) {
                let dx = to.x - from.x
                let dy = to.y - from.y
                let len = sqrt(dx*dx + dy*dy)
                guard len > 0 else { return }
                let ux = dx / len, uy = dy / len

                let start = CGPoint(x: from.x + ux * nodeRadius, y: from.y + uy * nodeRadius)
                let end   = CGPoint(x: to.x   - ux * (nodeRadius + 10), y: to.y - uy * (nodeRadius + 10))

                var path = Path()
                path.move(to: start)
                path.addLine(to: end)

                // arrowhead
                let arrowLen: CGFloat = 10
                let arrowAngle: CGFloat = 0.4
                let ax1 = CGPoint(
                    x: end.x - arrowLen * (ux * cos(arrowAngle) - uy * sin(arrowAngle)),
                    y: end.y - arrowLen * (uy * cos(arrowAngle) + ux * sin(arrowAngle))
                )
                let ax2 = CGPoint(
                    x: end.x - arrowLen * (ux * cos(-arrowAngle) - uy * sin(-arrowAngle)),
                    y: end.y - arrowLen * (uy * cos(-arrowAngle) + ux * sin(-arrowAngle))
                )
                path.move(to: end); path.addLine(to: ax1)
                path.move(to: end); path.addLine(to: ax2)

                var stroke = ctx.environment.displayScale > 0
                    ? GraphicsContext.Shading.color(.secondary)
                    : GraphicsContext.Shading.color(.secondary)

                if dashed {
                    stroke = GraphicsContext.Shading.color(Color("AccentTeal", bundle: nil).opacity(0.9))
                    ctx.stroke(path, with: stroke, style: StrokeStyle(lineWidth: 1.5, dash: [5, 4]))
                } else {
                    ctx.stroke(path, with: GraphicsContext.Shading.color(.secondary.opacity(0.7)),
                               style: StrokeStyle(lineWidth: 1.2))
                }
            }

            // Span arrows C→A, C→B (solid)
            draw(from: cCentre, to: aCentre, dashed: false)
            draw(from: cCentre, to: bCentre, dashed: false)

            // Pushout arrows A→P, B→P (dashed, teal)
            draw(from: aCentre, to: pCentre, dashed: true)
            draw(from: bCentre, to: pCentre, dashed: true)

            // Pushout corner mark (small L at P top-left)
            if result != nil {
                let px = pCentre.x - 52.0, py = pCentre.y - 28.0
                var corner = Path()
                corner.move(to: CGPoint(x: px, y: py + 12))
                corner.addLine(to: CGPoint(x: px, y: py))
                corner.addLine(to: CGPoint(x: px + 12, y: py))
                ctx.stroke(corner, with: GraphicsContext.Shading.color(Color.teal.opacity(0.8)),
                           style: StrokeStyle(lineWidth: 1.2))
            }
        }
    }
}

// Arrow caption view — sits at midpoint of each arrow
struct ArrowCaption: View {
    let text: String
    let from: CGPoint
    let to: CGPoint
    var offset: CGFloat = 0

    var mid: CGPoint {
        CGPoint(x: (from.x + to.x) / 2 + offset, y: (from.y + to.y) / 2)
    }

    var body: some View {
        Text(text)
            .font(.system(size: 10, weight: .regular))
            .foregroundStyle(.secondary)
            .multilineTextAlignment(.center)
            .frame(width: 90)
            .position(mid)
    }
}
