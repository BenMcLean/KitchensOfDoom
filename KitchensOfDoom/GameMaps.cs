namespace KitchensOfDoom;

public static class GameMaps
{
	// ── Constants ────────────────────────────────────────────────────────────

	private const ushort GridSize   = 256;
	private const byte   VoidCell   = 0xFF;
	private const ushort RlewTag    = 0xABCD;

	// Carmack compression tags — match GameMap.CARMACK_NEAR / CARMACK_FAR
	// BenMcLean.Wolf3D.Assets.Gameplay.GameMap (ID_CA.C)
	private const byte CarmackNear = 0xA7;
	private const byte CarmackFar  = 0xA8;

	// Wolf3D object-plane player spawn codes (WL_MAIN.C:SpawnPlayer)
	private const ushort SpawnNorth = 19;
	private const ushort SpawnEast  = 20;
	private const ushort SpawnSouth = 21;
	private const ushort SpawnWest  = 22;

	// 38 bytes of typed fields + 4 bytes "!ID!" = 42 total
	private const int LevelHeaderSize = 42;

	private static readonly (int dx, int dy)[] Directions =
		[(-1, 0), (1, 0), (0, -1), (0, 1)];

	// ── Public data record ───────────────────────────────────────────────────

	/// <summary>
	/// Raw (uncompressed) tile data for a single level.
	/// Compression is applied inside WriteGameMaps.
	/// </summary>
	public record LevelData(
		string   Name,
		ushort   Width,
		ushort   Height,       // Wolf3D "height" = Y depth
		ushort[] WallPlane,    // plane 0 — W×H tile numbers
		ushort[] ObjectPlane,  // plane 1 — spawn codes and objects
		ushort[] OtherPlane    // plane 2 — area / floor codes
	);

	// ── Public stream-based API (testable via MemoryStream) ──────────────────

	/// <summary>
	/// Writes a Carmackized GAMEMAPS file to <paramref name="stream"/>.
	/// Returns the absolute byte offset of each level header, for use by WriteMapHead.
	/// </summary>
	/// <remarks>
	/// Layout per level: [plane 0][plane 1][plane 2][header]
	/// Planes come first so every level header sits at a non-zero file offset.
	/// ParseMapHead (GameMap.cs) terminates on the first zero offset, so level 0's
	/// header must not be at offset 0 — placing planes before headers guarantees this.
	/// This also matches the GAMEMAPS.WL1 layout (observed via hex inspection).
	/// </remarks>
	public static uint[] WriteGameMaps(Stream stream, LevelData[] levels)
	{
		uint[] levelHeaderOffsets = new uint[levels.Length];
		uint   currentOffset      = 0;

		using BinaryWriter writer = new(stream, System.Text.Encoding.ASCII, leaveOpen: true);

		for (int i = 0; i < levels.Length; i++)
		{
			LevelData level = levels[i];

			// Compress each plane: raw tiles → RLEW → Carmack
			byte[] plane0 = CarmackCompress(RlewCompress(level.WallPlane));
			byte[] plane1 = CarmackCompress(RlewCompress(level.ObjectPlane));
			byte[] plane2 = CarmackCompress(RlewCompress(level.OtherPlane));

			uint plane0Offset  = currentOffset;
			uint plane1Offset  = plane0Offset + (uint)plane0.Length;
			uint plane2Offset  = plane1Offset + (uint)plane1.Length;
			uint headerOffset  = plane2Offset + (uint)plane2.Length;

			levelHeaderOffsets[i] = headerOffset; // header follows its own plane data

			// Write plane data first (planestart values point into this block)
			writer.Write(plane0);
			writer.Write(plane1);
			writer.Write(plane2);

			// Level header (38 bytes of typed fields)
			writer.Write(plane0Offset);
			writer.Write(plane1Offset);
			writer.Write(plane2Offset);
			writer.Write(checked((ushort)plane0.Length));
			writer.Write(checked((ushort)plane1.Length));
			writer.Write(checked((ushort)plane2.Length));
			writer.Write(level.Width);
			writer.Write(level.Height);

			// Name: exactly 16 chars, null-padded
			char[] name = new char[16];
			string nameStr = level.Name ?? string.Empty;
			for (int c = 0; c < Math.Min(nameStr.Length, 16); c++)
				name[c] = nameStr[c];
			writer.Write(name);

			// "!ID!" — signals carmackized format to the reader (GameMap.cs:116-119)
			writer.Write(['!', 'I', 'D', '!']);

			currentOffset = headerOffset + LevelHeaderSize;
		}

		return levelHeaderOffsets;
	}

