#!/usr/bin/env python3
r"""
extract_games_lib.py — GAMES.LIB extractor for Muppets Inside (1996, Starwave)
===============================================================================
Zero dependencies — stdlib only.  DCL decompressor inlined at the bottom.

Usage:
	python3 extract_games_lib.py <games_lib> [output_dir] [filter]

	games_lib   path to GAMES.LIB (absolute or relative)
	output_dir  where to write extracted files (default: directory of this
	            script); files are written directly into this directory,
	            no "extracted" subdirectory is added
	filter      optional case-insensitive directory prefix, e.g. "chef"
	            omit to extract everything

Examples:
	python3 extract_games_lib.py D:/MuppetsInside/CD/GAMES.LIB
	python3 extract_games_lib.py GAMES.LIB ./out chef

===============================================================================
GAMES.LIB FORMAT REFERENCE
===============================================================================

Background
----------
GAMES.LIB ships on the Muppets Inside CD-ROM (Starwave, 1996). It holds all
assets for the mini-games, including The Swedish Chef's Kitchen of Doom.

The first 5 bytes match the InstallShield cabinet signature (13 5D 65 8C 3A),
but the rest of the format is entirely proprietary. Standard tools (unshield,
cabextract, 7-zip) all reject it.

Overall file layout
-------------------
	Offset      Section
	──────────────────────────────────────────────────
	0x000000    Header  (256 bytes, fixed size)
	0x000100    Data area — compressed file bodies
	0xDEBB21    Directory table (variable length)
	0xDEBC73    File table     (variable length)
	0xDF46E3    EOF  (14,632,675 bytes total)

All multi-byte integers are little-endian.

───────────────────────────────────────────────────────────────────────────────
SECTION 1 — HEADER (offset 0x000000, 256 bytes)
───────────────────────────────────────────────────────────────────────────────

	Bytes       Content
	─────────────────────────────────────────────────────────────────
	0x00–0x04   Signature: 13 5D 65 8C 3A  (shared with IS cabinets)
	0x05–0x28   Various unknown fields; not needed for extraction
	0x29–0x2B   uint24 LE — directory table offset  (= 0xDEBB21)
	0x2C–0x30   Unknown
	0x31–0x33   uint24 LE — file table offset        (= 0xDEBC73)
	0x34–0xFF   Unknown / zero padding

Only 0x29 and 0x31 are needed to parse the archive.

───────────────────────────────────────────────────────────────────────────────
SECTION 2 — DATA AREA (0x000100 – 0xDEBB20)
───────────────────────────────────────────────────────────────────────────────

Compressed file bodies packed back-to-back with no padding or alignment.
Each body is located by its absolute offset recorded in the file table.

Every body begins with a 2-byte PKWARE DCL header:
	Byte 0: 0x00 = binary mode  (0x01 = ASCII/text mode)
	Byte 1: dictionary size     (0x04 = 1 KB, 0x05 = 2 KB, 0x06 = 4 KB)

All files in GAMES.LIB use 0x00 0x06. This pair is a reliable validity test
when scanning candidate file entries.

───────────────────────────────────────────────────────────────────────────────
SECTION 3 — DIRECTORY TABLE (starts at 0xDEBB21)
───────────────────────────────────────────────────────────────────────────────

Flat list of 16 variable-length entries. No count prefix.
Iteration terminates when entry_size != name_len + 11.

Entry format:
	Offset  Size  Field
	──────────────────────────────────────────────────────────────────
	 0       2    field1      uint16 LE — roughly "file count in dir"
	 2       2    entry_size  uint16 LE — INVARIANT: entry_size == name_len + 11
	 4       2    name_len    uint16 LE
	 6       N    name        ASCII, no null terminator
							  Subdirs use backslash: "chef\\KITCHENS"
	6+N      5    zeros

Known directory index → name mapping:
	 0  beaker              8  clifford
	 1  beaker\CONTROL      9  clifford\CONTROL
	 2  chef               10  clifford\IMAGE
	 3  chef\FOODS         11  clifford\SAMPLES
	 4  chef\KITCHENS      12  fozzie
	 5  chef\LEVELS        13  gonzo
	 6  chef\MISC          14  gonzo\LEVELS
	 7  chef\UTENSILS      15  sandw

───────────────────────────────────────────────────────────────────────────────
SECTION 4 — FILE TABLE (starts at 0xDEBC73)
───────────────────────────────────────────────────────────────────────────────

4a. Preamble — 29 bytes (0xDEBC73–0xDEBC8F)
	The first 29 bytes are a table header whose full meaning is not decoded.
	Bytes 4–5 contain 0xCC 0x01 (= 460), possibly a partial file count.
	Skip these 29 bytes unconditionally to reach the first file entry.

4b. File entries (variable length, tightly packed, no padding between them)
	Advance (N + 43) bytes after each entry. Total valid entries: 642.

	Offset   Size  Field
	────────────────────────────────────────────────────────────────────────
	 0        1    name_length  (N)
	 1        N    filename     ASCII, uppercase, no path, no null terminator
	N+1      14    null_padding ALWAYS 14 zero bytes — structural anchor
	N+15      2    dir_index    uint16 LE — index into the directory table
	N+17      4    uncompressed_size  uint32 LE
	N+21      4    compressed_size   uint32 LE
	N+25      4    data_offset       uint32 LE — absolute offset in GAMES.LIB
									   Always in the data area; always 0x00 0x06
	N+29      2    file_date    uint16 LE, DOS date (bits 15-9=yr-1980, 8-5=mo, 4-0=day)
	N+31      2    file_time    uint16 LE, DOS time (bits 15-11=hr, 10-5=min, 4-0=sec/2)
	N+33      4    flags        uint32 LE — 0x00000080 most common for game assets
	N+37      1    next_entry_size — byte size of the *next* entry (= next_N + 43)
	N+38      5    zeros
	────────────────────────────────────────────────────────────────────────
	Total: N + 43 bytes

───────────────────────────────────────────────────────────────────────────────
SECTION 5 — COMPRESSION
───────────────────────────────────────────────────────────────────────────────

Algorithm: PKWARE DCL "blast" (a.k.a. DCL Implode)
	Implemented by Mark Adler's blast.c (zlib/contrib/blast/blast.c).
	Uses Shannon-Fano entropy coding + LZ77 back-references.
	NOT the same as ZIP compression method 6 (ZIP Implode), though related.

	The decompressor at the bottom of this file is derived from pwexplode
	by Sven Kochmann (https://github.com/Schallaven/pwexplode, GPL-3.0),
	which is itself based on blast.c and Ben Rudiak-Gould's comp.compression
	post (https://groups.google.com/d/msg/comp.compression/M5P064or93o/W1ca1-ad6kgJ).

Validation (known-plaintext):
	WAVEMIX.INI — data_offset=0xCA9A1A, compressed=36 bytes, uncompressed=49
	Decompresses to: "60\r\n70\r\n-1\r\n0\r\n0\r\n100\r\n300\r\n180\r\n100\r\n1 620 180\r\n"

───────────────────────────────────────────────────────────────────────────────
SECTION 6 — OTHER FILES
───────────────────────────────────────────────────────────────────────────────

Same script also happens to work on _SETUP.LIB to get a few extra bitmaps.
Extracts MuppetSE.DLL from DLLS.LIB as well.

The CDX files on the disc are actually AVIs using CinePak video compression.
ffmpeg will convert them directly:
ffmpeg -i CNV53BDK.CDX -c:v libx264 -pix_fmt yuv420p -c:a aac -b:a 128k MuppetsInside.mp4

The Swedish Chef's Kitchen of Doom's sounds are WAVs under 5\SOUNDS

===============================================================================
END OF FORMAT REFERENCE
===============================================================================
"""

