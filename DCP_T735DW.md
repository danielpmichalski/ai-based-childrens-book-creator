# Brother DCP-T735DW: printer-specific notes

Findings about this particular printer (color inkjet, native Brother driver
on macOS, queue name `Brother_DCP_T735DW`) while printing booklets from
this app. The general workflow lives in [PRINTING.md](PRINTING.md); anything
here may not hold for another printer or driver.

## What the driver exposes

From `lpoptions -p Brother_DCP_T735DW -l` and the PPD in
`/etc/cups/ppd/Brother_DCP_T735DW.ppd`:

| Option             | Values (`*` = default)                                                                        |
|--------------------|-----------------------------------------------------------------------------------------------|
| `PageSize`         | `A4` (default), `A4.Fullbleed`, A5, A6(.Fullbleed), Letter(.Fullbleed), …                     |
| `MediaType`        | `stationery`, `stationery-inkjet`, `photographic-glossy`, `com.brother-bp71`, `any` (default) |
| `cupsPrintQuality` | `Draft` (300×300 dpi), `Normal` (default, 600×600), `High` (600×600)                          |
| `Duplex`           | `None`, `DuplexNoTumble` (long edge, default), `DuplexTumble` (short edge)                    |

`A4.Fullbleed` has an imageable area of the whole sheet (`0 0 595.28 841.89`
pt, the same size as plain A4). The PPD has no `UIConstraints` at all, so
CUPS never warns about the limitations below — they only show up on paper.

## Borderless and duplex don't combine

With `media=A4.Fullbleed` the printer prints one side and ejects the sheet,
ignoring `Duplex=DuplexTumble`. With plain `media=A4` it pulls the sheet back
in and prints the second side. So:

- **Automatic duplex** needs plain `A4` and leaves a thin white rim of
  unprintable margin on every edge.
- **Borderless** (no rim) means manual duplex: fronts first, reload, then
  backs.

## Borderless ignores the quality setting

`-o cupsPrintQuality=Draft` has no effect with `media=A4.Fullbleed`; the
print is as slow as `High`. With plain `A4`, Draft is fast and uses little
ink. Use plain `A4` + Draft for layout, page-order and stapling tests, and
keep `A4.Fullbleed` for the borderless reload test (print a couple of sheets
with `page-ranges`) and the final run.

## Booklet duplex direction

`Duplex=DuplexTumble` (short edge) is correct for the top-bound booklet from
`scripts/make_booklet.py`. Verified on a full 5-sheet debug booklet printed
with plain `A4` at Draft: page order, upright backs and stapling were all
right.

```sh
lp -d Brother_DCP_T735DW -o media=A4 -o MediaType=stationery \
   -o ColorModel=RGB -o cupsPrintQuality=Draft -o Duplex=DuplexTumble \
   "your-book_booklet_debug.pdf"
```

## Manual duplex reload

Take the printed sheets out of the output tray and put them back into the
paper drawer **exactly as they are, with no rotating or flipping**, then
print the even pages (the backs). Verified on a single scrap sheet (page 1
as the front, page 2 as the back).

```sh
# Fronts (odd pages), borderless, single-sided
lp -d Brother_DCP_T735DW -o media=A4.Fullbleed -o MediaType=stationery \
   -o ColorModel=RGB -o cupsPrintQuality=Draft -o Duplex=None \
   -o page-set=odd "your-book_booklet_debug.pdf"

# Reload the stack unchanged, then the backs (even pages)
lp -d Brother_DCP_T735DW -o media=A4.Fullbleed -o MediaType=stationery \
   -o ColorModel=RGB -o cupsPrintQuality=Draft -o Duplex=None \
   -o page-set=even "your-book_booklet_debug.pdf"
```

(Draft is accepted but ignored here, see above; keep it in the command so
the same line works with plain `A4`.)

## Not yet verified

- **Sheet order across a multi-sheet stack** in manual duplex. If the backs
  land on the wrong fronts, the stack came out reversed: add
  `-o outputorder=reverse` to the odd-pages command and re-test.
- **Paper weight in automatic duplex.** Whether the duplex unit feeds
  160 g satin paper reliably (the scrap tests used plain paper).
- **The good paper at `High`:** drying time, smearing on the second pass and
  cracking at the fold.
