using System.Text.Json;
using System.Text.Json.Serialization;

namespace MistfallForge;

internal record SavedBuild(Guid Id, string Name, string Code, int ActiveWeapon, int Career, SoulBrand? Brand = null);
internal record SaveRequest(Guid? Id, string Name, string Code, int ActiveWeapon, SoulBrand? Brand = null);

internal sealed class Library
{
    private readonly object gate = new();
    private readonly string path, oldPath;
    private static readonly JsonSerializerOptions Json = new(JsonSerializerDefaults.Web) { WriteIndented = true };

    public Library(string directory, string oldPath)
    {
        path = Path.Combine(directory, "builds.json");
        this.oldPath = oldPath;
    }

    public SavedBuild[] List(GearCode codec)
    {
        lock (gate) return Read(codec).ToArray();
    }

    public SavedBuild Save(SaveRequest request, GearCode codec, Action<BuildView>? validate = null)
    {
        if (request.Name?.Trim() is not { Length: > 0 and <= 100 } name)
            throw new ArgumentException("build-name");
        var build = codec.Decode(request.Code, request.ActiveWeapon);
        validate?.Invoke(build);
        lock (gate)
        {
            var rows = Read(codec);
            var row = new SavedBuild(request.Id ?? Guid.NewGuid(), name, build.Code,
                build.Loadout.ActiveWeapon, build.Loadout.Career, request.Brand);
            if (request.Id is Guid id)
            {
                int index = rows.FindIndex(saved => saved.Id == id);
                if (index < 0) throw new ArgumentException("build-missing");
                rows[index] = row;
            }
            else rows.Add(row);
            Write(rows);
            return row;
        }
    }

    public void Delete(Guid id, GearCode codec)
    {
        lock (gate)
        {
            var rows = Read(codec);
            if (rows.RemoveAll(row => row.Id == id) == 0) throw new ArgumentException("build-missing");
            Write(rows);
        }
    }

    private List<SavedBuild> Read(GearCode codec)
    {
        if (File.Exists(path))
        {
            using var stream = File.OpenRead(path);
            return JsonSerializer.Deserialize<List<SavedBuild>>(stream, Json) ?? [];
        }
        if (!File.Exists(oldPath)) return [];
        using var old = File.OpenRead(oldPath);
        var input = JsonSerializer.Deserialize<List<OldBuild>>(old, Json) ?? [];
        List<SavedBuild> imported = [];
        foreach (var row in input)
        {
            if (string.IsNullOrWhiteSpace(row.Code)) continue;
            int active = row.WeaponSlot == 11 ? 11 : 10;
            int career;
            try { career = codec.Decode(row.Code, active).Loadout.Career; }
            catch (ArgumentException) { career = 0; }
            imported.Add(new(Guid.NewGuid(), row.Name ?? "Untitled", row.Code, active, career));
        }
        Write(imported);
        return imported;
    }

    private void Write(List<SavedBuild> rows)
    {
        Directory.CreateDirectory(Path.GetDirectoryName(path)!);
        string pending = path + ".tmp";
        File.WriteAllText(pending, JsonSerializer.Serialize(rows, Json));
        File.Move(pending, path, true);
    }

    private record OldBuild(string? Name, string? Code,
        [property: JsonPropertyName("weapon_slot")] int WeaponSlot = 10);
}
