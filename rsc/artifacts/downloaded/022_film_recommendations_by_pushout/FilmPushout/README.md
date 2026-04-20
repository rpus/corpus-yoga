# Film Pushout

A SwiftUI iPhone app that computes film recommendations as categorical pushouts.

## Setup

1. Create a new Xcode project: **File → New → Project → App**
   - Product Name: `FilmPushout`
   - Interface: SwiftUI
   - Language: Swift

2. Delete the default `ContentView.swift` that Xcode creates.

3. Add all five `.swift` files from this folder to the project:
   - `FilmPushoutApp.swift`
   - `AnthropicService.swift`
   - `PushoutViewModel.swift`
   - `ArrowLayer.swift`
   - `NodeView.swift`
   - `VerdictCard.swift`
   - `ContentView.swift`

4. In `AnthropicService.swift`, replace `YOUR_ANTHROPIC_API_KEY` with your key.

5. Build and run on simulator or device (iOS 17+).

## How it works

The diagram is the UI. Three input nodes form the span:

- **C** (top): the shared substructure — what both films map *from*
- **A** (left): Film A
- **B** (right): Film B

The pushout **A ⊔_C B** (bottom) is the universal film that inherits
everything from A not in C, everything from B not in C, and identifies
the shared C-structure. Arrow captions populate after computation.

## Notes

- Requires iOS 17+ (for `onChange` and `Observable` compatibility)
- The API key is hardcoded — fine for personal use, do not ship publicly
- Model: `claude-sonnet-4-6`
