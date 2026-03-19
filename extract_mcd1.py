#!/usr/bin/env python3
"""
extract_mcd1.py — Extract all images from Muppets Inside (1996) MCD1.CD
========================================================================
No dependencies beyond the Python standard library.

Usage:
	python extract_mcd1.py [MCD1.CD] [pn10ni11.dll] [output_dir]

	All three arguments are optional and default to the same directory as
	this script:

		MCD1.CD       — copy from the root of the game disc
		pn10ni11.dll  — copy from the SYSTEM\ folder of the installed game
		output_dir    — same directory as this script

	Examples:
		python extract_mcd1.py
		python extract_mcd1.py /mnt/cdrom/MCD1.CD
		python extract_mcd1.py MCD1.CD pn10ni11.dll ./out

Where to find the required files:
	MCD1.CD       lives in the root of the Muppets Inside CD-ROM.
				  It is the main asset container for all game artwork.

	pn10ni11.dll  is NOT on the disc.  It is installed by the game's
				  setup program into the SYSTEM\ subfolder of the install
				  directory (e.g. "C:\Program Files\Muppets Inside\SYSTEM\").
				  Copy it next to this script before running.

Output:
	<output_dir>/
		bmp/   — small 8-bpp BMP UI sprites, written as original .bmp files
		pic/   — JPEG "PIC" images (title screens, panel art, game images),
				 written as .jpg files with the missing DQT marker injected;
				 no re-encoding — pixel data is bit-for-bit identical to the
				 original compressed stream

========================================================================
BACKGROUND — WHY THIS SCRIPT EXISTS
========================================================================

Muppets Inside ships with a proprietary JPEG codec called Pegasus Imaging
(pn10ni11.dll, ~180 KB, compiled with WATCOM C++). The game stores all of
its large artwork as JFIF JPEG files inside the container MCD1.CD, but
with one crucial piece stripped out: the DQT marker (FF DB), which holds
the quantization tables that the JPEG decoder needs in order to reconstruct
the image correctly.

The Pegasus codec supplies those tables itself from its own hardcoded data,
so the on-disc files are intentionally incomplete — they cannot be opened
by any standard viewer (Windows Photo Viewer, GIMP, Photoshop, etc.) as-is.

This script reverse-engineers that process:
  1. Reads the standard libjpeg base quantization tables out of pn10ni11.dll.
  2. Derives the correct quality factor from each image's own APP1 header
     using the formula Q = 100 - 6 * (param2 - param1).
  3. Injects a well-formed DQT marker into each stripped JPEG and writes it
     as a standard .jpg file.  No re-encoding — the compressed pixel data
     is copied verbatim.

========================================================================
MCD1.CD FORMAT
========================================================================

MCD1.CD is a Starwave RIFF container:

	Offset 0x0000 : RIFF header (5004 bytes)
					  "RIFF" <size> "STWV"
						RSRC chunks — HEAD / DPND / DATA sub-chunks
						Maps numeric resource IDs ↔ (offset, size) pairs
						in the raw data stream below.
						NOTE: IDs are opaque integers; filenames live only
						in MUPPET.ASP (FDIR block), which stores an external
						flag (FF FF FF FF) instead of literal offsets, so
						the ID↔filename mapping is not resolved here.

	Offset 0x138C : Raw resource data stream (~29.2 MB)
					  BMP and JPEG files packed back-to-back, no padding.

We ignore the RIFF header entirely and scan the raw stream directly for
magic bytes:
	FF D8 FF  — JPEG SOI
	42 4D     — BMP signature ("BM")

This is robust: every image is found regardless of the ID mapping.

------------------------------------------------------------------------
BMP files (indices 0–46 in the stream, starting at 0x138C)
------------------------------------------------------------------------

46 small 8-bpp palettised Windows BMP files used as UI sprites and
buttons. Sizes range from 24×19 to ~90×70 pixels. A tiny 1×1 sentinel
BMP sits at 0x138C itself.

Each BMP's size is given in bytes 2–5 of its header (little-endian uint32),
so the extent is fully self-describing.

------------------------------------------------------------------------
JPEG "PIC" files
------------------------------------------------------------------------

The game's artwork. Every PIC file has this structure:

	FF D8           SOI
	FF E0 00 10     APP0 — JFIF marker
	  4A 46 49 46 00  "JFIF\0"
	  02 01           Version 2.1  (non-standard; treat as 1.1)
	  02              Density units: pixels/cm
	  00 1C 00 1C     Xdensity=28, Ydensity=28
	  00 00           No thumbnail
	FF E1 00 0A     APP1 — Starwave "PIC" marker (10 payload bytes)
	  50 49 43 00   "PIC\0"
	  01            version = 1
	  ??            param1  \
	  ??            param2   > quality hint (see formula below)
	  01            flags = 1
	FF C0 ...       SOF0 — baseline DCT
					  3 components, 4:2:0 YCbCr subsampling
	FF C4 ...       DHT  — Huffman tables (present and valid)
	FF DA ...       SOS  — scan header + entropy-coded data
	FF D9           EOI

Missing: FF DB DQT.  We inject it (see below).

------------------------------------------------------------------------
Quantization tables in pn10ni11.dll
------------------------------------------------------------------------

The standard libjpeg base quantization tables (Q=50 reference tables)
are stored in zigzag order inside pn10ni11.dll at:

	Luma   (table 0): offset 0x27540, 64 bytes
	Chroma (table 1): offset 0x27580, 64 bytes

These are the ANNEX K tables from the JPEG spec, identical to those
used by Independent JPEG Group's libjpeg.  Scaled to quality Q using:

	scale = 5000 // Q          if Q < 50
	scale = 200 - 2*Q          if Q >= 50

	entry = clamp(1, 255, (base_value * scale + 50) // 100)

Quality is NOT hardcoded — it is derived from the APP1 param bytes:

	Q = 100 - 6 * (param2 - param1)

Verified against two distinct (param1, param2) pairs found in MCD1.CD:

	param1=0x06, param2=0x08  ->  100 - 6*(8-6)  = 88   (82 images)
	param1=0x0C, param2=0x0F  ->  100 - 6*(15-12) = 82   (1 image)

Both values confirmed correct by visual inspection.

Example: at Q=88, scale = 200 - 176 = 24.

The DQT marker injected before SOF0:

	FF DB                   marker
	00 84                   length = 2 + 1 + 64 + 1 + 64 = 132
	00 <64 luma bytes>      table-id=0, luma entries (zigzag order)
	01 <64 chroma bytes>    table-id=1, chroma entries (zigzag order)

========================================================================
KNOWN IMAGE INVENTORY
========================================================================

The script finds and extracts all images automatically; this table is
provided for reference only.

	Offset      Raw size    Image size      Notes
	0x660B6     63,419 B    640×480         Title screen candidate 1
	0x75CB3     40,154 B    432×173         Strip / banner
	0x7FDCF     30,727 B    432×173         Strip / banner
	0x87A18     36,405 B    432×173         Strip / banner
	0x90C8F     33,003 B    432×173         Strip / banner
	0x991BC     32,336 B    432×173         Strip / banner
	0xA144E     31,774 B    432×173         Strip / banner
	0xA94AE     32,691 B    432×173         Strip / banner
	0xB18A3     31,121 B    432×173         Strip / banner
	0xB9676     37,301 B    432×173         Strip / banner
	0xC2C6D     33,304 B    432×173         Strip / banner
	0xCB64D     67,372 B    640×480         Title screen candidate 2
	0x23E3CA   149,122 B    640×480         Large title screen
	0x325263    80,511 B    640×480         Title screen
	0x3662E6    79,399 B    640×480         Title screen
	...plus additional images throughout the file

Named PIC resources (from MUPPET.ASP FDIR block — ID↔offset not mapped):
	D_SwedishChefTitle.pic    D_SuperGonzoTitle.pic
	D_MuppetSquaresTitle.pic  D_FozzieTitle.pic
	D_BeakersWorldTitle.pic   D_FinaleTitle.pic
	D_G6_01.pic … D_G6_10.pic
	D_ChangeGears_001–003.pic D_FO_Open.pic
	LPanel.pic  RPanel.pic    D_Roadmap.pic
	D_Session01C.pic  D_Session03.pic  D_Session06B.pic  D_Session10.pic
	D_Fozzie2.pic  D_GonzoPiggy.pic  D_StatlerWaldorf.pic

========================================================================
"""