import os
import struct
import sys

# ─── Main ──────────────────────────────────────────────────────────────────────

def main():
	script_dir = os.path.dirname(os.path.abspath(__file__))

	games_lib  = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.join(script_dir, 'GAMES.LIB')
	out_root   = os.path.abspath(sys.argv[2]) if len(sys.argv) > 2 else script_dir
	dir_filter = sys.argv[3].lower()          if len(sys.argv) > 3 else None

	if not os.path.exists(games_lib):
		sys.exit("ERROR: %s not found.\nUsage: extract_games_lib.py [games_lib] [output_dir] [filter]" % games_lib)

	print("Loading %s …" % games_lib)
	with open(games_lib, 'rb') as fh:
		raw = fh.read()
	print("  %d bytes (0x%X)\n" % (len(raw), len(raw)))

	# ── Read directory table offset from the file header ─────────────────────
	#
	# Header bytes 0x29–0x2B hold the directory table offset as a uint24 LE.
	# Reading it at runtime means this script works for any archive that uses
	# the same Starwave format, regardless of its exact layout.
	dir_table_offset = int.from_bytes(raw[0x29:0x2C], 'little')
	print("  dir_table_offset = 0x%X (from header 0x29–0x2B)\n" % dir_table_offset)

	# All valid data_offset values must be below the directory table.
	data_area_end = dir_table_offset

	# ── Parse directory table ─────────────────────────────────────────────────
	#
	# Read entries until the invariant (entry_size == name_len + 11) breaks.

	dirs = []
	off  = dir_table_offset

	while off + 6 < len(raw):
		_field1, entry_size, name_len = struct.unpack_from('<HHH', raw, off)
		if entry_size != name_len + 11 or not (0 < name_len < 100):
			break
		dirs.append(raw[off + 6 : off + 6 + name_len].decode('ascii', errors='replace'))
		off += entry_size

	file_table_start = off  # byte immediately following the last directory entry

	print("=== Directories (%d) ===" % len(dirs))
	for i, d in enumerate(dirs):
		print("  [%2d] %s" % (i, d))
	print()

	# ── Parse file table ──────────────────────────────────────────────────────
	#
	# The file table has an undecoded preamble of unknown length before the
	# first entry. Scan forward from file_table_start until we find a byte
	# sequence that satisfies the entry invariants:
	#   - N in 1..64
	#   - N bytes of printable ASCII immediately follow
	#   - 14 null bytes follow the name
	# This makes the preamble length fully dynamic.

	off = file_table_start
	while off + 43 < len(raw):
		N = raw[off]
		if (1 <= N <= 64
				and all(0x20 <= b <= 0x7E for b in raw[off + 1 : off + 1 + N])
				and raw[off + 1 + N : off + 1 + N + 14] == b'\x00' * 14):
			break
		off += 1
	else:
		sys.exit("ERROR: could not locate start of file entries in file table")

	preamble = off - file_table_start
	print("  file_table_start = 0x%X  preamble = %d bytes\n" % (file_table_start, preamble))

	files = []

	while off + 43 < len(raw):
		N = raw[off]
		if N == 0 or N > 64:
			break  # end of table

		filename = raw[off + 1 : off + 1 + N].decode('ascii', errors='replace')

		# 14 null bytes are a reliable structural anchor — verify them.
		if raw[off + 1 + N : off + 1 + N + 14] != b'\x00' * 14:
			break

		meta              = off + 1 + N + 14
		dir_index         = struct.unpack_from('<H', raw, meta     )[0]
		uncompressed_size = struct.unpack_from('<I', raw, meta +  2)[0]
		compressed_size   = struct.unpack_from('<I', raw, meta +  6)[0]
		data_offset       = struct.unpack_from('<I', raw, meta + 10)[0]
		# DOS date/time at meta+14, meta+16 and flags at meta+18 are
		# parsed implicitly by the N+43 step; not needed for extraction.

		# Validity: offset must be in the data area and start with 0x00 0x06.
		if (0x200 < data_offset < data_area_end
				and 0 < compressed_size <= uncompressed_size <= 50_000_000
				and raw[data_offset] == 0x00
				and raw[data_offset + 1] == 0x06):
			dir_name = dirs[dir_index] if dir_index < len(dirs) else ("dir%d" % dir_index)
			files.append((filename, dir_name, uncompressed_size, compressed_size, data_offset))

		off += N + 43

	print("=== File table: %d valid entries ===\n" % len(files))

	# ── Optional filter ───────────────────────────────────────────────────────

	if dir_filter:
		files = [f for f in files if f[1].lower().startswith(dir_filter)]
		print("After filter '%s': %d files\n" % (dir_filter, len(files)))

	# ── Extract ───────────────────────────────────────────────────────────────

	ok = err = 0

	for filename, dir_name, uncomp, comp, data_off in files:
		out_dir  = os.path.join(out_root, dir_name.replace('\\', os.sep))
		out_path = os.path.join(out_dir, filename)
		os.makedirs(out_dir, exist_ok=True)

		try:
			decompressed = dcl_explode(raw[data_off : data_off + comp])
		except Exception as exc:
			print("  FAIL  %s\\%s — %s" % (dir_name, filename, exc))
			err += 1
			continue

		if len(decompressed) != uncomp:
			print("  WARN  %s\\%s  expected %d bytes, got %d"
				  % (dir_name, filename, uncomp, len(decompressed)))

		with open(out_path, 'wb') as fh:
			fh.write(decompressed)
		ok += 1

	print("Done: %d extracted, %d errors" % (ok, err))
	print("Output: %s" % out_root)


