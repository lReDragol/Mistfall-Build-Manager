using System.Globalization;
using System.Text.Json;

namespace MistfallForge;

internal static class LocalModels
{
    public const int MaxBytes = 80 * 1024 * 1024;

    internal sealed record Entry(string Kind, int Id, string Path, long Size);

    public static Entry[] Index(params string[] roots)
    {
        foreach (string root in roots)
        {
            var entries = new List<Entry>();
            try
            {
                if (!PlainDirectory(root)) continue;
                foreach (string kind in new[] { "characters", "items" })
                {
                    string folder = Path.Combine(root, kind);
                    if (!PlainDirectory(folder)) continue;
                    foreach (var file in new DirectoryInfo(folder).EnumerateFiles("*.glb"))
                    {
                        if (entries.Count >= 5000) break;
                        if ((file.Attributes & FileAttributes.ReparsePoint) != 0 ||
                            !int.TryParse(Path.GetFileNameWithoutExtension(file.Name), NumberStyles.None,
                                CultureInfo.InvariantCulture, out int id) || id <= 0 ||
                            !file.Name.Equals(id.ToString(CultureInfo.InvariantCulture) + ".glb", StringComparison.OrdinalIgnoreCase) ||
                            file.Length is < 20 or > MaxBytes) continue;
                        entries.Add(new(kind, id, file.FullName, file.Length));
                    }
                }
            }
            catch (Exception ex) when (ex is IOException or UnauthorizedAccessException) { continue; }
            if (entries.Count > 0)
            {
                ReadAliases(root, entries);
                return entries.DistinctBy(entry => (entry.Kind, entry.Id)).ToArray();
            }
        }
        return [];
    }

    private static bool PlainDirectory(string path) =>
        Directory.Exists(path) && (File.GetAttributes(path) & FileAttributes.ReparsePoint) == 0;

    private static void ReadAliases(string root, List<Entry> entries)
    {
        try
        {
            var index = new FileInfo(Path.Combine(root, "item-aliases.json"));
            if (!index.Exists || index.Length > 256 * 1024 ||
                (index.Attributes & FileAttributes.ReparsePoint) != 0) return;
            var files = entries.Where(entry => entry.Kind == "items").DistinctBy(entry => entry.Id)
                .ToDictionary(entry => entry.Id);
            using var source = index.OpenRead();
            var aliases = JsonSerializer.Deserialize<Dictionary<int, int>>(source);
            if (aliases is null) return;
            foreach (var (id, appearance) in aliases.OrderBy(pair => pair.Key))
            {
                if (entries.Count >= 5000) break;
                if (id <= 0 || files.ContainsKey(id) || !files.TryGetValue(appearance, out var file)) continue;
                entries.Add(file with { Id = id });
            }
        }
        catch (Exception ex) when (ex is IOException or UnauthorizedAccessException or JsonException) { }
    }
}
