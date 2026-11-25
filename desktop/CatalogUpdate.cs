using System.Buffers.Binary;
using System.Text.Json;
using System.Text.RegularExpressions;

namespace MistfallForge;

internal static class CatalogUpdate
{
    private static readonly Uri Wiki = new("https://mistfallhunter.wiki/");
    private static readonly HttpClient Client = new(new HttpClientHandler { AllowAutoRedirect = false })
    {
        Timeout = TimeSpan.FromSeconds(15)
    };
    private static readonly Dictionary<string, (string Group, string Slot)> Slots = new()
    {
        ["head"] = ("Helmet","0"), ["chest"] = ("Clothes","1"), ["hands"] = ("Gauntlets","2"),
        ["legs"] = ("Pants","3"), ["feet"] = ("Boots","4"), ["necklace"] = ("Necklace","5"),
        ["ring"] = ("Ring","6"), ["weapon"] = ("weapon","10")
    };
    private static readonly Dictionary<string, int> SocketColors = new()
        { ["a"] = 1, ["y"] = 2, ["m"] = 3, ["p"] = 4, ["x"] = -1 };
    private static readonly Dictionary<string, int> GemTypes = new()
        { ["Agate"] = 1, ["Amethyst"] = 2, ["Moonstone"] = 3, ["Peridot"] = 4 };
    private static readonly Dictionary<string, string> StatNames = new()
    {
        ["atk"] = "attack", ["def"] = "defence", ["hp"] = "maxHealth",
        ["pres"] = "physicalReduction", ["mres"] = "magicalReduction", ["cres"] = "criticalReduction",
        ["pdmg"] = "physicalIncrease", ["mdmg"] = "magicalIncrease", ["block"] = "blockRate"
    };

    public static async Task<(byte[] Pack, Dictionary<string, string> Images)> Fetch(Catalog legacy, CancellationToken cancel)
    {
        var assets = await Task.WhenAll(new[] { "gear", "gamecode", "wine" }.Select(name =>
            Download(new Uri(Wiki, "builder/data/" + name + ".json"), 4 * 1024 * 1024, cancel)));
        using var gear = JsonDocument.Parse(assets[0]);
        using var code = JsonDocument.Parse(assets[1]);
        using var wines = JsonDocument.Parse(assets[2]);
        return MakePack(gear.RootElement, code.RootElement, wines.RootElement, legacy);
    }