# ═══════════════════════════════════════════════════════════════════════════════
#  PKWARE DCL "blast" decompressor
#
#  Derived from pwexplode by Sven Kochmann (GPL-3.0)
#    https://github.com/Schallaven/pwexplode
#  Which is based on blast.c by Mark Adler (zlib/contrib/blast)
#  and Ben Rudiak-Gould's comp.compression post.
#
#  The three lookup tables below are the Shannon-Fano trees for:
#    _DCL_LITERALS  — byte values (for coded-literal mode)
#    _DCL_LENGTHS   — copy lengths (2–519; 519 = end-of-stream)
#    _DCL_OFFSETS   — high bits of back-reference distance
#
#  Keys are LSB-first bit-pattern strings; values are decoded integers.
# ═══════════════════════════════════════════════════════════════════════════════

_DCL_LITERALS = {
	"1111": 0x20, "11101": 0x45, "11100": 0x61, "11011": 0x65, "11010": 0x69,
	"11001": 0x6c, "11000": 0x6e, "10111": 0x6f, "10110": 0x72, "10101": 0x73,
	"10100": 0x74, "10011": 0x75, "100101": 0x2d, "100100": 0x31, "100011": 0x41,
	"100010": 0x43, "100001": 0x44, "100000": 0x49, "011111": 0x4c, "011110": 0x4e,
	"011101": 0x4f, "011100": 0x52, "011011": 0x53, "011010": 0x54, "011001": 0x62,
	"011000": 0x63, "010111": 0x64, "010110": 0x66, "010101": 0x67, "010100": 0x68,
	"010011": 0x6d, "010010": 0x70, "0100011": 0x0a, "0100010": 0x0d, "0100001": 0x28,
	"0100000": 0x29, "0011111": 0x2c, "0011110": 0x2e, "0011101": 0x30, "0011100": 0x32,
	"0011011": 0x33, "0011010": 0x34, "0011001": 0x35, "0011000": 0x37, "0010111": 0x38,
	"0010110": 0x3d, "0010101": 0x42, "0010100": 0x46, "0010011": 0x4d, "0010010": 0x50,
	"0010001": 0x55, "0010000": 0x6b, "0001111": 0x77, "00011101": 0x09, "00011100": 0x22,
	"00011011": 0x27, "00011010": 0x2a, "00011001": 0x2f, "00011000": 0x36, "00010111": 0x39,
	"00010110": 0x3a, "00010101": 0x47, "00010100": 0x48, "00010011": 0x57, "00010010": 0x5b,
	"00010001": 0x5f, "00010000": 0x76, "00001111": 0x78, "00001110": 0x79, "000011011": 0x2b,
	"000011010": 0x3e, "000011001": 0x4b, "000011000": 0x56, "000010111": 0x58, "000010110": 0x59,
	"000010101": 0x5d, "0000101001": 0x21, "0000101000": 0x24, "0000100111": 0x26,
	"0000100110": 0x71, "0000100101": 0x7a, "00001001001": 0x00, "00001001000": 0x3c,
	"00001000111": 0x3f, "00001000110": 0x4a, "00001000101": 0x51, "00001000100": 0x5a,
	"00001000011": 0x5c, "00001000010": 0x6a, "00001000001": 0x7b, "00001000000": 0x7c,
	"000001111111": 0x01, "000001111110": 0x02, "000001111101": 0x03, "000001111100": 0x04,
	"000001111011": 0x05, "000001111010": 0x06, "000001111001": 0x07, "000001111000": 0x08,
	"000001110111": 0x0b, "000001110110": 0x0c, "000001110101": 0x0e, "000001110100": 0x0f,
	"000001110011": 0x10, "000001110010": 0x11, "000001110001": 0x12, "000001110000": 0x13,
	"000001101111": 0x14, "000001101110": 0x15, "000001101101": 0x16, "000001101100": 0x17,
	"000001101011": 0x18, "000001101010": 0x19, "000001101001": 0x1b, "000001101000": 0x1c,
	"000001100111": 0x1d, "000001100110": 0x1e, "000001100101": 0x1f, "000001100100": 0x23,
	"000001100011": 0x25, "000001100010": 0x3b, "000001100001": 0x40, "000001100000": 0x5e,
	"000001011111": 0x60, "000001011110": 0x7d, "000001011101": 0x7e, "000001011100": 0x7f,
	"000001011011": 0xb0, "000001011010": 0xb1, "000001011001": 0xb2, "000001011000": 0xb3,
	"000001010111": 0xb4, "000001010110": 0xb5, "000001010101": 0xb6, "000001010100": 0xb7,
	"000001010011": 0xb8, "000001010010": 0xb9, "000001010001": 0xba, "000001010000": 0xbb,
	"000001001111": 0xbc, "000001001110": 0xbd, "000001001101": 0xbe, "000001001100": 0xbf,
	"000001001011": 0xc0, "000001001010": 0xc1, "000001001001": 0xc2, "000001001000": 0xc3,
	"000001000111": 0xc4, "000001000110": 0xc5, "000001000101": 0xc6, "000001000100": 0xc7,
	"000001000011": 0xc8, "000001000010": 0xc9, "000001000001": 0xca, "000001000000": 0xcb,
	"000000111111": 0xcc, "000000111110": 0xcd, "000000111101": 0xce, "000000111100": 0xcf,
	"000000111011": 0xd0, "000000111010": 0xd1, "000000111001": 0xd2, "000000111000": 0xd3,
	"000000110111": 0xd4, "000000110110": 0xd5, "000000110101": 0xd6, "000000110100": 0xd7,
	"000000110011": 0xd8, "000000110010": 0xd9, "000000110001": 0xda, "000000110000": 0xdb,
	"000000101111": 0xdc, "000000101110": 0xdd, "000000101101": 0xde, "000000101100": 0xdf,
	"000000101011": 0xe1, "000000101010": 0xe5, "000000101001": 0xe9, "000000101000": 0xee,
	"000000100111": 0xf2, "000000100110": 0xf3, "000000100101": 0xf4, "0000001001001": 0x1a,
	"0000001001000": 0x80, "0000001000111": 0x81, "0000001000110": 0x82, "0000001000101": 0x83,
	"0000001000100": 0x84, "0000001000011": 0x85, "0000001000010": 0x86, "0000001000001": 0x87,
	"0000001000000": 0x88, "0000000111111": 0x89, "0000000111110": 0x8a, "0000000111101": 0x8b,
	"0000000111100": 0x8c, "0000000111011": 0x8d, "0000000111010": 0x8e, "0000000111001": 0x8f,
	"0000000111000": 0x90, "0000000110111": 0x91, "0000000110110": 0x92, "0000000110101": 0x93,
	"0000000110100": 0x94, "0000000110011": 0x95, "0000000110010": 0x96, "0000000110001": 0x97,
	"0000000110000": 0x98, "0000000101111": 0x99, "0000000101110": 0x9a, "0000000101101": 0x9b,
	"0000000101100": 0x9c, "0000000101011": 0x9d, "0000000101010": 0x9e, "0000000101001": 0x9f,
	"0000000101000": 0xa0, "0000000100111": 0xa1, "0000000100110": 0xa2, "0000000100101": 0xa3,
	"0000000100100": 0xa4, "0000000100011": 0xa5, "0000000100010": 0xa6, "0000000100001": 0xa7,
	"0000000100000": 0xa8, "0000000011111": 0xa9, "0000000011110": 0xaa, "0000000011101": 0xab,
	"0000000011100": 0xac, "0000000011011": 0xad, "0000000011010": 0xae, "0000000011001": 0xaf,
	"0000000011000": 0xe0, "0000000010111": 0xe2, "0000000010110": 0xe3, "0000000010101": 0xe4,
	"0000000010100": 0xe6, "0000000010011": 0xe7, "0000000010010": 0xe8, "0000000010001": 0xea,
	"0000000010000": 0xeb, "0000000001111": 0xec, "0000000001110": 0xed, "0000000001101": 0xef,
	"0000000001100": 0xf0, "0000000001011": 0xf1, "0000000001010": 0xf5, "0000000001001": 0xf6,
	"0000000001000": 0xf7, "0000000000111": 0xf8, "0000000000110": 0xf9, "0000000000101": 0xfa,
	"0000000000100": 0xfb, "0000000000011": 0xfc, "0000000000010": 0xfd, "0000000000001": 0xfe,
	"0000000000000": 0xff,
}