	/// <summary>
	/// Writes a MAPHEAD file to <paramref name="stream"/>.
	/// </summary>
	public static void WriteMapHead(Stream stream, uint[] levelOffsets)
	{
		using BinaryWriter writer = new(stream, System.Text.Encoding.ASCII, leaveOpen: true);
		writer.Write(RlewTag);
		foreach (uint offset in levelOffsets)
			writer.Write(offset);
		writer.Write((uint)0); // terminator — GameMap.ParseMapHead reads until 0
	}

	// ── File-path convenience wrapper ────────────────────────────────────────

	/// <summary>
	/// Converts the 10 KOD level files into GAMEMAPS.KOD and MAPHEAD.KOD
	/// in <paramref name="outputFolder"/>.
	/// </summary>
	public static void WriteTo(string outputFolder, string inputFolder)
	{
		string levelsFolder  = Path.Combine(inputFolder, "chef", "LEVELS");
		string kitchensFolder = Path.Combine(inputFolder, "chef", "KITCHENS");

		if (!Directory.Exists(levelsFolder))
		{
			Console.Error.WriteLine($"ERROR: LEVELS folder not found: {levelsFolder}");
			return;
		}
		if (!Directory.Exists(kitchensFolder))
		{
			Console.Error.WriteLine($"ERROR: KITCHENS folder not found: {kitchensFolder}");
			return;
		}

		Dictionary<string, ushort> texturePage = BuildTexturePageMap(kitchensFolder);

		LevelData[] levels = new LevelData[10];
		for (int levelNum = 1; levelNum <= 10; levelNum++)
		{
			string pcxPath = Path.Combine(levelsFolder, $"LEVEL{levelNum:D2}.PCX");
			string blkPath = Path.Combine(levelsFolder, $"LEVEL{levelNum:D2}.BLK");
			levels[levelNum - 1] = ConvertLevel(pcxPath, blkPath, texturePage, levelNum);
		}

		string gameMapsPath = Path.Combine(outputFolder, "GAMEMAPS.KOD");
		string mapHeadPath  = Path.Combine(outputFolder, "MAPHEAD.KOD");

		using (FileStream gmStream = new(gameMapsPath, FileMode.Create))
		using (FileStream mhStream = new(mapHeadPath,  FileMode.Create))
		{
			uint[] offsets = WriteGameMaps(gmStream, levels);
			WriteMapHead(mhStream, offsets);
		}

		Console.WriteLine($"Written 10 levels to {gameMapsPath} and {mapHeadPath}");
	}

	// ── Compression ──────────────────────────────────────────────────────────

	/// <summary>
	/// Port of CA_RLEWCompress (wolf3d/ID_CA.C).
	/// Returns a ushort[] where [0] = expanded byte count, [1..] = RLEW body.
	/// </summary>
	public static ushort[] RlewCompress(ushort[] data)
	{
		List<ushort> output = [];
		output.Add((ushort)(data.Length * 2)); // expanded byte count at [0]

		int i = 0;
		while (i < data.Length)
		{
			ushort value = data[i];
			int    count = 1;
			while (i + count < data.Length && data[i + count] == value)
				count++;

			// Threshold matches original: count > 3 OR value collides with the tag
			if (count > 3 || value == RlewTag)
			{
				output.Add(RlewTag);
				output.Add((ushort)count);
				output.Add(value);
			}
			else
			{
				for (int j = 0; j < count; j++)
					output.Add(value);
			}

			i += count;
		}

		return [.. output];
	}

