# RhymeMapper Design System — "Spectrum"

## 1. Visual Theme & Atmosphere

RhymeMapper is a dark, near-black instrument (`#08080c`, `#0f0f16`, `#16161f`) built
on one idea taken from music players and inverted:

> **The analysis is the album art.**

Spotify's interface recedes into charcoal so that cover art supplies the colour.
RhymeMapper has no cover art — it has *phonetics*. So the chrome is deliberately
achromatic, and every hue on screen is generated from the rhyme groups themselves.
A syllable is coloured because of how it sounds. Colour is data here, never
decoration, and the interface is built so nothing competes with it.

Around that sits the **weave** — glowing filaments drifting behind the
content, reacting to the track when one is playing. It gives the page the feel of
a darkened room with a system running in it, rather than a document.

Everything else is restraint: a single warm accent (`#ff8a3d`) for actions, one
cool accent (`#5ce1e6`) for live state, generous black, and type doing the work.

**Key characteristics**

- Near-black ground (`#08080c`–`#16161f`); the UI disappears behind the analysis
- **Hue is generated from the data** — the rhyme palette is the brand palette
- One warm accent for action, one cool accent for "playing"
- Editorial display serif against a geometric UI sans and a phonetic mono
- Woven threads + film grain: atmosphere, never texture for its own sake
- Motion that explains — reveals follow reading order, colour arrives with meaning
- Big hit areas, pill geometry, deep shadows

---

## 2. Colour Palette & Roles

### Ground
| Token | Value | Role |
|---|---|---|
| `--void` | `#08080c` | Page ground, deepest surface |
| `--surface` | `#0f0f16` | Panels, cards |
| `--surface-2` | `#16161f` | Raised surface, inputs |
| `--surface-3` | `#1e1e2a` | Hover, active rows |
| `--hairline` | `#272733` | 1px borders |
| `--hairline-bright` | `#3a3a4a` | Focus and hover borders |

### Text
| Token | Value | Role |
|---|---|---|
| `--ink` | `#f4f4f8` | Primary text |
| `--ink-2` | `#a8a8bb` | Secondary, labels |
| `--ink-3` | `#6b6b80` | Tertiary, captions, disabled |

### Accents
| Token | Value | Role |
|---|---|---|
| `--flame` | `#ff8a3d` | Primary action, focus, brand |
| `--flame-deep` | `#ff5e3a` | Gradient partner for `--flame` |
| `--pulse` | `#5ce1e6` | Live state: playing, streaming, active |
| `--danger` | `#ff6b81` | Errors |

Accent gradient: `linear-gradient(100deg, #ff5e3a, #ff8a3d, #ffc46b)`.

### The generated palette (the important one)

Rhyme-group colour is **computed, not chosen**. A group's label is hashed to a
hue, then stepped by the golden angle (137.508°) so neighbouring groups land far
apart on the wheel:

```
hue        = (hash(label) * 137.508) mod 360
saturation = 70–78%
lightness  = 62–74%      (varied per label so adjacent hues separate further)
```

This has to be generated rather than enumerated: the old interface shipped 26 CSS
classes (`.rhyme-a` … `.rhyme-z`) and could not colour a verse with more groups.
*Rap God* produces 56 under the exact engine and 257 under chain detection.

Syllable text on a generated colour is always `#0b0b10` — the palette is kept
light enough that dark ink always clears contrast.

### Shadows & glow
| Token | Value | Role |
|---|---|---|
| `--shadow-panel` | `0 24px 60px -20px rgba(0,0,0,.8)` | Panels, modals |
| `--shadow-lift` | `0 8px 24px rgba(0,0,0,.45)` | Cards, buttons |
| `--glow-flame` | `0 0 32px -6px rgba(255,138,61,.55)` | Primary action |
| `--glow-pulse` | `0 0 24px -4px rgba(92,225,230,.6)` | Currently-singing syllable |

---

## 3. Typography

### Families
| Role | Stack |
|---|---|
| Display | `'Bodoni Moda', 'Didot', 'Iowan Old Style', Georgia, serif` |
| UI / Body | `'Manrope', 'Inter', system-ui, -apple-system, sans-serif` |
| Phonetic | `'JetBrains Mono', ui-monospace, 'SF Mono', Menlo, monospace` |

The display serif is doing deliberate work: the subject is *poetics*, and an
editorial serif says analysis rather than dashboard. The mono is not styling —
ARPAbet (`AE1`, `NG`, `DH`) is code and reads as code.

### Scale
| Role | Size | Weight | Tracking | Notes |
|---|---|---|---|---|
| Hero | `clamp(2.75rem, 7vw, 5.5rem)` | 400 | `-0.03em` | Display serif, line-height 0.95 |
| Section title | `clamp(1.5rem, 3vw, 2rem)` | 400 | `-0.02em` | Display serif |
| Panel heading | `0.8rem` | 600 | `0.12em` | UI sans, uppercase |
| Body | `0.95rem` | 400 | normal | UI sans, line-height 1.6 |
| Lyric | `clamp(1rem, 1.3vw, 1.2rem)` | 500 | `-0.005em` | UI sans, line-height 2.1 |
| Stat value | `clamp(1.4rem, 2.6vw, 2rem)` | 500 | `-0.02em` | Tabular numerals |
| Label | `0.68rem` | 500 | `0.14em` | Uppercase, `--ink-3` |
| Phonetic | `0.75rem` | 400 | `0.02em` | Mono |