_DCL_LENGTHS = {
	# Source: pwexplode by Sven Kochmann (https://github.com/Schallaven/pwexplode)
	# These are the actual Shannon-Fano codes from the PKWARE DCL spec.
	# Keys are LSB-first bit-pattern strings; values are copy lengths.
	# Length 519 is the end-of-stream sentinel.
	"11": 3, "101": 2, "100": 4, "011": 5, "0101": 6, "0100": 7, "0011": 8,
	"00101": 9, "001001": 11, "001000": 10, "0001111": 15, "0001110": 13,
	"0001101": 14, "0001100": 12, "00010111": 23, "00010110": 19, "00010101": 21,
	"00010100": 17, "00010011": 22, "00010010": 18, "00010001": 20, "00010000": 16,
	"0000111111": 39, "0000111110": 31, "0000111101": 35, "0000111100": 27,
	"0000111011": 37, "0000111010": 29, "0000111001": 33, "0000111000": 25,
	"0000110111": 38, "0000110110": 30, "0000110101": 34, "0000110100": 26,
	"0000110011": 36, "0000110010": 28, "0000110001": 32, "0000110000": 24,
	"00001011111": 71, "00001011110": 55, "00001011101": 63, "00001011100": 47,
	"00001011011": 67, "00001011010": 51, "00001011001": 59, "00001011000": 43,
	"00001010111": 69, "00001010110": 53, "00001010101": 61, "00001010100": 45,
	"00001010011": 65, "00001010010": 49, "00001010001": 57, "00001010000": 41,
	"00001001111": 70, "00001001110": 54, "00001001101": 62, "00001001100": 46,
	"00001001011": 66, "00001001010": 50, "00001001001": 58, "00001001000": 42,
	"00001000111": 68, "00001000110": 52, "00001000101": 60, "00001000100": 44,
	"00001000011": 64, "00001000010": 48, "00001000001": 56, "00001000000": 40,
	"000001111111": 135, "000001111110": 103, "000001111101": 119, "000001111100": 87,
	"000001111011": 127, "000001111010": 95, "000001111001": 111, "000001111000": 79,
	"000001110111": 131, "000001110110": 99, "000001110101": 115, "000001110100": 83,
	"000001110011": 123, "000001110010": 91, "000001110001": 107, "000001110000": 75,
	"000001101111": 133, "000001101110": 101, "000001101101": 117, "000001101100": 85,
	"000001101011": 125, "000001101010": 93, "000001101001": 109, "000001101000": 77,
	"000001100111": 129, "000001100110": 97, "000001100101": 113, "000001100100": 81,
	"000001100011": 121, "000001100010": 89, "000001100001": 105, "000001100000": 73,
	"000001011111": 134, "000001011110": 102, "000001011101": 118, "000001011100": 86,
	"000001011011": 126, "000001011010": 94, "000001011001": 110, "000001011000": 78,
	"000001010111": 130, "000001010110": 98, "000001010101": 114, "000001010100": 82,
	"000001010011": 122, "000001010010": 90, "000001010001": 106, "000001010000": 74,
	"000001001111": 132, "000001001110": 100, "000001001101": 116, "000001001100": 84,
	"000001001011": 124, "000001001010": 92, "000001001001": 108, "000001001000": 76,
	"000001000111": 128, "000001000110": 96, "000001000101": 112, "000001000100": 80,
	"000001000011": 120, "000001000010": 88, "000001000001": 104, "000001000000": 72,
	"00000011111111": 263, "00000011111110": 199, "00000011111101": 231,
	"00000011111100": 167, "00000011111011": 247, "00000011111010": 183,
	"00000011111001": 215, "00000011111000": 151, "00000011110111": 255,
	"00000011110110": 191, "00000011110101": 223, "00000011110100": 159,
	"00000011110011": 239, "00000011110010": 175, "00000011110001": 207,
	"00000011110000": 143, "00000011101111": 259, "00000011101110": 195,
	"00000011101101": 227, "00000011101100": 163, "00000011101011": 243,
	"00000011101010": 179, "00000011101001": 211, "00000011101000": 147,
	"00000011100111": 251, "00000011100110": 187, "00000011100101": 219,
	"00000011100100": 155, "00000011100011": 235, "00000011100010": 171,
	"00000011100001": 203, "00000011100000": 139, "00000011011111": 261,
	"00000011011110": 197, "00000011011101": 229, "00000011011100": 165,
	"00000011011011": 245, "00000011011010": 181, "00000011011001": 213,
	"00000011011000": 149, "00000011010111": 253, "00000011010110": 189,
	"00000011010101": 221, "00000011010100": 157, "00000011010011": 237,
	"00000011010010": 173, "00000011010001": 205, "00000011010000": 141,
	"00000011001111": 257, "00000011001110": 193, "00000011001101": 225,
	"00000011001100": 161, "00000011001011": 241, "00000011001010": 177,
	"00000011001001": 209, "00000011001000": 145, "00000011000111": 249,
	"00000011000110": 185, "00000011000101": 217, "00000011000100": 153,
	"00000011000011": 233, "00000011000010": 169, "00000011000001": 201,
	"00000011000000": 137, "00000010111111": 262, "00000010111110": 198,
	"00000010111101": 230, "00000010111100": 166, "00000010111011": 246,
	"00000010111010": 182, "00000010111001": 214, "00000010111000": 150,
	"00000010110111": 254, "00000010110110": 190, "00000010110101": 222,
	"00000010110100": 158, "00000010110011": 238, "00000010110010": 174,
	"00000010110001": 206, "00000010110000": 142, "00000010101111": 258,
	"00000010101110": 194, "00000010101101": 226, "00000010101100": 162,
	"00000010101011": 242, "00000010101010": 178, "00000010101001": 210,
	"00000010101000": 146, "00000010100111": 250, "00000010100110": 186,
	"00000010100101": 218, "00000010100100": 154, "00000010100011": 234,
	"00000010100010": 170, "00000010100001": 202, "00000010100000": 138,
	"00000010011111": 260, "00000010011110": 196, "00000010011101": 228,
	"00000010011100": 164, "00000010011011": 244, "00000010011010": 180,
	"00000010011001": 212, "00000010011000": 148, "00000010010111": 252,
	"00000010010110": 188, "00000010010101": 220, "00000010010100": 156,
	"00000010010011": 236, "00000010010010": 172, "00000010010001": 204,
	"00000010010000": 140, "00000010001111": 256, "00000010001110": 192,
	"00000010001101": 224, "00000010001100": 160, "00000010001011": 240,
	"00000010001010": 176, "00000010001001": 208, "00000010001000": 144,
	"00000010000111": 248, "00000010000110": 184, "00000010000101": 216,
	"00000010000100": 152, "00000010000011": 232, "00000010000010": 168,
	"00000010000001": 200, "00000010000000": 136, "000000011111111": 519,
	"000000011111110": 391, "000000011111101": 455, "000000011111100": 327,
	"000000011111011": 487, "000000011111010": 359, "000000011111001": 423,
	"000000011111000": 295, "000000011110111": 503, "000000011110110": 375,
	"000000011110101": 439, "000000011110100": 311, "000000011110011": 471,
	"000000011110010": 343, "000000011110001": 407, "000000011110000": 279,
	"000000011101111": 511, "000000011101110": 383, "000000011101101": 447,
	"000000011101100": 319, "000000011101011": 479, "000000011101010": 351,
	"000000011101001": 415, "000000011101000": 287, "000000011100111": 495,
	"000000011100110": 367, "000000011100101": 431, "000000011100100": 303,
	"000000011100011": 463, "000000011100010": 335, "000000011100001": 399,
	"000000011100000": 271, "000000011011111": 515, "000000011011110": 387,
	"000000011011101": 451, "000000011011100": 323, "000000011011011": 483,
	"000000011011010": 355, "000000011011001": 419, "000000011011000": 291,
	"000000011010111": 499, "000000011010110": 371, "000000011010101": 435,
	"000000011010100": 307, "000000011010011": 467, "000000011010010": 339,
	"000000011010001": 403, "000000011010000": 275, "000000011001111": 507,
	"000000011001110": 379, "000000011001101": 443, "000000011001100": 315,
	"000000011001011": 475, "000000011001010": 347, "000000011001001": 411,
	"000000011001000": 283, "000000011000111": 491, "000000011000110": 363,
	"000000011000101": 427, "000000011000100": 299, "000000011000011": 459,
	"000000011000010": 331, "000000011000001": 395, "000000011000000": 267,
	"000000010111111": 517, "000000010111110": 389, "000000010111101": 453,
	"000000010111100": 325, "000000010111011": 485, "000000010111010": 357,
	"000000010111001": 421, "000000010111000": 293, "000000010110111": 501,
	"000000010110110": 373, "000000010110101": 437, "000000010110100": 309,
	"000000010110011": 469, "000000010110010": 341, "000000010110001": 405,
	"000000010110000": 277, "000000010101111": 509, "000000010101110": 381,
	"000000010101101": 445, "000000010101100": 317, "000000010101011": 477,
	"000000010101010": 349, "000000010101001": 413, "000000010101000": 285,
	"000000010100111": 493, "000000010100110": 365, "000000010100101": 429,
	"000000010100100": 301, "000000010100011": 461, "000000010100010": 333,
	"000000010100001": 397, "000000010100000": 269, "000000010011111": 513,
	"000000010011110": 385, "000000010011101": 449, "000000010011100": 321,
	"000000010011011": 481, "000000010011010": 353, "000000010011001": 417,
	"000000010011000": 289, "000000010010111": 497, "000000010010110": 369,
	"000000010010101": 433, "000000010010100": 305, "000000010010011": 465,
	"000000010010010": 337, "000000010010001": 401, "000000010010000": 273,
	"000000010001111": 505, "000000010001110": 377, "000000010001101": 441,
	"000000010001100": 313, "000000010001011": 473, "000000010001010": 345,
	"000000010001001": 409, "000000010001000": 281, "000000010000111": 489,
	"000000010000110": 361, "000000010000101": 425, "000000010000100": 297,
	"000000010000011": 457, "000000010000010": 329, "000000010000001": 393,
	"000000010000000": 265, "000000001111111": 518, "000000001111110": 390,
	"000000001111101": 454, "000000001111100": 326, "000000001111011": 486,
	"000000001111010": 358, "000000001111001": 422, "000000001111000": 294,
	"000000001110111": 502, "000000001110110": 374, "000000001110101": 438,
	"000000001110100": 310, "000000001110011": 470, "000000001110010": 342,
	"000000001110001": 406, "000000001110000": 278, "000000001101111": 510,
	"000000001101110": 382, "000000001101101": 446, "000000001101100": 318,
	"000000001101011": 478, "000000001101010": 350, "000000001101001": 414,
	"000000001101000": 286, "000000001100111": 494, "000000001100110": 366,
	"000000001100101": 430, "000000001100100": 302, "000000001100011": 462,
	"000000001100010": 334, "000000001100001": 398, "000000001100000": 270,
	"000000001011111": 514, "000000001011110": 386, "000000001011101": 450,
	"000000001011100": 322, "000000001011011": 482, "000000001011010": 354,
	"000000001011001": 418, "000000001011000": 290, "000000001010111": 498,
	"000000001010110": 370, "000000001010101": 434, "000000001010100": 306,
	"000000001010011": 466, "000000001010010": 338, "000000001010001": 402,
	"000000001010000": 274, "000000001001111": 506, "000000001001110": 378,
	"000000001001101": 442, "000000001001100": 314, "000000001001011": 474,
	"000000001001010": 346, "000000001001001": 410, "000000001001000": 282,
	"000000001000111": 490, "000000001000110": 362, "000000001000101": 426,
	"000000001000100": 298, "000000001000011": 458, "000000001000010": 330,
	"000000001000001": 394, "000000001000000": 266, "000000000111111": 516,
	"000000000111110": 388, "000000000111101": 452, "000000000111100": 324,
	"000000000111011": 484, "000000000111010": 356, "000000000111001": 420,
	"000000000111000": 292, "000000000110111": 500, "000000000110110": 372,
	"000000000110101": 436, "000000000110100": 308, "000000000110011": 468,
	"000000000110010": 340, "000000000110001": 404, "000000000110000": 276,
	"000000000101111": 508, "000000000101110": 380, "000000000101101": 444,
	"000000000101100": 316, "000000000101011": 476, "000000000101010": 348,
	"000000000101001": 412, "000000000101000": 284, "000000000100111": 492,
	"000000000100110": 364, "000000000100101": 428, "000000000100100": 300,
	"000000000100011": 460, "000000000100010": 332, "000000000100001": 396,
	"000000000100000": 268, "000000000011111": 512, "000000000011110": 384,
	"000000000011101": 448, "000000000011100": 320, "000000000011011": 480,
	"000000000011010": 352, "000000000011001": 416, "000000000011000": 288,
	"000000000010111": 496, "000000000010110": 368, "000000000010101": 432,
	"000000000010100": 304, "000000000010011": 464, "000000000010010": 336,
	"000000000010001": 400, "000000000010000": 272, "000000000001111": 504,
	"000000000001110": 376, "000000000001101": 440, "000000000001100": 312,
	"000000000001011": 472, "000000000001010": 344, "000000000001001": 408,
	"000000000001000": 280, "000000000000111": 488, "000000000000110": 360,
	"000000000000101": 424, "000000000000100": 296, "000000000000011": 456,
	"000000000000010": 328, "000000000000001": 392, "000000000000000": 264,
}

