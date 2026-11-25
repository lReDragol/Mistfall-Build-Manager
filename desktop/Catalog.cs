using System.Text.Json;
using System.Text.Json.Serialization;

namespace MistfallForge;

internal record Socket(int Type, int Rank);
internal record Gear(int Id, string Name, int Grade, Socket[] Sockets, string? Innate,
    string? Weapon, string? Icon, Dictionary<string, double> Stats, string Description, bool Missing = false);
internal record Gem(int Id, string Name, int Type, int Rank, string[] Affixes, string? Icon);
internal record Affix(string Name, int Cap, string Category, string Description, string[] Effects, string? Icon);
internal record Wine(int Id, string Name, int Slots, int Per);
internal record Career(int Id, string Name, string[] Weapons);
internal record Piece(int Id, int[] Gems);
internal record Loadout(int Career, Dictionary<int, Piece> Equipment, int ActiveWeapon = 10);
internal record BuildView(string Code, int Version, Loadout Loadout, Dictionary<int, Gear> Items,
    Dictionary<string, int> Attributes, Dictionary<string, double> Stats, Dictionary<int, Gem?[]> EquippedGems, SoulBrand? Brand = null);

internal sealed class Catalog
{
    private static readonly Dictionary<string, string> LegacyAffixIcons = new(StringComparer.Ordinal)
    {
        ["Ethereal"] = "Бесплотность.png",
        ["Blessing"] = "Благословение.png",
        ["Wealth"] = "Богатство.png",
        ["Brotherhood"] = "Братство.png",
        ["Swift"] = "Быстрота.png",
        ["Burst"] = "Взрыв.png",
        ["Wrath"] = "Гнев.png",
        ["Ranged"] = "Дальний бой.png",
        ["Valor"] = "Доблесть.png",
        ["Iron Helmet"] = "Железный шлем.png",
        ["Tenacious"] = "Живучесть.png",
        ["Distant Ward"] = "Защита на расстоянии.png",
        ["Bulwark"] = "Защита.png",
        ["Focused"] = "Концентрация.png",
        ["Eloquence"] = "Красноречие.png",
        ["Seeker"] = "Ловец.png",
        ["Sleight of Hand"] = "Ловкость.png",
        ["Sky Piercer"] = "Небесный пронзатель.png",
        ["Unyielding"] = "Непреклонность.png",
        ["Seamless"] = "Непрерывность.png",
        ["Elusive"] = "Неуловимость.png",
        ["Curse"] = "Проклятие.png",
        ["Fervid"] = "Пыл.png",
        ["Strife"] = "Раздор.png",
        ["Fervor"] = "Рвение.png",
        ["Creation"] = "Создание.png",
        ["Stoic"] = "Стоик.png",
        ["Smiting"] = "Угнетение.png",
        ["Spirit Shield"] = "Щит духа.png",
        ["Aegis"] = "Эгида.png",
        ["Vitality"] = "Энергичность.png",
        ["Resilience"] = "Выносливость.png",
        ["Deft"] = "Ловкость.png", ["Skypiercing"] = "Небесный пронзатель.png"
    };
    private static string AffixCategory(string name, string category)
    {
        // Use the same categories as the Qt builder, including old catalog labels such as “mobility”.
        if (name is "Brotherhood" or "Ethereal" or "Side by Side" or "Stoic" or "Spirit Shield" or "Unyielding"
            or "Aegis" or "Iron Helmet" or "Tenacious" or "Bulwark" or "Distant Ward" or "Resilience") return "defense";
        if (name is "Valor" or "Wrath" or "Sky Piercer" or "Skypiercing" or "Fervid" or "Seeker" or "Ranged"
            or "Fervor" or "Smiting" or "Burst" or "Strife" or "Dominion" or "Cripple") return "offense";
        if (LegacyAffixIcons.ContainsKey(name)) return "utility";
        return category is "offense" or "defense" ? category : "utility";
    }
    public static readonly int[] EquipmentSlots = [0, 1, 2, 3, 4, 5, 6, 10, 11];
    private readonly Dictionary<(int Career, int Slot), int[]> nativeSlots = new();
    private readonly Dictionary<(int Career, int Slot), Gear[]> choices = new();
    private readonly Dictionary<(int Type, int Rank), Gem[]> gemChoices = new();
    private readonly Dictionary<int, string> weaponAffinities = new();
    public int Head { get; }
    public int Version { get; }
    public string Generated { get; }
    public int[] Slots { get; }
    public int[] GemIds { get; }
    public Dictionary<int, int> Holes { get; }
    public Dictionary<int, Gear> Items { get; } = new();
    public Dictionary<int, Gem> Gems { get; } = new();
    public Dictionary<int, Career> Careers { get; } = new();
    public Dictionary<string, Affix> Affixes { get; } = new(StringComparer.Ordinal);
    public HashSet<string> ReferencedIcons { get; } = new(StringComparer.OrdinalIgnoreCase);
    public Wine[] Wines { get; }