import os
import struct
import sys


# ── Default paths ──────────────────────────────────────────────────────────────
#
# Both input files are expected next to this script by default.
# MCD1.CD comes from the game disc; pn10ni11.dll comes from the installed game.

_SCRIPT_DIR     = os.path.dirname(os.path.abspath(__file__))
_DEFAULT_MCD1   = os.path.join(_SCRIPT_DIR, 'MCD1.CD')
_DEFAULT_DLL    = os.path.join(_SCRIPT_DIR, 'pn10ni11.dll')
_DEFAULT_OUTDIR = _SCRIPT_DIR

# Offset in MCD1.CD where the raw resource data stream starts (immediately
# after the 5004-byte RIFF header).
_DATA_START = 0x138C

# Maximum plausible JPEG size (5 MB).  Any apparent JPEG larger than this
# is treated as a false positive and skipped.
_MAX_JPEG_SIZE = 5_000_000


# ── Quantization table helpers ─────────────────────────────────────────────────

def _load_qtables(dll_bytes):
	"""Read the Q=50 base quantization tables from pn10ni11.dll.

	The tables are stored in JPEG zigzag order at fixed offsets:
		Luma   (table 0): 0x27540
		Chroma (table 1): 0x27580

	Returns (luma_zigzag, chroma_zigzag) as lists of 64 ints.
	"""
	if len(dll_bytes) < 0x27580 + 64:
		raise ValueError(
			"pn10ni11.dll is too small — expected at least 0x275C0 bytes, "
			f"got {len(dll_bytes)}.  Wrong file?"
		)
	luma   = list(dll_bytes[0x27540 : 0x27540 + 64])
	chroma = list(dll_bytes[0x27580 : 0x27580 + 64])
	return luma, chroma