    private static (byte[], Dictionary<string, string>) MakePack(JsonElement gear, JsonElement code, JsonElement wines, Catalog legacy)
    {
        static string Str(JsonElement e, string key) => e.TryGetProperty(key, out var v) && v.ValueKind == JsonValueKind.String ? v.GetString()! : "";
        static int Int(JsonElement e) => e.ValueKind == JsonValueKind.String ?
            int.Parse(e.GetString()!, System.Globalization.CultureInfo.InvariantCulture) : e.GetInt32();
        static string Key(int id) => id.ToString(System.Globalization.CultureInfo.InvariantCulture);
        var classes = code.GetProperty("classes").EnumerateObject().ToDictionary(p => p.Name, p => Int(p.Value));
        var rarities = gear.GetProperty("rarities").EnumerateArray().Select(x => x.GetString()).ToArray();
        var holes = code.GetProperty("holes");
        var tables = code.GetProperty("lists").EnumerateObject().ToDictionary(p => p.Name,
            p => p.Value.EnumerateObject().ToDictionary(s => s.Name, s => s.Value.EnumerateArray().Select(Int).ToArray()));
        foreach (var table in tables.Values) table.TryAdd("11", table["10"]);
        var memberships = tables.ToDictionary(p => p.Key, p => p.Value.ToDictionary(s => s.Key, s => s.Value.ToHashSet()));
        var codeItems = code.GetProperty("items");
        var items = new Dictionary<string,List<object>>();
        var images = new Dictionary<string,string>(StringComparer.OrdinalIgnoreCase);
        foreach (var item in gear.GetProperty("items").EnumerateArray())
        {
            string name = Str(item,"name"), weapon = Str(item,"weaponType");
            var (group, slot) = Slots[Str(item,"slot")];
            int grade = Array.IndexOf(rarities,Str(item,"rarity")) + 1;
            int id = Int(item.GetProperty("id"));
            if (grade == 0 || !codeItems.TryGetProperty(Key(id), out var variants)) continue;
            var layouts = item.GetProperty("sockets");
            item.TryGetProperty("innate", out var innates);
            string restricted = Str(item,"class");
            var classNames = restricted.Length == 0 ? classes.Keys.AsEnumerable() : restricted.Split(", ");
            int index = -1;
            foreach (var entry in variants.EnumerateArray())
            {
                index++;
                if (entry.ValueKind is JsonValueKind.Null or JsonValueKind.False) continue;
                bool ordered = entry.ValueKind == JsonValueKind.Array;
                int cfg = Int(ordered ? entry[0] : entry);
                if (cfg == 0) continue;
                var layout = layouts.GetArrayLength() == 0 ? Array.Empty<JsonElement>() : layouts[index].EnumerateArray().ToArray();
                if (ordered && entry[1].ValueKind == JsonValueKind.Array)
                {
                    int[] order = entry[1].EnumerateArray().Select(Int).ToArray();
                    if (order.Length != layout.Length || !order.Order().SequenceEqual(Enumerable.Range(0,layout.Length)))
                        throw new InvalidDataException("Invalid socket ordering");
                    layout = Enumerable.Range(0, order.Length).Select(i => layout[Array.IndexOf(order,i)]).ToArray();
                }
                if ((holes.TryGetProperty(Key(cfg),out var length)?Int(length):0) != layout.Length) continue;
                string? innate = innates.ValueKind == JsonValueKind.Array && index < innates.GetArrayLength() ? innates[index].GetString() : null;
                var stats = item.GetProperty("stats").EnumerateObject().Where(p=>StatNames.ContainsKey(p.Name))
                    .ToDictionary(p=>StatNames[p.Name],p=>p.Value.GetDouble()/(p.Name is "atk" or "def" or "hp"?1:100));
                stats["combatValue"] = item.TryGetProperty(innate is not null ? "cvAffix":"cv", out var cv)
                    ? cv.GetDouble() : item.GetProperty("value").GetDouble();
                string filename = $"s2-item-{id}.png";
                if (legacy.Items.TryGetValue(cfg,out var old) && old.Name == name && old.Icon is { } existing)
                    filename = Uri.UnescapeDataString(existing.Split('/')[^1]);
                else if (Str(item,"icon") is { Length: > 0 } url) images.TryAdd(filename,url);
                var row = new { id=Key(cfg), n=name, g=grade,
                    s=layout.Select(x=>x.ValueKind==JsonValueKind.String && x.GetString() is { Length:2 } marker
                        ? new[] {SocketColors[marker[1].ToString()], Math.Max(1,marker[0]-'0')}
                        : new[] {SocketColors[x[1].GetString()!], Math.Max(1,Int(x[0]))}).ToArray(),
                    i=innate, ic=filename, at=stats, d=Str(item,"description") };
                foreach (string className in classNames)
                {
                    string classId = Key(classes[className]);
                    if (!memberships[classId][slot].Contains(cfg)) continue;
                    string key = $"{classId}|{group}|{weapon}|{grade}";
                    if (!items.TryGetValue(key,out var list)) items[key] = list = [];
                    list.Add(row);
                }
            }
        }
        var affixes = gear.GetProperty("affixes").EnumerateArray().ToDictionary(a=>Str(a,"name"),a=>
        {
            var file = $"s2-affix-{Str(a,"name").ToLowerInvariant().Replace(' ','-')}.png";
            if (Str(a,"icon") is { Length: > 0 } url) images.TryAdd(file,url);
            return new { cap=Int(a.GetProperty("max")), desc=Str(a,"effect").Replace("'''",""),
                eff=a.GetProperty("levels"), cat=Str(a,"color") switch {"red"=>"offense","blue"=>"defense",_=>"utility"},
                mat=a.GetProperty("types").EnumerateArray().Select(x=>GemTypes[x.GetString()!]).ToArray(), ic=file };
        });
        var gemIds = code.GetProperty("gemList").EnumerateArray().Select(Int).ToArray();
        var legalGems = gemIds.ToHashSet();
        var gemCodes=code.GetProperty("gems");
        var gems = new List<object>();
        foreach (var gem in gear.GetProperty("gems").EnumerateArray())
        {
            if (!gemCodes.TryGetProperty(Key(Int(gem.GetProperty("id"))),out var cfg) || !legalGems.Contains(Int(cfg))) continue;
            int type=GemTypes[Str(gem,"type")], rank=Int(gem.GetProperty("tier"));
            gems.Add(new { id=Key(Int(cfg)), n=Str(gem,"name"), t=type, l=rank,
                a=gem.GetProperty("affixes").EnumerateArray().SelectMany(x=>Enumerable.Repeat(Str(x,"name"),
                    Math.Clamp(Int(x.GetProperty("level")),0,7))).ToArray(),
                ic=$"SPR_UI_EquipGemHole_Gem_{rank}_{"ADBC"[type-1]}.webp" });
        }
        var pack = new { season=gear.GetProperty("season"), generated=Str(gear,"generated"), source=new Uri(Wiki,"builder/data").AbsoluteUri,
            classes=classes.ToDictionary(x=>Key(x.Value),x=>x.Key),
            armes=gear.GetProperty("classes").EnumerateArray().ToDictionary(c=>Key(classes[Str(c,"name")]),c=>c.GetProperty("weapons")),
            objets=items, gemmes=gems, affixes,
            codec=new { head=code.GetProperty("head"), version=code.GetProperty("codeVersion"), slots=code.GetProperty("slots"),
                equipParClasseEtSlot=tables, gemIds, trous=holes },
            wine_profiles=wines.GetProperty("wines"), affinites=legacy.Careers.Keys.ToDictionary(Key,id=>legacy.Affinity(id,""))
        };
        return (JsonSerializer.SerializeToUtf8Bytes(pack),images);
    }

