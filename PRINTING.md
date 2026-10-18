# Printing a generated book

This covers turning a book made with this app into a physical, bound
booklet — either the simple way (one full A4 landscape sheet per page) or
as a folded A5 pamphlet (2 pages per A4 sheet, double-sided, folded and
clipped/stapled at the spine).

Tested with a Brother DCP-T735DW (color inkjet, AirPrint + native macOS
driver) and "Color Copy" 160gsm satin-coated paper, but the general steps
apply to any inkjet/laser printer and paper stock.

**Note on paper/media type:** if you're using dedicated glossy *photo*
paper, use `MediaType=photographic-glossy` below instead of
`stationery-inkjet` — glossy photo stock is coated to absorb much more
ink than general-purpose satin/silk copier paper, and using the wrong
setting in either direction causes problems: `photographic-glossy` on
non-photo paper over-inks and smudges; `stationery`/`stationery-inkjet`
on true photo paper under-inks and looks dull. When in doubt, check your
paper's packaging for its actual finish and match it to whichever driver
`MediaType` option is closest, and always confirm with a one-page test
print (§4) before committing a full run.

## 1. Generate the PDF from the app

In `index.html`, go to the **Book** view and click **🖨 Print / Save PDF**
(`printBook()` in the script). This opens a new tab with a print-ready
document and auto-triggers the browser print dialog after fonts load.

- **Paper size:** A4, **Landscape** — this is hardcoded in the generated
  page (`@page { size: A4 landscape; margin: 0; }`), one full-bleed sheet
  per book page (cover + one per story page).
- In the print dialog, set **Margins: None** and enable **Background
  graphics** (Chrome/Edge) or **Print backgrounds** (Firefox/Safari) — the
  art and caption bar are CSS backgrounds and won't print without this.
- Choose **Save as PDF** to get a file, or print directly if you're doing
  the simple one-page-per-sheet layout (skip to §4).

Sanity-check the resulting PDF before printing anything:

```sh
pdfinfo "your-book.pdf"
```

Expect: `Page size: 841.92 x 594.96 pts (A4)` (i.e. A4 landscape) and a
page count of `1 + number of story pages` (page 1 is the cover).

## 2. (Optional) Turn it into an A5 pamphlet

`scripts/make_booklet.py` re-imposes the single-page-per-sheet PDF from
step 1 into a saddle-stitch booklet: 2 pages per portrait A4 sheet,
printed double-sided, folded in half and bound at the spine.

**Why this fold direction, specifically:** the book's pages are landscape
(wide) full-bleed art. An A4 sheet can only fold into A5 two ways:

- **Horizontal fold** (crease left-right, portrait A4) → each half is a
  **landscape** A5 (210×148.5mm), same aspect ratio as the source pages,
  so art scales down with **zero cropping**. The spine ends up at the
  top/bottom, so the bound booklet flips like a top-bound flip
  pad/calendar rather than a traditional left-bound book.
- **Vertical fold** (crease top-bottom, landscape A4) → each half is a
  **portrait** A5, spine on the left, turns like a normal book — but every
  full-bleed landscape illustration would need to be cropped hard on the
  sides to fit the narrower portrait frame.

The script implements the first option (no cropping, top-bound spine).
There is no A4 fold that gives a left-bound book with zero cropping for
landscape art — that's a hard constraint of paper geometry, not a script
limitation.

Saddle-stitch also requires the page count to be a multiple of 4 (each
folded sheet always carries exactly 4 pages). The script pads the end of
the book with blank pages automatically.

The script also inserts one **blank page right after the front cover**
(the inside of the cover). Opening the booklet then shows the blank on top
and the first story page at the bottom of the spread, instead of the story
starting on the top half. Pass `--no-blank-after-cover` to turn this off.

### Setup

```sh
python3 -m venv .venv
.venv/bin/pip install pymupdf
```

### Run it

```sh
# Test version first — stamps each slot with its source page number
# (or "BLANK") in small red text, for a cheap scrap-paper check:
.venv/bin/python scripts/make_booklet.py "your-book.pdf" --debug

# Final, clean version once the test folds correctly:
.venv/bin/python scripts/make_booklet.py "your-book.pdf"
```

