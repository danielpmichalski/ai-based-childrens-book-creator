# AGENTS.md

## What this is

Storybook Studio — a single-file, client-side web app for producing illustrated
children's books. There is no build step, no backend, no package manager, and
no dependencies beyond one Google Fonts `<link>`. The entire app is
`index.html` (~920 lines: `<style>` block, then markup for 3 views, then a
single `<script>` block with all logic).

The app doesn't call any LLM or image API itself. It generates a *prompt* the
user pastes into Claude by hand, and generates *image prompts* the user pastes
into an image generator (OpenArt) by hand. All state lives in memory in the
browser tab; nothing is persisted (no localStorage, no cookies, no network
calls except the Google Fonts stylesheet) and nothing is uploaded anywhere.

To run it: open `index.html` directly in a browser, or serve the directory
with any static file server. There is nothing to install and nothing to
build.

## Repo layout

```
index.html   the entire application (HTML + CSS + JS)
README.md    one-line description + link to a published Claude Artifacts copy
LICENSE
```

There is no `src/`, no `package.json`, no test suite, no CI. Changes are made
directly to `index.html`.

## Conceptual model: 3 views, one page

The app is a single HTML document with three `.view` divs toggled by
`switchView(v)` (`prompt` | `import` | `book`), driven by the header tabs.
Only one view has the `active` class (thus `display: block`/`flex`) at a
time. There is no routing/URL state — reloading the page resets everything.

### View 1 — `#view-prompt` ("① Prompt")
A form (`.prompt-builder`) for book metadata: title, setting, theme, target
age, tone, art style, page count, and any number of characters (name, role,
appearance description). `buildPrompt()` assembles all of this into one large
text prompt instructing an LLM to return a strict JSON storybook structure
(see "JSON book schema" below), and renders it into `#prompt-output`.
`copyBuiltPrompt()` copies it to the clipboard. The user pastes this into
Claude (or any capable LLM) themselves, outside the app.

Character state lives in the `charRows` array (`{id, name, role, desc}`),
uncapped, managed by `addCharRow`/`removeCharRow`/`updateCharRow`/
`renderCharRows`.

### View 2 — `#view-import` ("② Import JSON")
Takes the LLM's JSON response back in, either via drag-and-drop of a `.json`
file, file picker, or pasting raw text into `#json-paste`. `importJSON()`:
1. Strips optional ```json fences, `JSON.parse`s the result.
2. Validates `parsed.pages` is an array (only check performed).
3. Stores the result in the global `bookData`, resets `pageImages`.
4. Renders the "attach character reference photos" section
   (`renderPhotoSection`) if `characters` is present — purely local, stores
   data URLs in `charPhotos` keyed by character name, shown as thumbnails
   later in the book view and print output.
5. Switches to the Book view and calls `renderBook(parsed)`.

### View 3 — `#view-book` ("③ Book")
Renders `bookData` as a header (title, tagline, color palette swatches,
character chips) plus a grid of page cards (`renderBook()` builds
`#pages-grid` from scratch on every re-render — there is no incremental
DOM diffing). Each page card (`.page-card`) shows:
- An image area that is either a drop-zone/file-input (no image yet) or the
  uploaded illustration, with hover overlay controls to Replace/Remove.
  Images are stored as data URLs in `pageImages` keyed by page number —
  never sent anywhere, purely `FileReader.readAsDataURL` in-browser.
- Page text, a collapsible "Image prompt" box (`buildPromptForPage`, which
  appends fixed framing/negative-space/no-text instructions to the
  page's `illustration_prompt`), a link that opens OpenArt pre-filled with
  that prompt (`openartUrl`, URL-encoded, truncated to 500 chars), and a
  "Copy prompt" button.

A progress bar (`updateProgress()`) shows `pageImages` count vs total pages.

Toolbar actions: re-import, expand/collapse all prompt boxes, copy all
prompts concatenated, export the current `bookData` as a downloadable
`.json` (`exportJSON`), and **Print / Save PDF**.

`printBook()` builds a *second, fully self-contained HTML document* (own
`<style>`, its own copy of print CSS, a `document.fonts.ready`-triggered
`window.print()`), opens it in a new tab via a `Blob` + `URL.createObjectURL`
(falling back to a downloadable file if the popup is blocked). This print
document is independent of the `@media print` rules also present in the main
page's `<style>` block (those exist so `Ctrl/Cmd+P` on the main page itself
also produces a reasonable A4-landscape layout, e.g. as a fallback) — if you
change print layout/styling, **both places must be updated**: the `@media
print` block (~line 250) and the inline `<style>` string inside
`printBook()` (~line 797).