	/// <summary>
	/// Complement of GameMap.CarmackExpand (BenMcLean.Wolf3D.Assets.Gameplay.GameMap).
	/// Input: ushort[] produced by RlewCompress (including the [0] expanded-byte-count word).
	/// Output: byte[] suitable for direct inclusion in a GAMEMAPS file.
	/// </summary>
	public static byte[] CarmackCompress(ushort[] data)
	{
		List<byte> output = [];

		// First word: expanded byte count of this ushort[] (data.Length * 2).
		// CarmackExpand reads this as: length = ReadUInt16() >> 1  (word count).
		ushort expandedByteCount = (ushort)(data.Length * 2);
		output.Add((byte)(expandedByteCount & 0xFF));
		output.Add((byte)(expandedByteCount >> 8));

		int i = 0;
		while (i < data.Length)
		{
			ushort word     = data[i];
			byte   wordHigh = (byte)(word >> 8);

			// Search for a NEAR back-reference: last ≤255 words, count ≥2 (cost 3 bytes)
			int bestNearLen = 0, bestNearOffset = 0;
			int maxOffset = Math.Min(255, i);
			for (int offset = 1; offset <= maxOffset; offset++)
			{
				// For NEAR offset k, the expander copies word-by-word from (index−k),
				// wrapping into a repeating k-word pattern for overlapping runs.
				// data[i − k + (len % k)] is what the expander would produce at step len.
				int len = 0;
				while (i + len < data.Length && len < 255
					&& data[i - offset + (len % offset)] == data[i + len])
					len++;

				if (len >= 2 && len > bestNearLen)
				{
					bestNearLen    = len;
					bestNearOffset = offset;
					if (bestNearLen >= 16) break; // good enough; stop searching
				}
			}

			// Search for a FAR back-reference: absolute position, count ≥3 (cost 4 bytes)
			// Limit the look-back window to avoid O(N²) on large inputs.
			int bestFarLen = 0, bestFarPos = 0;
			int farStart = Math.Max(0, i - 1024);
			for (int pos = farStart; pos < i; pos++)
			{
				int len = 0;
				while (i + len < data.Length && len < 255
					&& pos + len < i               // non-overlapping only
					&& data[pos + len] == data[i + len])
					len++;
				if (len >= 3 && len > bestFarLen)
				{
					bestFarLen = len;
					bestFarPos = pos;
				}
			}

			// Emit best option
			if (bestNearLen >= 2 && bestNearLen >= bestFarLen)
			{
				// NEAR: [byte count][byte 0xA7][byte backward-offset]
				output.Add((byte)bestNearLen);
				output.Add(CarmackNear);
				output.Add((byte)bestNearOffset);
				i += bestNearLen;
			}
			else if (bestFarLen >= 3)
			{
				// FAR: [byte count][byte 0xA8][ushort absolute-position LE]
				output.Add((byte)bestFarLen);
				output.Add(CarmackFar);
				output.Add((byte)(bestFarPos & 0xFF));
				output.Add((byte)(bestFarPos >> 8));
				i += bestFarLen;
			}
			else if (wordHigh == CarmackNear || wordHigh == CarmackFar)
			{
				// Escape: literal word whose high byte collides with a tag.
				// count=0 signals escape to CarmackExpand; next byte is the actual low byte.
				output.Add(0x00);       // count = 0 (escape marker, low byte of tag word)
				output.Add(wordHigh);   // tag byte (high byte of tag word)
				output.Add((byte)(word & 0xFF)); // actual low byte of the literal
				i++;
			}
			else
			{
				// Plain literal word (little-endian ushort)
				output.Add((byte)(word & 0xFF));
				output.Add(wordHigh);
				i++;
			}
		}

		return [.. output];
	}

	// ── KOD level conversion ─────────────────────────────────────────────────

	private static LevelData ConvertLevel(
		string pcxPath, string blkPath,
		Dictionary<string, ushort> texturePage, int levelNum)
	{
		(int startX, int startY, int heading) = ParseBlkHeader(blkPath);
		Dictionary<int, BlockDef> blocks = ParseBlkBlocks(blkPath);

		using FileStream pcxStream = File.OpenRead(pcxPath);
		byte[] grid = VSwap.DecodePcxRle(pcxStream, GridSize);

		(ushort minX, ushort minY, ushort width, ushort height, HashSet<(int, int)> reachable)
			= FloodFill(grid, startX, startY);

		ushort[] wallPlane   = new ushort[width * height];
		ushort[] objectPlane = new ushort[width * height];
		ushort[] otherPlane  = new ushort[width * height]; // all zeros

		for (int y = 0; y < height; y++)
			for (int x = 0; x < width; x++)
			{
				int gridX  = minX + x;
				int gridY  = minY + y;
				int mapIdx = y * width + x;

				if (!reachable.Contains((gridX, gridY)))
				{
					wallPlane[mapIdx] = 1; // void or unreachable → default wall tile
					continue;
				}

				byte blockId = grid[gridY * GridSize + gridX];
				wallPlane[mapIdx] = MapBlockToWallTile(blockId, blocks, texturePage);
			}

		// Place player spawn in the object plane
		int spawnX = startX - minX;
		int spawnY = startY - minY;
		if (spawnX >= 0 && spawnY >= 0 && spawnX < width && spawnY < height)
			objectPlane[spawnY * width + spawnX] = HeadingToSpawnCode(heading);

		return new LevelData(
			Name:        $"LEVEL{levelNum:D2}",
			Width:       width,
			Height:      height,
			WallPlane:   wallPlane,
			ObjectPlane: objectPlane,
			OtherPlane:  otherPlane
		);
	}

