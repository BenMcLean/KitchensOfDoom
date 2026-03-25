using BenMcLean.Wolf3D.Assets.Gameplay;
using Xunit;

namespace KitchensOfDoom.Test;

/// <summary>
/// Verifies that GameMaps.WriteGameMaps + WriteMapHead produce output that
/// GameMap.Load can read back with identical tile data.
/// GAMEMAPS.WL1 and MAPHEAD.WL1 are embedded resources (WL1 is shareware).
/// </summary>
public class GameMapsRoundtripTests
{
	private static Stream GetResource(string name) =>
		typeof(GameMapsRoundtripTests).Assembly
			.GetManifestResourceStream($"KitchensOfDoom.Test.{name}") is Stream stream
			? stream
			: throw new InvalidOperationException(
				$"Embedded resource '{name}' not found. " +
				$"Available: {string.Join(", ", typeof(GameMapsRoundtripTests).Assembly.GetManifestResourceNames())}");
	[Fact]
	public void RoundtripWL1MapsAreIdentical()
	{
		// ── 1. Load originals using the existing reader ──────────────────────
		GameMap[] original;
		using (Stream mhStream = GetResource("MAPHEAD.WL1"))
		using (Stream gmStream = GetResource("GAMEMAPS.WL1"))
			original = GameMap.Load(mhStream, gmStream);

		Assert.NotEmpty(original);

		// ── 2. Wrap original tile data in LevelData records ──────────────────
		GameMaps.LevelData[] levels = [.. original
			.Select(static m => new GameMaps.LevelData(
				m.Name, m.Width, m.Depth,
				m.MapData, m.ObjectData, m.OtherData))];

		// ── 3. Write to MemoryStreams ─────────────────────────────────────────
		using MemoryStream gmOut = new();
		using MemoryStream mhOut = new();
		uint[] offsets = GameMaps.WriteGameMaps(gmOut, levels);
		GameMaps.WriteMapHead(mhOut, offsets);

		// ── 4. Reset and reload ───────────────────────────────────────────────
		gmOut.Position = 0;
		mhOut.Position = 0;
		GameMap[] reloaded = GameMap.Load(mhOut, gmOut);

		// ── 5. Assert tile data matches ───────────────────────────────────────
		Assert.Equal(original.Length, reloaded.Length);

		for (int i = 0; i < original.Length; i++)
		{
			Assert.Equal(original[i].Width, reloaded[i].Width);
			Assert.Equal(original[i].Depth, reloaded[i].Depth);
			Assert.Equal(original[i].MapData, reloaded[i].MapData);
			Assert.Equal(original[i].ObjectData, reloaded[i].ObjectData);
			Assert.Equal(original[i].OtherData, reloaded[i].OtherData);
		}
	}
}