    public Catalog(Stream stream, IReadOnlyDictionary<string, string> icons)
    {
        using var document = JsonDocument.Parse(stream);
        var data = document.RootElement;
        var codec = data.GetProperty("codec");
        Head = codec.GetProperty("head").GetInt32();
        Version = codec.GetProperty("version").GetInt32();
        Generated = String(data, "generated");
        Slots = Numbers(codec.GetProperty("slots"));
        if (!Slots.SequenceEqual(EquipmentSlots) || Version is < 1 or > 2 || Head != 1265153)
            throw new InvalidDataException("Unsupported catalog codec");
        GemIds = Numbers(codec.GetProperty("gemIds"));
        Holes = codec.GetProperty("trous").EnumerateObject().ToDictionary(p => int.Parse(p.Name), p => Number(p.Value));
        if (GemIds is not [0, ..] || GemIds.Length > 1024 || Holes.Values.Any(count => count is < 0 or > 3))
            throw new InvalidDataException("Invalid catalog gem tables");
        foreach (var c in data.GetProperty("classes").EnumerateObject())
        {
            int id = int.Parse(c.Name);
            if (id is < 0 or > 15 || c.Value.GetString() is not { Length: > 0 } name)
                throw new InvalidDataException("Invalid career");
            var weapons = data.GetProperty("armes").TryGetProperty(c.Name, out var array) ? Strings(array) : [];
            Careers.Add(id, new Career(id, name, weapons));
            if (data.TryGetProperty("affinites", out var types) && types.TryGetProperty(c.Name, out var affinity))
                weaponAffinities[id] = affinity.GetString() ?? "physical";
            var tables = codec.GetProperty("equipParClasseEtSlot").GetProperty(c.Name);
            foreach (int slot in Slots)
            {
                int[] ids = Numbers(tables.GetProperty(slot.ToString()));
                if (ids is not [0, ..] || ids.Length > 1024)
                    throw new InvalidDataException("Invalid native equipment table");
                nativeSlots[(id, slot)] = ids;
            }
        }
        foreach (var group in data.GetProperty("objets").EnumerateObject())
        {
            var fields = group.Name.Split('|');
            foreach (var item in group.Value.EnumerateArray())
            {
                int id = Number(item.GetProperty("id"));
                var sockets = item.GetProperty("s").EnumerateArray()
                    .Select(socket => new Socket(Number(socket[0]), Number(socket[1]))).ToArray();
                Dictionary<string, double> stats = [];
                if (item.TryGetProperty("at", out var parameters) && parameters.ValueKind == JsonValueKind.Object)
                    stats = parameters.EnumerateObject().Where(stat => stat.Value.ValueKind == JsonValueKind.Number)
                        .ToDictionary(stat => stat.Name, stat => stat.Value.GetDouble());
                string innate = String(item, "i");
                if (String(item,"ic") is { Length:>0 } itemIcon) ReferencedIcons.Add(itemIcon);
                Items[id] = new(id, String(item, "n"), Number(item.GetProperty("g")), sockets,
                    innate.Length > 0 ? innate : null, fields[1] == "weapon" ? fields[2] : null,
                    Icon(icons, String(item, "ic")), stats, String(item, "d"));
            }
        }
        if (Version == 1) AddLegacyItems(icons);
        foreach (var gem in data.GetProperty("gemmes").EnumerateArray())
        {
            int id = Number(gem.GetProperty("id"));
            if (String(gem,"ic") is { Length:>0 } gemIcon) ReferencedIcons.Add(gemIcon);
            Gems[id] = new(id, String(gem, "n"), Number(gem.GetProperty("t")), Number(gem.GetProperty("l")),
                Strings(gem.GetProperty("a")), Icon(icons, String(gem, "ic")));
        }
        foreach (var affix in data.GetProperty("affixes").EnumerateObject())
        {
            if (affix.Value.ValueKind != JsonValueKind.Object) continue;
            var value = affix.Value;
            if (String(value,"ic") is { Length:>0 } affixIcon) ReferencedIcons.Add(affixIcon);
            Affixes[affix.Name] = new(affix.Name, value.TryGetProperty("cap", out var cap) ? Math.Clamp(Number(cap), 1, 7) : 7,
                AffixCategory(affix.Name, String(value, "cat")), String(value, "desc"),
                value.TryGetProperty("eff", out var effects) ? Strings(effects) : [],
                Icon(icons, String(value, "ic")) ??
                Icon(icons, $"s2-affix-{affix.Name.ToLowerInvariant().Replace(' ', '-')}.png") ??
                Icon(icons, LegacyAffixIcons.GetValueOrDefault(affix.Name) ?? ""));
        }
        Wines = data.TryGetProperty("wine_profiles", out var profiles)
            ? profiles.Deserialize<Wine[]>(new JsonSerializerOptions(JsonSerializerDefaults.Web)) ?? [] : [];
        if (Wines.Any(w => w.Id < 1 || w.Slots is < 0 or > 8 || w.Per is < 0 or > 2))
            throw new InvalidDataException("Invalid wine profile");
        foreach (var (key, ids) in nativeSlots)
            choices[key] = ids.Distinct().Where(Items.ContainsKey).Select(id => Items[id])
                .OrderByDescending(item => item.Grade).ThenBy(item => item.Name, StringComparer.Ordinal).ToArray();
        var codeGems = GemIds.ToHashSet();
        foreach (int rank in new[] { 1, 2 })
        foreach (int type in new[] { -1, 1, 2, 3, 4 })
            gemChoices[(type, rank)] = Gems.Values.Where(g => codeGems.Contains(g.Id) && g.Rank <= rank
                && (type == -1 || type == g.Type)).OrderBy(g => g.Name, StringComparer.Ordinal).ToArray();
    }