_DCL_OFFSETS = {
	"11": 0x00, "1011": 0x01, "1010": 0x02, "10011": 0x03, "10010": 0x04,
	"10001": 0x05, "10000": 0x06, "011111": 0x07, "011110": 0x08, "011101": 0x09,
	"011100": 0x0a, "011011": 0x0b, "011010": 0x0c, "011001": 0x0d, "011000": 0x0e,
	"010111": 0x0f, "010110": 0x10, "010101": 0x11, "010100": 0x12, "010011": 0x13,
	"010010": 0x14, "010001": 0x15, "0100001": 0x16, "0100000": 0x17, "0011111": 0x18,
	"0011110": 0x19, "0011101": 0x1a, "0011100": 0x1b, "0011011": 0x1c, "0011010": 0x1d,
	"0011001": 0x1e, "0011000": 0x1f, "0010111": 0x20, "0010110": 0x21, "0010101": 0x22,
	"0010100": 0x23, "0010011": 0x24, "0010010": 0x25, "0010001": 0x26, "0010000": 0x27,
	"0001111": 0x28, "0001110": 0x29, "0001101": 0x2a, "0001100": 0x2b, "0001011": 0x2c,
	"0001010": 0x2d, "0001001": 0x2e, "0001000": 0x2f, "00001111": 0x30, "00001110": 0x31,
	"00001101": 0x32, "00001100": 0x33, "00001011": 0x34, "00001010": 0x35, "00001001": 0x36,
	"00001000": 0x37, "00000111": 0x38, "00000110": 0x39, "00000101": 0x3a, "00000100": 0x3b,
	"00000011": 0x3c, "00000010": 0x3d, "00000001": 0x3e, "00000000": 0x3f,
}


