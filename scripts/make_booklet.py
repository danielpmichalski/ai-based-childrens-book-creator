#!/usr/bin/env python3
"""
Impose a single-page-per-sheet landscape A4 storybook PDF (as produced by
index.html's "Print / Save PDF" button) into a top-bound saddle-stitch A5
pamphlet: 2-up per portrait A4 sheet, duplex, ready to fold and clip/staple
at the spine.

See ../PRINTING.md for the full physical printing and binding workflow.

Usage:
    python3 make_booklet.py INPUT.pdf [-o OUTPUT.pdf] [--debug]

    --debug   Stamp each slot with its source page number (or "BLANK") in
              small red text, for a cheap scrap-paper test print before
              committing good paper. Omit for the final print.

Fold model
----------
- Source pages are landscape A4 (297x210mm) with full-bleed art; aspect
  ratio is preserved throughout, so nothing gets cropped or redesigned.
- Each output sheet is portrait A4 (210x297mm), split into a TOP half and
  a BOTTOM half, each 210x148.5mm (landscape A5). Source pages are scaled
  down uniformly to fit - same aspect ratio, so no cropping.
- Physical fold: horizontal crease at the sheet's mid-height, spine at the
  TOP. The booklet opens/flips like a top-bound flip pad, not a
  left-bound book (a left-bound fold would require portrait-shaped pages,
  which would crop every illustration - see PRINTING.md for why this
  fold direction was chosen).
- Slot mapping is the standard saddle-stitch imposition formula, rotated
  90 degrees (TOP takes the role "left"/spine-adjacent plays in a normal
  left-right booklet; BOTTOM takes the role "right"/cover-facing plays):
    For N pages (padded to a multiple of 4), sheet i (0-indexed, i=0 is
    the outermost sheet):
      front: TOP = N - 2i,      BOTTOM = 2i + 1
      back:  TOP = 2i + 2,      BOTTOM = N - 2i - 1
- Output PDF page order is print order for a duplex run: sheet0-front,
  sheet0-back, sheet1-front, sheet1-back, ...
- Print with duplex set to short-edge / tumble (see PRINTING.md) - the
  long-edge default would print the back sides upside-down relative to
  the front.

Requires: pymupdf (`pip install pymupdf`).
"""
import argparse
import os
import sys

import pymupdf as fitz

A4_W, A4_H = 595.28, 841.89  # A4 portrait, points
HALF_H = A4_H / 2


def build_booklet(src, debug=False):
    n_real = src.page_count
    n = n_real
    while n % 4 != 0:
        n += 1
    n_blank = n - n_real
    print(f"Source pages: {n_real}, padded to {n} ({n_blank} blank pages appended)")

    out = fitz.open()

    def place(page, page_no, rect):
        if page_no is not None and page_no <= n_real:
            page.show_pdf_page(rect, src, page_no - 1)
            label = str(page_no)
        else:
            label = "BLANK"
        if debug:
            page.insert_text((rect.x0 + 4, rect.y0 + 12), label, fontsize=8, color=(1, 0, 0))

    sheets = n // 4
    for i in range(sheets):
        front_top, front_bottom = n - 2 * i, 2 * i + 1
        back_top, back_bottom = 2 * i + 2, n - 2 * i - 1

        p = out.new_page(width=A4_W, height=A4_H)
        place(p, front_top if front_top <= n_real else None, fitz.Rect(0, 0, A4_W, HALF_H))
        place(p, front_bottom if front_bottom <= n_real else None, fitz.Rect(0, HALF_H, A4_W, A4_H))

        p = out.new_page(width=A4_W, height=A4_H)
        place(p, back_top if back_top <= n_real else None, fitz.Rect(0, 0, A4_W, HALF_H))
        place(p, back_bottom if back_bottom <= n_real else None, fitz.Rect(0, HALF_H, A4_W, A4_H))

    print(f"-> {out.page_count} output pages = {sheets} duplex sheets")
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", help="Source PDF from the app's Print/Save PDF button (one landscape A4 page per book page)")
    ap.add_argument("-o", "--output", help="Output path (default: INPUT_booklet.pdf next to the input, or INPUT_booklet_debug.pdf with --debug)")
    ap.add_argument("--debug", action="store_true", help="Stamp page numbers on each slot for a scrap-paper test print")
    args = ap.parse_args()

    src = fitz.open(args.input)
    out = build_booklet(src, debug=args.debug)

    if args.output:
        out_path = args.output
    else:
        base, ext = os.path.splitext(args.input)
        out_path = f"{base}_booklet{'_debug' if args.debug else ''}{ext}"

    out.save(out_path)
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    sys.exit(main())
