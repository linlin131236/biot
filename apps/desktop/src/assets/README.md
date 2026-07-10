# Bolt Logo Assets

Canonical first-party brand marks for the desktop renderer and any consumer that imports from this directory.

These assets express **controlled energy**: a permission boundary with a directional strike that can be approved and traced. They are intentionally asset-only in this iteration — the desktop UI still shows Biot in places and is **not** rebranded by these files.

## Inventory

| File | Purpose | Default surface |
|---|---|---|
| `bolt-mark.svg` | Colored master mark / app icon | Dark or mid-tone screens |
| `bolt-mark-mono.svg` | Single-color master mark (`currentColor`) | Theme-driven UI, CLI, print |
| `bolt-logo-horizontal.svg` | Colored mark + wordmark | Headers, site chrome ≥ 96 CSS px wide |
| `bolt-logo-stacked.svg` | Colored mark over wordmark | Square/portrait launch and profile surfaces |

## Color tokens

| Token | Hex | Role |
|---|---:|---|
| Bolt Night | `#08111F` | Dark application background |
| Electric Blue | `#39D9FF` | Primary energy |
| Pulse Violet | `#7B61FF` | Directional energy depth |
| Signal White | `#F5FAFF` | Dark-surface wordmark / light mono mark |
| Ink | `#101827` | Light-surface mono mark / dark wordmark |

Colored marks use a diagonal gradient from Electric Blue to Pulse Violet. Mono marks inherit host color via `currentColor`.

## Production rules

- Do not redraw, rotate, outline, or apply a drop shadow to the mark.
- Keep clear space equal to one quarter of the mark's width on every side.
- Do not use the horizontal lockup below 96 CSS pixels wide.
- Do not use the standalone mark below 16 CSS pixels wide.
- On light surfaces, use `bolt-mark-mono.svg` with `color: #101827` until a dedicated light-surface colored lockup is approved.
- The current desktop interface is branded Biot in places; do not replace UI copy or class names as part of asset-only work.

## Import examples (Vite / React)

```tsx
import boltMark from './assets/bolt-mark.svg';

<img src={boltMark} width={32} height={32} alt="Bolt" />
```

Monochrome / theme-aware:

```tsx
import boltMarkMono from './assets/bolt-mark-mono.svg';

<img className="brandMark" src={boltMarkMono} width={24} height={24} alt="Bolt" />
```

```css
.brandMark {
  color: #101827;
}
```

> Note: SVG `<img>` tags do not inherit CSS `color` for `currentColor` fills. For true monochrome theming, either inline the mono SVG or set the host color and use an SVG React component path if the build is later extended for it. Until then, prefer the colored mark on dark surfaces and pre-tinted mono variants if needed.

## Geometry notes

- Master mark viewBox: `0 0 64 64`
- Horizontal lockup viewBox: `0 0 256 64`
- Stacked lockup viewBox: `0 0 160 150`
- Wordmarks are pure path geometry (no fonts)
- No external image or font dependencies
