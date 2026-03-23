namespace KitchensOfDoom;

public static class Program
{
	public static void Main(string[] args)
	{
		string inputFolder = args.Length > 0 ? args[0] : Directory.GetCurrentDirectory();
		string kitchensFolder = Path.Combine(inputFolder, "chef", "KITCHENS");
		string outputPath = args.Length > 1 ? args[1] : Path.Combine(inputFolder, "VSWAP.KOD");

		if (!Directory.Exists(kitchensFolder))
		{
			Console.Error.WriteLine($"ERROR: KITCHENS folder not found: {kitchensFolder}");
			return;
		}

		string[] pcxFiles = [.. Directory.GetFiles(kitchensFolder, "*.PCX")
			.OrderBy(static f => f, StringComparer.OrdinalIgnoreCase)];

		if (pcxFiles.Length == 0)
		{
			Console.Error.WriteLine($"ERROR: No PCX files found in {kitchensFolder}");
			return;
		}

		const ushort tileSqrt = 256;

		byte[][] wallPages = new byte[pcxFiles.Length][];
		for (int i = 0; i < pcxFiles.Length; i++)
		{
			byte[] pcxData = File.ReadAllBytes(pcxFiles[i]);
			byte[] rowMajor = DecodePcxRle(pcxData, tileSqrt);
			wallPages[i] = ToColumnMajorWithPaletteRemap(rowMajor, tileSqrt);
		}

		WriteVSwap(outputPath, wallPages, tileSqrt);
		Console.WriteLine($"Written {pcxFiles.Length} wall pages ({tileSqrt}x{tileSqrt}) to {outputPath}");
	}

	/// <summary>
	/// Decodes PCX RLE-compressed pixel data.
	/// Returns row-major array of palette indices (tileSqrt × tileSqrt bytes).
	/// </summary>
	private static byte[] DecodePcxRle(byte[] pcxData, ushort tileSqrt)
	{
		int pixelCount = tileSqrt * tileSqrt;
		byte[] pixels = new byte[pixelCount];
		int srcIdx = 128; // skip 128-byte PCX header
		int dstIdx = 0;
		while (dstIdx < pixelCount)
		{
			byte b = pcxData[srcIdx++];
			if ((b & 0xC0) == 0xC0)
			{
				int count = b & 0x3F;
				byte value = pcxData[srcIdx++];
				for (int j = 0; j < count && dstIdx < pixelCount; j++)
					pixels[dstIdx++] = value;
			}
			else
				pixels[dstIdx++] = b;
		}
		return pixels;
	}

	/// <summary>
	/// Converts row-major pixel data to Wolf3D column-major wall format,
	/// remapping palette indices: I3D index 0 (transparent) → Wolf3D index 255 (transparent)
	/// by subtracting 1 from each index mod 256.
	/// </summary>
	private static byte[] ToColumnMajorWithPaletteRemap(byte[] rowMajor, ushort tileSqrt)
	{
		byte[] output = new byte[tileSqrt * tileSqrt];
		for (int x = 0; x < tileSqrt; x++)
			for (int y = 0; y < tileSqrt; y++)
				// Subtract 1 mod 256: 0→255 (transparent), 1→0, 2→1, …
				output[x * tileSqrt + y] = (byte)(rowMajor[y * tileSqrt + x] - 1);
		return output;
	}

	/// <summary>
	/// Writes a VSWAP file containing only wall pages (no sprites, no sounds).
	/// </summary>
	private static void WriteVSwap(string outputPath, byte[][] wallPages, ushort tileSqrt)
	{
		ushort wallCount = (ushort)wallPages.Length;
		// One extra page entry so the loader can find soundDataStart = end of wall data
		ushort numPages = (ushort)(wallCount + 1);
		ushort spritePage = wallCount; // no sprites
		ushort soundPage = wallCount;  // no sounds in Pages array

		int pageSize = tileSqrt * tileSqrt;
		// Header: 3 × ushort + numPages × (uint offset + ulong length) = 6 + numPages × 12
		// Page lengths are written as ulong (8 bytes) to permanently support any page size.
		// The loader reads these when LongPageLengths="true" is set in the game XML.
		int headerSize = 6 + numPages * 12;

		using FileStream fs = new(outputPath, FileMode.Create, FileAccess.Write);
		using BinaryWriter writer = new(fs);

		writer.Write(numPages);
		writer.Write(spritePage);
		writer.Write(soundPage);

		// Page offsets: wall pages packed contiguously after header
		uint dataOffset = (uint)headerSize;
		for (int i = 0; i < wallCount; i++)
		{
			writer.Write(dataOffset);
			dataOffset += (uint)pageSize;
		}
		// Extra entry points to end of all wall data — used as soundDataStart by the loader
		writer.Write(dataOffset);

		// Page lengths (ulong, 8 bytes each — permanently supports any page size)
		for (int i = 0; i < wallCount; i++)
			writer.Write((ulong)pageSize);
		writer.Write((ulong)0); // extra entry

		// Wall data
		for (int i = 0; i < wallCount; i++)
			writer.Write(wallPages[i]);
	}
}