## JSON book schema

This is the contract between the prompt built in View 1 and the JSON parsed
in View 2. Keep both in sync if you change one — `buildPrompt()`'s
`REQUIRED JSON STRUCTURE` section is the spec, `importJSON()`/`renderBook()`
are the consumers.

```jsonc
{
  "title": "...",
  "tagline": "one evocative sentence",
  "characters": [
    { "name": "...", "role": "...", "visual_lock": "..." }
  ],
  "color_palette": ["#hex1", "#hex2", "#hex3", "#hex4"],
  "pages": [
    {
      "page": 1,                       // 1-indexed, used as a lookup key in pageImages
      "text": "...",                   // max ~30 words
      "illustration_prompt": "...",    // self-contained, must inline each character's visual_lock
      "mood": "one word",
      "characters_on_page": ["CharacterName"]  // must match characters[].name for photo lookup
    }
  ]
}
```

Only `pages` (must be an array) is actually validated on import — everything
else is used defensively with `||` fallbacks (missing `title`, `characters`,
`color_palette`, `tagline` all degrade gracefully to empty).

## Global state (all in-memory, no persistence)

| Variable     | Shape                          | Purpose                                   |
|--------------|---------------------------------|--------------------------------------------|
| `charRows`   | `[{id, name, role, desc}]`     | Prompt-builder character rows (view 1)    |
| `charPhotos` | `{ [charName]: dataUrl }`      | Reference photos attached in view 2       |
| `pageImages` | `{ [pageNumber]: dataUrl }`    | Illustrations attached per page in view 3 |
| `bookData`   | parsed JSON (see schema above) | The imported book                         |
| `charIdCtr`  | number                          | Monotonic id counter for `charRows`       |

`renderBook(bookData)` is called after *any* mutation that affects the book
view (importing, attaching/removing a character photo, adding/removing a
page image) and does a full re-render of `#pages-grid` from scratch.

## Working in this file

- Everything is global functions on `window` via inline `onclick`/`onchange`/
  `oninput`/`ondragover` etc. attributes in the template strings — there is
  no event delegation, no framework, no modules. New interactive elements
  should follow the same pattern for consistency.
- HTML is built via template-literal string concatenation
  (`.innerHTML = \`...\``), not a templating library. User-supplied strings
  going into HTML must go through `escHtml`/`escAttr`/`escJs` (see below) —
  most existing interpolations already do this, but double-check any new
  ones, since this is the main injection risk in the app (XSS via crafted
  book JSON, e.g. in `title`/`tagline`/character names/page text).
- Utility escaping functions (bottom of the script):
  - `escHtml(s)` — for text nodes / innerHTML content.
  - `escAttr(s)` — for values placed inside `"..."` HTML attributes.
  - `escJs(s)` — for values interpolated into an inline `onclick="...('...')"`
    string literal.
- `showToast(msg)` — the only UI feedback mechanism; a bottom-center toast
  that auto-dismisses. Use it for any new async/user-facing confirmation
  rather than `alert()` (the codebase uses `alert()` only once, for a
  blocking validation error in `buildPrompt()`).
- Styling uses CSS custom properties defined once in `:root` (`--ink`,
  `--paper`, `--cream`, `--warm`, `--accent`, `--accent-dark`, `--accent-light`,
  `--muted`, `--border`, `--radius`). Reuse these rather than hardcoding
  colors; the printable HTML generated by `printBook()` duplicates a subset
  of these as its own `:root` since it's a separate document.
- No build/lint/test tooling exists. Verify changes by opening `index.html`
  in a browser and manually exercising the flow: build a prompt → paste a
  hand-crafted JSON matching the schema into the Import tab → verify the
  Book view renders → attach a photo/image → Print/Save PDF.
- Since this is a single ~920-line file, prefer full-file `Read` over
  partial reads when making non-trivial changes, to keep the HTML/CSS/JS
  triad (which cross-reference each other by id/class name) consistent.