	// ── Flood fill ───────────────────────────────────────────────────────────

	private static (ushort minX, ushort minY, ushort width, ushort height,
		HashSet<(int, int)> reachable)
		FloodFill(byte[] grid, int startX, int startY)
	{
		HashSet<(int, int)> visited = [];
		Queue<(int, int)>   queue   = new();

		if (grid[startY * GridSize + startX] != VoidCell)
		{
			queue.Enqueue((startX, startY));
			visited.Add((startX, startY));
		}

		int minX = startX, maxX = startX, minY = startY, maxY = startY;

		while (queue.Count > 0)
		{
			(int cx, int cy) = queue.Dequeue();

			if (cx < minX) minX = cx;
			if (cx > maxX) maxX = cx;
			if (cy < minY) minY = cy;
			if (cy > maxY) maxY = cy;

			foreach ((int dx, int dy) in Directions)
			{
				int nx = cx + dx, ny = cy + dy;
				if ((uint)nx >= GridSize || (uint)ny >= GridSize) continue;
				if (grid[ny * GridSize + nx] == VoidCell) continue;
				if (visited.Add((nx, ny)))
					queue.Enqueue((nx, ny));
			}
		}

		return (
			(ushort)minX, (ushort)minY,
			(ushort)(maxX - minX + 1), (ushort)(maxY - minY + 1),
			visited
		);
	}

	// ── BLK file parsing ─────────────────────────────────────────────────────

	private record BlockDef(
		bool   IsPassable,
		string NWall, string EWall, string SWall, string WWall
	);

	private static (int startX, int startY, int heading) ParseBlkHeader(string blkPath)
	{
		int startX = 0, startY = 0, heading = 0;

		foreach (string rawLine in File.ReadLines(blkPath))
		{
			string line = StripInlineComment(rawLine).Trim();

			if (line.StartsWith("Player start x", StringComparison.OrdinalIgnoreCase))
				startX = ParseIntAfterColon(line);
			else if (line.StartsWith("Player start y", StringComparison.OrdinalIgnoreCase))
				startY = ParseIntAfterColon(line);
			else if (line.StartsWith("Player start heading", StringComparison.OrdinalIgnoreCase))
				heading = ParseIntAfterColon(line);
			else if (line.StartsWith("block ",  StringComparison.OrdinalIgnoreCase)
				||   line.StartsWith("thing ",  StringComparison.OrdinalIgnoreCase)
				||   line.StartsWith("action ", StringComparison.OrdinalIgnoreCase))
				break; // past the header section
		}

		return (startX, startY, heading);
	}

	private static Dictionary<int, BlockDef> ParseBlkBlocks(string blkPath)
	{
		Dictionary<int, BlockDef> blocks = [];

		bool   inEntry   = false;
		bool   isThing   = false;
		int    currentId = -1;
		bool   isPassable = false;
		string nWall = "", eWall = "", sWall = "", wWall = "";

		foreach (string rawLine in File.ReadLines(blkPath))
		{
			string line = StripInlineComment(rawLine).Trim();
			if (line.Length == 0) continue;

			if (!inEntry)
			{
				if (TryParseEntryStart(line, "block", out int id))
				{
					currentId = id;
					inEntry   = true;
					isThing   = false;
					isPassable = false;
					nWall = eWall = sWall = wWall = "";
				}
				else if (line.StartsWith("thing ",  StringComparison.OrdinalIgnoreCase)
					||   line.StartsWith("action ", StringComparison.OrdinalIgnoreCase)
					||   line.StartsWith("anim ",   StringComparison.OrdinalIgnoreCase))
				{
					inEntry = true;
					isThing = true;
				}
			}
			else // inside an entry
			{
				if (line[0] == ')')
				{
					inEntry = false;
					if (!isThing && currentId >= 0)
						blocks[currentId] = new BlockDef(isPassable, nWall, eWall, sWall, wWall);
				}
				else if (!isThing)
				{
					string lower = line.ToLowerInvariant();

					// "shape = empty" → passable floor; "set wall" → solid wall
					if (lower.Contains("shape") && lower.Contains("empty"))
						isPassable = true;
					else if (lower.Contains("set wall"))
						isPassable = false;

					ParseWallTextures(line, ref nWall, ref eWall, ref sWall, ref wWall);
				}
			}
		}

		return blocks;
	}