Lyric line-height is 2.1 — far looser than normal body text. Coloured syllables
form horizontal bands, and without air between the lines a dense verse turns into
a solid block of colour.

---

## 4. Spacing & Layout

4px base. `4, 8, 12, 16, 24, 32, 48, 64, 96, 128`.

| Token | Value |
|---|---|
| `--gap-xs` … `--gap-3xl` | `4px, 8px, 12px, 16px, 24px, 32px, 48px, 64px` |
| `--radius-sm` / `-md` / `-lg` / `-xl` | `6px / 10px / 16px / 24px` |
| `--radius-pill` | `999px` |

- Page max width `1440px`; reading column max `72ch`
- Analysis view: `minmax(0,1fr)` + `340px` sidebar; single column below `1040px`
- Section rhythm: `96px` desktop, `56px` mobile
- Gutter never below `16px` at any width

---

## 5. Motion

Motion exists to explain sequence and causation. If an animation does not help
someone understand what changed, it should not run.

| Token | Value | Use |
|---|---|---|
| `--ease-out` | `cubic-bezier(.22,1,.36,1)` | Entrances, reveals |
| `--ease-in-out` | `cubic-bezier(.65,0,.35,1)` | State changes |
| `--ease-spring` | `cubic-bezier(.34,1.56,.64,1)` | Buttons, magnetics |
| `--t-fast` | `140ms` | Hover, focus |
| `--t-base` | `260ms` | Panels, tabs |
| `--t-slow` | `600ms` | Reveals, hero |

Rules

1. **Reveals follow reading order.** Staggered children, 18–30ms apart, never more
   than ~600ms total.
2. **Colour arrives with meaning.** Syllables fade from neutral to their rhyme
   hue *after* the text lands, so the reader sees words, then the pattern.
3. **One thing moves at a time.** The weave is ambient and continuous; anything
   else animates only in response to input.
4. **`prefers-reduced-motion` is honoured completely** — the weave frozen, reveals
   become instant, no parallax. The page must remain fully usable and still
   handsome.

---

## 6. Components

**Button — primary.** Pill, `--flame` gradient, `--glow-flame`. Magnetic within
~26px of the cursor. Animated conic border on the analyse action only, so exactly
one element on the page is asking to be pressed.

**Button — ghost.** Transparent, `--hairline` border, `--ink-2` text. Border
brightens and text goes `--ink` on hover.

**Input — link bar.** The hero's centrepiece. `--surface-2` pill, `18px`
vertical padding, monospace placeholder. Focus raises a `--flame` ring plus glow.

**Panel.** `--surface`, `--hairline` border, `--radius-lg`, `--shadow-panel`.
Spotlight on hover: a soft radial highlight tracks the cursor.

**Syllable.** Inline, `2px` radius, `1px` horizontal padding. States: plain
(`--ink`), rhyming (generated hue, `#0b0b10` ink), traced (white ring), playing
(`--pulse` ring + `--glow-pulse`), dimmed (opacity `.14`).

**Chain row.** Swatch, label, then length × occurrences right-aligned. The whole
row is a hit target; selected rows carry a `--flame` border.

---

## 7. Effects

Ported to vanilla JS/CSS from the patterns in
[react-bits](https://github.com/DavidHDev/react-bits):

| Effect | Where | Notes |
|---|---|---|
| WebThreads | Page background | WebGL2 fragment shader; hue follows the rhyme under the playhead |
| Aurora | Background fallback | Canvas 2D; used where there is no GPU to run the shader on |
| Noise | Global overlay | Tiled grain, `mix-blend-mode: overlay`, ~3% opacity |
| SplitText | Hero headline | Per-character rise + blur clear |
| ShinyText | Brand mark, badges | Sweeping highlight |
| GradientText | Key figures | Accent gradient clipped to text |
| CountUp | Stat tiles | Eased counting, honours reduced motion |
| ClickSpark | Global | Radial spark burst on click |
| Magnet | Primary buttons | Cursor attraction with spring return |
| StarBorder | Analyse action | Rotating conic gradient border |
| SpotlightCard | Panels | Radial highlight follows cursor |
| ScrambledText | Loading states | Character scramble while work is in flight |

Every effect is capped: `prefers-reduced-motion` disables all of them, and the
the weave is drawn once and held still.

---

## 8. Do's and Don'ts

**Do**
- Let rhyme colour be the only chroma in the content area
- Keep phonetic data in mono
- Give lyrics room to breathe — line-height 2.1 minimum
- Animate *into* meaning: text first, colour second
- Keep one primary action visible per view

**Don't**
- Tint the chrome with accent colour; it competes with the data
- Enumerate rhyme colours in CSS — generate them, there is no upper bound
- Animate the weave and a reveal and a hover simultaneously
- Use colour alone to convey state; pair it with a ring, label or position
- Put anything behind a hover on touch: every hover affordance has a tap path

---

## 9. Responsive

| Breakpoint | Behaviour |
|---|---|
| `> 1040px` | Two columns: analysis + sidebar |
| `640–1040px` | Single column, sidebar below, stats wrap to 3 |
| `< 640px` | Hero type at `clamp` floor, stats 2-up, controls full-width |

Touch targets `44px` minimum. Hover-only affordances always have a tap
equivalent. The page never scrolls horizontally at any width.