def dcl_explode(data):
	"""Decompress a PKWARE DCL 'blast' byte string. Returns decompressed bytes.

	Header (2 bytes):
	  data[0]: literal mode — 0=raw 8-bit, 1=Shannon-Fano coded
	  data[1]: dict size    — 4=1KB, 5=2KB, 6=4KB sliding window

	Bitstream is LSB-first within each byte. After the 2-byte header, tokens
	alternate between:
	  bit=0  → literal (8 raw bits, or variable-width coded bits)
	  bit=1  → back-reference: length (from _DCL_LENGTHS) + distance prefix
			   (from _DCL_OFFSETS) + low bits determined by dict size
	Length 519 is the end-of-stream sentinel.
	"""
	coded    = data[0]          # 0 = raw literals, 1 = coded literals
	dictbits = data[1]          # low-bit count for distance = 4, 5, or 6

	if dictbits not in (4, 5, 6):
		raise ValueError("DCL: unsupported dict size byte %d" % dictbits)

	# Expand all bytes into an LSB-first bit string, skip the 2-byte header.
	bits = "".join("{:08b}".format(b)[::-1] for b in data)[16:]
	blen = len(bits)

	out = bytearray()
	pos = 0

	while pos < blen:
		kind = bits[pos];  pos += 1

		if kind == '0':
			# ── Literal ──────────────────────────────────────────────────────
			if coded:
				# Grow window 1 bit at a time until we match the SF tree.
				buf = bits[pos : pos + 4]
				while len(buf) <= 13:
					if buf in _DCL_LITERALS:
						out.append(_DCL_LITERALS[buf])
						pos += len(buf)
						break
					buf = bits[pos : pos + len(buf) + 1]
				else:
					raise RuntimeError("DCL: coded literal not found")
			else:
				# Raw: next 8 bits are the byte value (LSB first).
				out.append(int(bits[pos : pos + 8][::-1], 2))
				pos += 8

		else:
			# ── Back-reference ────────────────────────────────────────────────
			# Step 1: decode copy length.
			buf = bits[pos : pos + 2]
			while len(buf) <= 15:
				if buf in _DCL_LENGTHS:
					length = _DCL_LENGTHS[buf];  pos += len(buf)
					break
				buf = bits[pos : pos + len(buf) + 1]
			else:
				raise RuntimeError("DCL: length code not found")

			if length == 519:
				break   # end-of-stream sentinel

			# Step 2: decode distance prefix (high bits).
			buf = bits[pos : pos + 2]
			while len(buf) <= 8:
				if buf in _DCL_OFFSETS:
					dist_hi = _DCL_OFFSETS[buf];  pos += len(buf)
					break
				buf = bits[pos : pos + len(buf) + 1]
			else:
				raise RuntimeError("DCL: offset code not found")

			# Step 3: read low bits of distance.
			# length==2 always uses 2 low bits; longer copies use dictbits.
			low_n = 2 if length == 2 else dictbits
			low   = int(bits[pos : pos + low_n][::-1], 2)
			pos  += low_n
			dist  = (dist_hi << low_n) | low

			# Step 4: copy `length` bytes from output[-(dist+1)].
			# Byte-by-byte to handle overlapping RLE-style runs correctly.
			src = len(out) - dist - 1
			for _ in range(length):
				out.append(out[src]);  src += 1

	return bytes(out)


if __name__ == '__main__':
	main()