    public static bool SafeFile(string file) => Regex.IsMatch(file, @"\A[\p{L}\p{N}][\p{L}\p{N} _'-]{0,118}\.(png|webp)\z",
        RegexOptions.IgnoreCase | RegexOptions.CultureInvariant);

    public static async Task CacheIcon(string folder, string name, byte[] bytes, CancellationToken cancel)
    {
        Directory.CreateDirectory(folder);
        string pending=Path.Combine(folder,Guid.NewGuid().ToString("N")+".tmp");
        try
        {
            await File.WriteAllBytesAsync(pending,bytes,cancel);
            File.Move(pending,Path.Combine(folder,name),true);
        }
        finally { if(File.Exists(pending)) File.Delete(pending); }
    }

    private static Uri? ImageUri(string path)
    {
        if (!path.StartsWith("/images/",StringComparison.Ordinal) || path.Contains("..") || path.IndexOfAny(['\\','#','?']) >= 0)
            return null;
        var url=new Uri(Wiki,path);
        return url.Host==Wiki.Host && url.AbsolutePath.StartsWith("/images/",StringComparison.Ordinal) ? url : null;
    }

    public static async Task<int> CacheImages(Dictionary<string,string> images, string folder,
        IReadOnlyDictionary<string,string> known, CancellationToken cancel)
    {
        int saved=0;
        var missing=images.Where(p=>!known.ContainsKey(p.Key)&&SafeFile(p.Key)).Take(120).ToArray();
        if (missing.Length==0) return 0;
        Directory.CreateDirectory(folder);
        await Parallel.ForEachAsync(missing,new ParallelOptions{MaxDegreeOfParallelism=6,CancellationToken=cancel},async (pair, ct)=>
        {
            if (ImageUri(pair.Value) is not { } url) return;
            try
            {
                byte[] bytes;
                try { bytes=await Download(url,1024*1024,ct); }
                catch(HttpRequestException)
                {
                    string original=Regex.Replace(pair.Value,@"^/images/thumb/(.*)/[^/]+$", "/images/$1");
                    if (original==pair.Value||ImageUri(original) is not { } fallback) return;
                    bytes=await Download(fallback,1024*1024,ct);
                }
                if (ImageType(bytes)==null) return;
                await CacheIcon(folder,pair.Key,bytes,ct);
                Interlocked.Increment(ref saved);
            }
            catch(Exception ex) when(ex is HttpRequestException or IOException || ex is OperationCanceledException && !ct.IsCancellationRequested) {}
        });
        return saved;
    }

