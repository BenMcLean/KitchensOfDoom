namespace KitchensOfDoom;

public static class VSwap
{
	/// <summary>
	/// Reads PCX wall textures from chef/KITCHENS/ and writes VSWAP.KOD.
	/// </summary>
	public static void WriteTo(string outputPath, string inputFolder)
	{
		string kitchensFolder = Path.Combine(inputFolder, "chef", "KITCHENS");

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
			using FileStream pcxStream = File.OpenRead(pcxFiles[i]);
			byte[] rowMajor = DecodePcxRle(pcxStream, tileSqrt);
			wallPages[i] = ToColumnMajorWithPaletteRemap(rowMajor, tileSqrt);
		}

		using FileStream outputStream = new(outputPath, FileMode.Create, FileAccess.Write);
		WriteVSwap(outputStream, wallPages, tileSqrt);
		Console.WriteLine($"Written {pcxFiles.Length} wall pages ({tileSqrt}x{tileSqrt}) to {outputPath}");
	}

	// Standard ZSoft PCX file header size (fixed at 128 bytes per PCX spec)
	public const int PcxHeaderSize = 128;

	/// <summary>
	/// Decodes PCX RLE-compressed pixel data.
	/// Returns row-major array of palette indices (tileSqrt × tileSqrt bytes).
	/// </summary>
	public static byte[] DecodePcxRle(Stream pcxStream, ushort tileSqrt)
	{
		// Skip PCX header
		byte[] header = new byte[PcxHeaderSize];
		pcxStream.ReadExactly(header);

		int pixelCount = tileSqrt * tileSqrt;
		byte[] pixels = new byte[pixelCount];
		int dstIdx = 0;
		while (dstIdx < pixelCount)
		{
			int b = pcxStream.ReadByte();
			if ((b & 0xC0) == 0xC0)
			{
				int count = b & 0x3F;
				byte value = (byte)pcxStream.ReadByte();
				for (int j = 0; j < count && dstIdx < pixelCount; j++)
					pixels[dstIdx++] = value;
			}
			else
				pixels[dstIdx++] = (byte)b;
		}
		return pixels;
	}

	/// <summary>
	/// Converts row-major pixel data to Wolf3D column-major wall format,
	/// remapping palette indices: I3D index 0 (transparent) → Wolf3D index 255 (transparent)
	/// by subtracting 1 from each index mod 256.
	/// </summary>
	public static byte[] ToColumnMajorWithPaletteRemap(byte[] rowMajor, ushort tileSqrt)
	{
		byte[] output = new byte[tileSqrt * tileSqrt];
		for (int x = 0; x < tileSqrt; x++)
		{
			int colBase = x * tileSqrt;
			for (int y = 0; y < tileSqrt; y++)
				// Subtract 1 mod 256: 0→255 (transparent), 1→0, 2→1, …
				output[colBase + y] = (byte)(rowMajor[y * tileSqrt + x] - 1);
		}
		return output;
	}

	/// <summary>
	/// Writes a VSWAP file containing only wall pages (no sprites, no sounds).
	/// </summary>
	public static void WriteVSwap(Stream outputStream, byte[][] wallPages, ushort tileSqrt)
	{
		ushort wallCount = (ushort)wallPages.Length;
		// One extra page entry so the loader can find soundDataStart = end of wall data
		ushort numPages = (ushort)(wallCount + 1);
		ushort spritePage = wallCount; // no sprites
		ushort soundPage = wallCount;  // no sounds in Pages array

		int pageSize = tileSqrt * tileSqrt;
		// Header: 3 × ushort + numPages × (uint offset + uint length) = 6 + numPages × 8
		// Page lengths are written as uint (4 bytes) to support page sizes exceeding 65535 bytes.
		// The loader reads these when FourBytePageLengths="true" is set in the game XML.
		int headerSize = 6 + numPages * 8;

		using BinaryWriter writer = new(outputStream, System.Text.Encoding.Default, leaveOpen: true);

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

		// Page lengths (uint, 4 bytes each — supports page sizes exceeding 65535 bytes)
		for (int i = 0; i < wallCount; i++)
			writer.Write((uint)pageSize);
		writer.Write((uint)0); // extra entry

		// Wall data
		for (int i = 0; i < wallCount; i++)
			writer.Write(wallPages[i]);
	}
}