	private static bool TryParseEntryStart(string line, string keyword, out int id)
	{
		id = -1;
		if (!line.StartsWith(keyword + " ", StringComparison.OrdinalIgnoreCase))
			return false;
		string rest = line[(keyword.Length + 1)..].TrimStart();
		int end = rest.IndexOfAny([' ', '(']);
		string numStr = end >= 0 ? rest[..end] : rest;
		return int.TryParse(numStr, out id);
	}

	private static void ParseWallTextures(
		string line,
		ref string nWall, ref string eWall,
		ref string sWall, ref string wWall)
	{
		// A single line may contain multiple semicolon-separated assignments:
		// "n_wall = kitchens\fifts_00; e_wall = kitchens\fifts_01;"
		foreach (string segment in line.Split(';'))
		{
			string seg = segment.Trim();
			int    eq  = seg.IndexOf('=');
			if (eq < 0) continue;
			string key = seg[..eq].Trim().ToLowerInvariant();
			string val = seg[(eq + 1)..].Trim();
			switch (key)
			{
				case "n_wall": nWall = val; break;
				case "e_wall": eWall = val; break;
				case "s_wall": sWall = val; break;
				case "w_wall": wWall = val; break;
			}
		}
	}

	private static int ParseIntAfterColon(string line)
	{
		int colon = line.IndexOf(':');
		if (colon < 0) return 0;
		string val = line[(colon + 1)..].Trim();
		return int.TryParse(val, out int n) ? n : 0;
	}

	private static string StripInlineComment(string line)
	{
		int start = line.IndexOf('{');
		if (start < 0) return line;
		int end = line.IndexOf('}', start);
		return end >= 0 ? line[..start] + line[(end + 1)..] : line[..start];
	}

	// ── Tile mapping helpers ─────────────────────────────────────────────────

	private static ushort MapBlockToWallTile(
		byte blockId,
		Dictionary<int, BlockDef> blocks,
		Dictionary<string, ushort> texturePage)
	{
		if (blockId == 0) return 0; // open floor

		if (!blocks.TryGetValue(blockId, out BlockDef? def)) return 1; // unknown → default wall
		if (def.IsPassable) return 0;

		// Prefer n_wall; fall back through other faces
		string texPath = def.NWall.Length > 0 ? def.NWall
			: def.EWall.Length > 0 ? def.EWall
			: def.SWall.Length > 0 ? def.SWall
			: def.WWall;

		if (texPath.Length == 0) return 1;

		// Texture path is like "kitchens\fifts_00" — extract just the filename
		string texName = Path.GetFileName(texPath).ToLowerInvariant();

		return texturePage.TryGetValue(texName, out ushort pageIndex)
			? (ushort)(pageIndex + 1) // tile 0 = floor; tile 1+ = VSWAP page + 1
			: (ushort)1;              // texture not in KITCHENS (e.g. MISC) → default wall
	}

	// I3D heading (blk file) → Wolf3D object-plane spawn code (WL_MAIN.C:SpawnPlayer)
	private static ushort HeadingToSpawnCode(int heading) => heading switch
	{
		64  => SpawnEast,
		128 => SpawnSouth,
		192 => SpawnWest,
		_   => SpawnNorth, // 0 = north; default for unexpected values
	};

	/// <summary>
	/// Maps KITCHENS PCX filenames to VSWAP page indices using the same sort
	/// order as VSwap.WriteTo, so tile numbers align with VSWAP.KOD pages.
	/// </summary>
	private static Dictionary<string, ushort> BuildTexturePageMap(string kitchensFolder)
	{
		string[] files = [.. Directory.GetFiles(kitchensFolder, "*.PCX")
			.OrderBy(static f => f, StringComparer.OrdinalIgnoreCase)];

		Dictionary<string, ushort> map = new(files.Length);
		for (int i = 0; i < files.Length; i++)
		{
			string name = Path.GetFileNameWithoutExtension(files[i]).ToLowerInvariant();
			map[name] = (ushort)i;
		}
		return map;
	}
}