    public int[] Native(int career, int slot) => nativeSlots.GetValueOrDefault((career, slot)) ?? [];
    public Gear[] ForSlot(int career, int slot) => choices.GetValueOrDefault((career, slot)) ?? [];
    public Gem[] Compatible(Socket socket) => gemChoices.GetValueOrDefault((socket.Type, socket.Rank)) ?? [];
    public Gear GetItem(int id) => Items.GetValueOrDefault(id) ?? new Gear(id, $"Item #{id}", 0, [], null, null, null, [], "", true);
    public string Affinity(int career, string weapon) => weapon is "Catalyst" or "Staff" ? "magic"
        : weapon.Length > 0 ? "physical" : weaponAffinities.GetValueOrDefault(career, "physical");

    public bool Preserves(Catalog baseline)
    {
        if (Head != baseline.Head || Version != baseline.Version || !GemIds.AsSpan().StartsWith(baseline.GemIds))
            return false;
        foreach (var (slot, ids) in baseline.nativeSlots)
        {
            if (!nativeSlots.TryGetValue(slot, out var newer) || !newer.AsSpan().StartsWith(ids))
                return false;
            if (ids.Any(id => Holes.GetValueOrDefault(id) != baseline.Holes.GetValueOrDefault(id)))
                return false;
        }
        return true;
    }

