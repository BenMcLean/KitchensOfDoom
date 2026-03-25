namespace KitchensOfDoom;

public static class Program
{
	public static void Main(string[] args)
	{
		string inputFolder  = args.Length > 0 ? args[0] : Directory.GetCurrentDirectory();
		string outputFolder = args.Length > 1 ? args[1] : inputFolder;

		VSwap.WriteTo(Path.Combine(outputFolder, "VSWAP.KOD"), inputFolder);
		GameMaps.WriteTo(outputFolder, inputFolder);
	}
}