def _make_dqt_marker(quality, luma_zigzag, chroma_zigzag):
	"""Build a JPEG DQT marker for the given quality factor.

	Uses the standard libjpeg scaling formula:
		scale = 5000 // quality      if quality < 50
			  = 200 - 2 * quality    if quality >= 50
		entry = clamp(1, 255, (base * scale + 50) // 100)

	The marker contains both table 0 (luma) and table 1 (chroma), each
	preceded by their one-byte table-id, giving a total payload of
	2 + 65 + 65 = 132 bytes (including the length field itself).
	"""
	scale = 5000 // quality if quality < 50 else 200 - 2 * quality

	def _scale(table):
		return bytes(max(1, min(255, (v * scale + 50) // 100)) for v in table)

	payload = bytes([0]) + _scale(luma_zigzag) + bytes([1]) + _scale(chroma_zigzag)
	length  = len(payload) + 2          # +2 for the length field itself
	return b'\xff\xdb' + length.to_bytes(2, 'big') + payload


def _quality_from_pic_header(jpeg_bytes):
	"""Extract the JPEG quality factor from the Starwave APP1 'PIC' header.

	APP1 layout (offsets from SOI):
		+20  FF E1         APP1 marker
		+22  00 0A         length (10, includes self)
		+24  50 49 43 00   "PIC\\0"
		+28  01            version (always 1)
		+29  param1        \\
		+30  param2         > quality hint
		+31  01            flags

	Formula derived empirically from two confirmed (param1, param2) pairs:
		param1=0x06, param2=0x08  ->  Q=88
		param1=0x0C, param2=0x0F  ->  Q=82

		Q = 100 - 6 * (param2 - param1)
	"""
	param1, param2 = jpeg_bytes[29], jpeg_bytes[30]
	return 100 - 6 * (param2 - param1)


def _inject_dqt(jpeg_bytes, luma_zigzag, chroma_zigzag):
	"""Inject a DQT marker into jpeg_bytes immediately before SOF0 (FF C0).

	Quality is read from the image's own APP1 PIC header via
	_quality_from_pic_header(), so every image self-describes its tables.

	The DQT must appear before SOF0 so the decoder knows the quantization
	step before it processes the frame header.  All other markers (APP0,
	APP1, DHT, etc.) are left untouched.

	Raises ValueError if no SOF0 is found.
	"""
	quality = _quality_from_pic_header(jpeg_bytes)
	dqt     = _make_dqt_marker(quality, luma_zigzag, chroma_zigzag)
	sof0    = jpeg_bytes.find(b'\xff\xc0')
	if sof0 < 0:
		raise ValueError("No SOF0 marker (FF C0) found in JPEG data")
	return jpeg_bytes[:sof0] + dqt + jpeg_bytes[sof0:], quality


# ── MCD1.CD scanner ────────────────────────────────────────────────────────────

def _scan_images(data, start=_DATA_START):
	"""Scan the raw data stream of MCD1.CD for BMP and JPEG files.

	Strategy:
		- BMP: magic bytes 42 4D ("BM") at current position.  The file size
		  is stored as a little-endian uint32 at bytes 2–5 of the BMP header,
		  so the extent is self-describing.
		- JPEG: magic bytes FF D8 FF at current position.  Scan forward for
		  the EOI marker (FF D9) to find the end.  Cap at _MAX_JPEG_SIZE to
		  avoid false positives.

	Yields (kind, offset, raw_bytes) where kind is 'bmp' or 'jpeg'.
	"""
	pos = start
	end = len(data)

	while pos < end - 4:
		# ── BMP ──────────────────────────────────────────────────────────────
		if data[pos:pos+2] == b'BM':
			bmp_size = struct.unpack_from('<I', data, pos + 2)[0]
			if 54 <= bmp_size <= 10_000_000 and pos + bmp_size <= end:
				yield 'bmp', pos, data[pos : pos + bmp_size]
				pos += bmp_size
				continue

		# ── JPEG ─────────────────────────────────────────────────────────────
		# Only accept Starwave "PIC" format JPEGs.  These are identified by
		# the APP1 marker (FF E1) immediately after the APP0 block, with a
		# payload starting with "PIC\0".  The APP0 block is always 20 bytes
		# (FF E0 00 10 + 16-byte JFIF header), so APP1 starts at offset 20
		# from the SOI and "PIC\0" is at offset 24.
		#
		# Vanilla JPEG fragments, EXIF thumbnails, and other JFIF files that
		# happen to start with FF D8 FF do not have this marker and are
		# skipped.  This eliminates hundreds of false positives.
		if data[pos:pos+3] == b'\xff\xd8\xff':
			if data[pos+24:pos+28] == b'PIC\x00':
				eoi = data.find(b'\xff\xd9', pos + 2)
				if 0 < eoi - pos < _MAX_JPEG_SIZE and eoi + 2 <= end:
					yield 'jpeg', pos, data[pos : eoi + 2]
					pos = eoi + 2
					continue

		pos += 1


# ── Extraction ─────────────────────────────────────────────────────────────────

def extract(mcd1_path=_DEFAULT_MCD1, dll_path=_DEFAULT_DLL, out_dir=_DEFAULT_OUTDIR):
	"""Extract all images from MCD1.CD.

	BMP files are written out as-is (they are already valid Windows BMP files).
	JPEG "PIC" files have the missing DQT marker injected and are written as
	.jpg files.  No re-encoding takes place — the compressed pixel data is
	copied verbatim from MCD1.CD.

	Parameters
	----------
	mcd1_path : str
		Path to MCD1.CD (the Starwave RIFF container).
	dll_path : str
		Path to pn10ni11.dll (the Pegasus Imaging JPEG codec).
	out_dir : str
		Root output directory.  Sub-directories 'bmp/' and 'pic/' are
		created automatically.
	"""
	# ── Validate inputs ───────────────────────────────────────────────────────
	for path, label, hint in [
		(mcd1_path, 'MCD1.CD',      'copy it from the root of the game disc'),
		(dll_path,  'pn10ni11.dll', 'copy it from SYSTEM\\ in the installed game'),
	]:
		if not os.path.isfile(path):
			sys.exit(f"ERROR: {label} not found at: {path}\n"
					 f"  Hint: {hint}\n"
					 f"Usage: python extract_mcd1.py [MCD1.CD] [pn10ni11.dll] [output_dir]")

	# ── Load files ────────────────────────────────────────────────────────────
	print(f"Reading {mcd1_path} …")
	with open(mcd1_path, 'rb') as fh:
		mcd1 = fh.read()
	print(f"  {len(mcd1):,} bytes")

	print(f"Reading {dll_path} …")
	with open(dll_path, 'rb') as fh:
		dll = fh.read()

	# ── Load quantization base tables from the codec ──────────────────────────
	luma_zigzag, chroma_zigzag = _load_qtables(dll)
	print(f"  Q-table base tables loaded (luma @ 0x27540, chroma @ 0x27580)\n")

	# ── Prepare output directories ────────────────────────────────────────────
	bmp_dir = os.path.join(out_dir, 'bmp')
	pic_dir = os.path.join(out_dir, 'pic')
	os.makedirs(bmp_dir, exist_ok=True)
	os.makedirs(pic_dir, exist_ok=True)

	# ── Scan and extract ──────────────────────────────────────────────────────
	bmp_count = jpeg_count = err_count = 0

	for kind, offset, raw in _scan_images(mcd1):
		if kind == 'bmp':
			bmp_count += 1
			fname = f'bmp_{bmp_count:03d}_@{offset:07X}.bmp'
			out_path = os.path.join(bmp_dir, fname)
			try:
				width  = struct.unpack_from('<i', raw, 18)[0]
				height = abs(struct.unpack_from('<i', raw, 22)[0])
				with open(out_path, 'wb') as fh:
					fh.write(raw)
				print(f"  BMP  [{bmp_count:3d}]  0x{offset:07X}  "
					  f"{width}x{height}  ->  {out_path}")
			except Exception as exc:
				err_count += 1
				print(f"  BMP  [{bmp_count:3d}]  0x{offset:07X}  FAILED: {exc}")

		elif kind == 'jpeg':
			jpeg_count += 1
			try:
				patched, quality = _inject_dqt(raw, luma_zigzag, chroma_zigzag)
				# Read dimensions directly from the SOF0 marker rather than
				# decoding the image.  SOF0 (FF C0) payload: 1-byte precision,
				# then 2-byte height, 2-byte width (all big-endian).
				sof0 = patched.find(b'\xff\xc0')
				height, width = struct.unpack_from('>HH', patched, sof0 + 5)
				fname = f'pic_{jpeg_count:03d}_@{offset:07X}_{width}x{height}.jpg'
				out_path = os.path.join(pic_dir, fname)
				with open(out_path, 'wb') as fh:
					fh.write(patched)
				print(f"  PIC  [{jpeg_count:3d}]  0x{offset:07X}  "
					  f"{width}x{height}  Q={quality}  {len(raw):,} B  ->  {out_path}")
			except Exception as exc:
				err_count += 1
				print(f"  PIC  [{jpeg_count:3d}]  0x{offset:07X}  "
					  f"{len(raw):,} B  FAILED: {exc}")

	# ── Summary ───────────────────────────────────────────────────────────────
	print()
	print(f"Done.")
	print(f"  BMP images : {bmp_count}")
	print(f"  PIC images : {jpeg_count}")
	print(f"  Errors     : {err_count}")
	print(f"  Output     : {os.path.abspath(out_dir)}")


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == '__main__':
	args = sys.argv[1:]
	extract(
		mcd1_path = args[0] if len(args) > 0 else _DEFAULT_MCD1,
		dll_path  = args[1] if len(args) > 1 else _DEFAULT_DLL,
		out_dir   = args[2] if len(args) > 2 else _DEFAULT_OUTDIR,
	)