    public BuildView Inspect(Loadout loadout, string code)
    {
        Dictionary<string, int> attributes = new(StringComparer.Ordinal);
        Dictionary<string, double> stats = new(StringComparer.Ordinal);
        var items = loadout.Equipment.ToDictionary(pair => pair.Key, pair => GetItem(pair.Value.Id));
        foreach (var (slot, piece) in loadout.Equipment)
        {
            if (slot is 10 or 11 && loadout.ActiveWeapon != slot) continue;
            Gear item = items[slot];
            if (item.Innate is { Length: > 0 } name)
                attributes[name] = attributes.GetValueOrDefault(name) + 1;
            foreach (var (stat, value) in item.Stats)
                stats[stat] = stats.GetValueOrDefault(stat) + value;
            foreach (int gemId in piece.Gems)
                if (Gems.TryGetValue(gemId, out var gem))
                    foreach (string a in gem.Affixes)
                        attributes[a] = attributes.GetValueOrDefault(a) + 1;
        }
        var equippedGems = loadout.Equipment.Where(pair => pair.Value.Gems.Length > 0)
            .ToDictionary(pair => pair.Key, pair => Array.ConvertAll(pair.Value.Gems, id => Gems.GetValueOrDefault(id)));
        return new(code, Version, loadout, items, attributes, stats, equippedGems);
    }

    private static int Number(JsonElement value) => value.ValueKind == JsonValueKind.Number ? value.GetInt32() : int.Parse(value.GetString()!);
    private static string String(JsonElement value, string field) =>
        value.TryGetProperty(field, out var text) && text.ValueKind == JsonValueKind.String ? text.GetString()! : "";
    private static int[] Numbers(JsonElement array) => array.EnumerateArray().Select(Number).ToArray();
    private static string[] Strings(JsonElement array) => array.EnumerateArray().Select(x => x.GetString() ?? "").ToArray();
    private static string? Icon(IReadOnlyDictionary<string, string> index, string name) => index.GetValueOrDefault(name);

    private void AddLegacyItems(IReadOnlyDictionary<string, string> icons)
    {
        // IDs present in the v1 codec but absent from its public item table (same overrides as the Qt builder).
        void Add(int id, string name, Socket[] sockets, string image, Dictionary<string, double> stats,
            string description = "", string? weapon = null, string? innate = null)
        {
            if (Holes.GetValueOrDefault(id) != sockets.Length) return;
            Items.TryAdd(id, new Gear(id, name, weapon is null ? 6 : 7, sockets, innate, weapon, Icon(icons, image), stats, description));
        }
        Add(1660402, "Raven War Pendant", [new(4,2), new(1,1), new(3,1)], "T_UI_Icon_Equip_1221011.webp",
            new() { ["attack"] = 8, ["combatValue"] = 500, ["magicalIncrease"] = 0.018 });
        Add(1660403, "Raven War Pendant", [new(4,2), new(1,1), new(4,1)], "T_UI_Icon_Equip_1221011.webp",
            new() { ["attack"] = 8, ["combatValue"] = 500, ["magicalIncrease"] = 0.018 },
            "Warriors often offer raw meat to crows before marching into battle, hoping that once Hermeil's heralds are satiated, they won't come to guide them to the Realm of the Dead.");
        Add(1760103, "Ancestral Blessing Ring", [new(4,2), new(1,1), new(2,1)], "T_UI_Icon_Equip_1220018.webp",
            new() { ["maxHealth"] = 34, ["combatValue"] = 500, ["physicalReduction"] = 0.018 },
            "The Northerners believe that after death, a part of the soul returns from the Realm of the Dead to be reborn within the same family.");
        Add(1760401, "Eye of the Sea Giant", [new(3,2), new(2,1), new(4,1)], "T_UI_Icon_Equip_1220017.webp",
            new() { ["attack"] = 8, ["combatValue"] = 500, ["magicalIncrease"] = 0.018 });
        Add(3070904, "Moon Deity - Soul Devourer Catalyst", [new(4,2), new(1,1)], "3070904.webp",
            new() { ["attack"] = 40, ["combatValue"] = 600, ["magicalIncrease"] = 0.072 }, weapon: "Catalyst", innate: "Seeker");
        Add(3071001, "Moon Deity - Summoning Catalyst", [new(4,2), new(1,1)], "3071001.webp",
            new() { ["attack"] = 40, ["combatValue"] = 600, ["magicalIncrease"] = 0.072 }, weapon: "Catalyst");
    }
}