    public static string? ImageType(byte[] bytes)
    {
        if (bytes.Length>=24 && bytes.AsSpan(0,8).SequenceEqual(new byte[] {137,80,78,71,13,10,26,10})
            && bytes.AsSpan(12,4).SequenceEqual("IHDR"u8) &&
            BinaryPrimitives.ReadUInt32BigEndian(bytes.AsSpan(16,4)) is >0 and <=1024 &&
            BinaryPrimitives.ReadUInt32BigEndian(bytes.AsSpan(20,4)) is >0 and <=1024) return "image/png";
        // Existing wiki icon exports are PNG. Accept WebP variants only with bounded image dimensions.
        if (bytes.Length<30 || !bytes.AsSpan(0,4).SequenceEqual("RIFF"u8) || !bytes.AsSpan(8,4).SequenceEqual("WEBP"u8)
            || BinaryPrimitives.ReadUInt32LittleEndian(bytes.AsSpan(4,4)) != bytes.Length-8) return null;
        int width, height;
        if (bytes.AsSpan(12,4).SequenceEqual("VP8X"u8))
        {
            width=1+bytes[24]+(bytes[25]<<8)+(bytes[26]<<16);
            height=1+bytes[27]+(bytes[28]<<8)+(bytes[29]<<16);
        }
        else if (bytes.AsSpan(12,4).SequenceEqual("VP8L"u8) && bytes[20]==0x2f)
        {
            uint size=BinaryPrimitives.ReadUInt32LittleEndian(bytes.AsSpan(21,4));
            width=1+(int)(size&0x3fff); height=1+(int)((size>>14)&0x3fff);
        }
        else if (bytes.AsSpan(12,4).SequenceEqual("VP8 "u8) && bytes.AsSpan(23,3).SequenceEqual(new byte[]{0x9d,0x01,0x2a}))
        {
            width=BinaryPrimitives.ReadUInt16LittleEndian(bytes.AsSpan(26,2))&0x3fff;
            height=BinaryPrimitives.ReadUInt16LittleEndian(bytes.AsSpan(28,2))&0x3fff;
        }
        else return null;
        return width is >0 and <=1024 && height is >0 and <=1024 ? "image/webp" : null;
    }

    private static async Task<byte[]> Download(Uri uri, int limit, CancellationToken cancel)
    {
        using var deadline=CancellationTokenSource.CreateLinkedTokenSource(cancel);
        deadline.CancelAfter(TimeSpan.FromSeconds(18));
        using var request=new HttpRequestMessage(HttpMethod.Get,uri);
        request.Headers.UserAgent.ParseAdd("MistfallForge/5.0.13");
        using var response=await Client.SendAsync(request,HttpCompletionOption.ResponseHeadersRead,deadline.Token);
        response.EnsureSuccessStatusCode();
        if (response.Content.Headers.ContentLength > limit) throw new InvalidDataException("File too large");
        await using var stream=await response.Content.ReadAsStreamAsync(deadline.Token);
        using var result=new MemoryStream();
        byte[] buffer=new byte[16384];
        int read;
        while ((read=await stream.ReadAsync(buffer,deadline.Token))>0)
        {
            if (result.Length+read>limit) throw new InvalidDataException("File too large");
            result.Write(buffer,0,read);
        }
        return result.ToArray();
    }
}
