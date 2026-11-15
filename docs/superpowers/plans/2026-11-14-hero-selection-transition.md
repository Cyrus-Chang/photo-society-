# Hero Selection Transition Implementation Plan

> **For agentic workers:** Native implementation in the current session.

**Goal:** Fix selected-photo motion and return-state jitter without touching the original background image or user content.

**Architecture:** Keep the existing single hero background `<img>` as a persistent layer. Add a selection state class to the hero; animate only the active photo card, stage wrapper, heading visibility, and right-side detail panel. Source gallery metadata from the existing `works` records and `localWorkUrl()`.

**Tech Stack:** Vue 3, TypeScript, CSS transitions, Vite.

**Spec:** `docs/superpowers/specs/2026-11-14-hero-selection-transition-design.md`

## Global Constraints

- Preserve `hero-stars.webp` `<img>` sizing and cropping contract exactly.
- Do not change any user-authored hero copy.
- Do not duplicate the background image.
- Empty author descriptions stay empty.

## Review Focus

- Selecting a card: active image moves left and scales once; detail enters from the right.
- Closing detail: only selection state clears; background element and geometry remain unchanged.
- Rapid select/close/select: no stale transition leaves the detail at the bottom.
- Asset mapping: every visible gallery item resolves from one `works` record and one local asset URL.
- Empty description: no invented story appears in the detail panel.

---

### Task 1: Lock gallery data and content boundaries

**Files:**
- Modify: `src/pages/HomePage.vue`

**Interfaces:**
- `galleryItems: GalleryItem[]` remains the render source.
- Each item uses `works` metadata and `localWorkUrl(filename)`; `story` is empty unless supplied by data.

- [x] Replace hand-maintained title/image metadata with the existing `works` lookup while preserving the current gallery order.
- [x] Keep the current hero headline text byte-for-byte unchanged.
- [x] Render the detail description only when `activeItem.story` is non-empty.

### Task 2: Implement the single-layer selection transition

**Files:**
- Modify: `src/pages/HomePage.vue`
- Modify: `src/styles.css`

**Interfaces:**
- `hasSelected` controls the hero selection state.
- `selectCard(index)` changes selection; `closeDetail()` clears it.

- [x] Add the `has-selection` class to `.spiral-hero`.
- [x] Animate `.gallery-card.is-active` with a leftward stage shift and a scale-up; keep the background `<img>` outside the animated properties.
- [x] Hide the hero heading only while selected and keep its content unchanged.
- [x] Position `.spiral-detail` absolutely on the right with a translate-in transition; keep it out of normal document flow.
- [x] Remove the duplicate “添加你的现场” orbit card.
- [x] Disable the pupil highlight rotation while preserving its static blue styling.

### Task 3: Verify regression boundaries

**Files:**
- Test: `npm run build`
- Review: browser at `/`

- [x] Run `npm run build` and require a successful Vite build.
- [x] Verify the initial state shows one `hero-bg-image` element.
- [x] Verify selecting a card keeps the background image computed geometry unchanged while the card and detail animate.
- [x] Verify closing detail removes the selection class without changing the background image.
- [x] Verify no empty story copy or broken local asset URL is rendered.