Default output is `your-book_booklet.pdf` (or `..._booklet_debug.pdf`)
next to the input; pass `-o path/to/output.pdf` to choose your own.

Output is always `ceil((pages + 1)/4)` double-sided A4 sheets, counting the
blank after the cover (e.g. 17 source pages → 18 → padded to 20 → 5 sheets).

### Validate before using good paper

1. Print the `_debug` PDF on plain scrap paper, duplex, **short-edge /
   tumble** (see §3 — this matters, long-edge duplex prints the backs
   upside-down relative to the fronts for this fold direction).
2. Stack the sheets in the order they printed (sheet 1 outermost) and
   fold the whole stack in half at once, horizontally.
3. Flip through it front to back: the little red numbers should read in
   order 1, BLANK, 2, 3, … with the cover (page 1) as the very first thing
   you see, a blank inside the cover, and the remaining "BLANK" pages only
   at the very end — never interrupting the story sequence.
4. If it doesn't read in order, don't print the real thing — something's
   off in the fold/duplex direction, not the imposition math (rerun
   through the checklist in §3 before re-testing).

## 3. Printer setup (macOS)

### Add the printer

System Settings → Printers & Scanners → Add Printer. If the printer
shows up with a manufacturer-specific driver option (not just "AirPrint"
or "Secure AirPrint"), pick that — it exposes proper media types
(e.g. glossy photo paper) and often a full-bleed/borderless page size
that the generic AirPrint driver doesn't.

Verify what got installed and confirm it's the full driver, not a bare
AirPrint fallback:

```sh
lpstat -p                                  # list installed printers
lpoptions -p <PrinterQueueName> -l         # -l after -p, not before —
                                            # otherwise you get stale/cached defaults
```

Look for these in the option list (names vary by driver, but this is
what the Brother driver exposes):

- `PageSize`: should include an `A4.Fullbleed` (or similarly named
  borderless) option alongside plain `A4`.
- `MediaType`: should include several options beyond plain `stationery`,
  e.g. `stationery-inkjet` and `photographic-glossy`.
- `ColorModel`: should default to `RGB`, not `Gray`.

If none of that shows up, you likely only have the generic AirPrint
driver — install Brother's driver package from their support site for
this model and re-add the printer.

### Duplex direction for the booklet

Check the PPD for how the duplex options are labeled:

```sh
grep "Duplex" /etc/cups/ppd/<PrinterQueueName>.ppd
```

You want whichever option is labeled **short-edge** (often named
`DuplexTumble`) for the booklet — the pages are landscape content on a
portrait sheet folding at the top, which is exactly the case short-edge
duplex exists for. The default long-edge option (`DuplexNoTumble`) will
print every back side upside-down relative to its front.

### Borderless and duplex don't combine (Brother DCP-T735DW)

The PPD lists `A4.Fullbleed` and `DuplexTumble` with no `UIConstraints`, but
in practice the printer **ignores duplex when the page size is borderless**:
with `media=A4.Fullbleed` it prints one side and ejects the sheet, with
plain `media=A4` it pulls the sheet back in for the second side.

So you have to choose:

- **Automatic duplex** with plain `A4` — one print run, but a thin white rim
  of unprintable margin remains on every edge.
- **Manual duplex** with `A4.Fullbleed` — print the fronts, reload, print the
  backs. True edge-to-edge art, but you handle each sheet twice.

## 4. Print commands

Single page-per-sheet (no booklet), full-bleed A4 landscape, on satin
copier paper (e.g. Color Copy 160gsm satin) — swap `MediaType` per the
note in the intro if you're using true glossy photo paper instead:

```sh
lp -d <PrinterQueueName> \
   -o media=A4.Fullbleed \
   -o MediaType=stationery-inkjet \
   -o ColorModel=RGB \
   -o cupsPrintQuality=High \
   -o Duplex=None \
   "your-book.pdf"
```

A5 booklet, automatic duplex, on satin copier paper (run only after the
scrap test in §2 reads correctly). Uses plain `A4`, so expect the white rim
described in §3:

```sh
lp -d <PrinterQueueName> \
   -o media=A4 \
   -o MediaType=stationery-inkjet \
   -o ColorModel=RGB \
   -o cupsPrintQuality=High \
   -o Duplex=DuplexTumble \
   "your-book_booklet.pdf"
```

Test the scrap-paper booklet run the same way but with `MediaType=stationery`
(plain paper), `cupsPrintQuality=Draft` (much faster, uses little ink) and
the `_debug` PDF instead of your good stock. This verified the page order,
tumble direction and stapling on a full 5-sheet book.

### Manual duplex, borderless (untested)

For a booklet without the white rim: print every front side borderless,
reload the stack, then print every back side borderless. The booklet PDF is
already laid out as front, back, front, back, … so the odd pages are the
fronts and the even pages the backs. **This procedure has not been verified
yet** — do the whole thing with the `_debug` PDF on scrap paper first, and
adjust the reload step until the folded result reads in order.

```sh
# 1. Fronts (odd pages), borderless, single-sided
lp -d <PrinterQueueName> \
   -o media=A4.Fullbleed \
   -o MediaType=stationery-inkjet \
   -o ColorModel=RGB \
   -o cupsPrintQuality=High \
   -o Duplex=None \
   -o page-set=odd \
   "your-book_booklet.pdf"

# 2. Reload the printed stack (see below), then the backs (even pages)
lp -d <PrinterQueueName> \
   -o media=A4.Fullbleed \
   -o MediaType=stationery-inkjet \
   -o ColorModel=RGB \
   -o cupsPrintQuality=High \
   -o Duplex=None \
   -o page-set=even \
   "your-book_booklet.pdf"
```

Things the scrap test has to settle, since they depend on how the tray feeds:

- **Which way up to reload.** The back sides are laid out for a short-edge
  flip: turn each sheet over like a calendar page (top edge becomes bottom
  edge). Mark one corner of a scrap sheet with a pencil and note which
  orientation puts the back right-way-up behind the front.
- **Sheet order.** If the backs end up on the wrong fronts, the stack came
  out reversed. Add `-o outputorder=reverse` to the first command (or reload
  the stack in the other order) and re-test.
- **Feeding twice.** Coated 160 g satin paper can curl or jam on the second
  pass. Let the fronts dry fully first, and feed one or two sheets at a
  time if it misfeeds.

Always send a one-page test (`-o page-ranges=1`) on scrap paper first
when trying a printer/paper combination for the first time, to check
alignment and that borderless printing isn't cropping anything important
— borderless/full-bleed inkjet printing intentionally over-scans by a
mm or two on every edge to avoid a white sliver, which is normal.

## 5. Physical assembly

- **Let ink set before stacking.** Coated stock (satin or glossy) dries
  slower than plain paper. Let each sheet sit in the output tray for at
  least ~30 seconds before stacking it with others — true glossy photo
  paper needs longer (a minute or more) than satin copier paper. Let the
  full set dry further before folding/handling if colors still feel
  tacky.
- **Single-sheet-per-page layout:** stack in order (cover, page 1, page
  2, …), then clip along the **short (210mm) edge** on the left with the
  long-arm clipper — it flips like a picture book/flip-chart.
- **A5 booklet layout:** stack the printed sheets in the order they came
  out (sheet 1 on top/outermost) and fold the whole stack in half at once
  along the horizontal crease. On coated 160 g stock, score the crease
  first (bone folder or the back of a knife) so the coating and ink don't
  crack, or fold each sheet individually and nest them afterwards.
- **Stapling:** open the folded stack flat and put the crease under the
  long-arm stapler (the throat has to reach about 148.5 mm, half the
  sheet's length). Staple through the crease at roughly ¼ and ¾ of its
  210 mm length, from the inside so the prongs clinch inside the booklet.
  A staple through the crease needs no extra inner margin. A 5-sheet book
  is 10 layers of 160 g, roughly 20 sheets of ordinary 80 g paper, which is
  close to a 25-sheet stapler's rating — a thicker book than that needs a
  higher-capacity stapler or fewer pages.

## Files in this repo related to printing

- `scripts/make_booklet.py` — the A5 booklet imposition script (§2).
