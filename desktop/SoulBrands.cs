using System.Text.Json;

namespace MistfallForge;

internal record SoulBrand(int Rarity, int Level, BrandEffect[] Effects);
internal record BrandEffect(string Kind, int Id = 0, double Value = 0, int Type = 0, int Rank = 0);
internal record BrandRarity(string Key, string Name, string Rarity, int Cap, int Max, string Icon);
internal record BrandRule(int Fixed, int Gem, int FixedGem, int ClassTalent, int GeneralTalent, int[] AffixLevels);
internal record BrandAttribute(int Id, string Name, bool Pct, string? Stat, string[]? Cls, double[][] V);
internal record BrandAffix(int Id, string Name, string[]? Cls);
internal record BrandTalent(int Id, string Name, string Desc);
internal record SoulBrandData(int Version, string Season, BrandRarity[] Rarities, BrandRule Rules,
    BrandAttribute[] Attrs, BrandAffix[] Affixes, Dictionary<string, BrandTalent[]> Talents);

internal sealed class SoulBrands(SoulBrandData data)
{
    private static readonly Dictionary<string, string> EquipmentStats = new()
    {
        ["atk"] = "attack", ["def"] = "defence", ["hp"] = "maxHealth", ["cres"] = "criticalReduction",
        ["mdmg"] = "magicalIncrease", ["mres"] = "magicalReduction", ["pdmg"] = "physicalIncrease", ["pres"] = "physicalReduction"
    };
    public SoulBrandData Data { get; } = data with
    {
        Rarities = data.Rarities.Select(r => r with { Icon = "/soulbrand-icons/" + Path.ChangeExtension(Path.GetFileName(r.Icon), ".png") }).ToArray()
    };

    public static SoulBrands Load(string path)
    {
        using var stream = File.OpenRead(path);
        var data = JsonSerializer.Deserialize<SoulBrandData>(stream, new JsonSerializerOptions(JsonSerializerDefaults.Web));
        if (data is not { Version: 1, Season: "S2", Rarities.Length: 4 }) throw new InvalidDataException("Soul Brand catalog");
        return new(data);
    }

    public static bool Available(string[]? classes, string career) => classes is null || classes.Contains(career);

    public static string AffixName(Catalog catalog, string name) => name switch
    {
        "Deft" when !catalog.Affixes.ContainsKey(name) => "Sleight of Hand",
        "Skypiercing" when !catalog.Affixes.ContainsKey(name) => "Sky Piercer",
        _ => name
    };

    public (Dictionary<string, int> Affixes, Dictionary<string, double> Stats) Evaluate(Catalog catalog, int careerId, SoulBrand? brand)
    {
        Dictionary<string, int> affixes = new(StringComparer.Ordinal);
        Dictionary<string, double> stats = new(StringComparer.Ordinal);
        if (brand == null) return (affixes, stats);
        static ArgumentException Invalid() => new("invalid-brand");
        if (!catalog.Careers.TryGetValue(careerId, out var career) || brand.Rarity < 0 || brand.Rarity >= Data.Rarities.Length ||
            brand.Level < 1 || brand.Level > Data.Rarities[brand.Rarity].Max || brand.Effects is null ||
            brand.Effects.Length > brand.Level) throw Invalid();
        var rules = Data.Rules;
        var statsSeen = new HashSet<int>();
        var affixesSeen = new HashSet<int>();
        var colors = new HashSet<int>();
        int fixedCount = 0, gems = 0, classTalent = 0, generalTalent = 0;
        void Add(string name, int level) => affixes[name] = affixes.GetValueOrDefault(name) + level;
        foreach (var effect in brand.Effects)
        {
            switch (effect?.Kind)
            {
                case "stat":
                    var attr = Data.Attrs.FirstOrDefault(a => a.Id == effect.Id);
                    if (attr == null || !Available(attr.Cls, career.Name) || !statsSeen.Add(effect.Id)) throw Invalid();
                    var range = attr.V[brand.Rarity];
                    double steps = effect.Value * (attr.Pct ? 10 : 1);
                    if (!double.IsFinite(steps) || Math.Abs(steps - Math.Round(steps)) > 1e-6 ||
                        effect.Value < range[0] - 1e-6 || effect.Value > range[2] + 1e-6) throw Invalid();
                    string key = attr.Stat != null && EquipmentStats.TryGetValue(attr.Stat, out var mapped)
                        ? mapped : "brandStat" + attr.Id;
                    stats[key] = attr.Pct ? effect.Value / 100 : effect.Value;
                    break;
                case "affix":
                    var affix = Data.Affixes.FirstOrDefault(a => a.Id == effect.Id);
                    if (++fixedCount > rules.Fixed || affix == null || !Available(affix.Cls, career.Name) ||
                        !affixesSeen.Add(effect.Id) || effect.Value != Math.Truncate(effect.Value) ||
                        effect.Value < rules.AffixLevels[0] || effect.Value > rules.AffixLevels[1]) throw Invalid();
                    string name = AffixName(catalog, affix.Name);
                    if (!catalog.Affixes.ContainsKey(name)) throw Invalid();
                    Add(name, (int)effect.Value);
                    break;
                case "gem":
                    if (++gems > rules.Gem || effect.Type is 0 or < -1 or > 4 || effect.Rank is < 1 or > 2 ||
                        (effect.Type != -1 && !colors.Add(effect.Type))) throw Invalid();
                    if (effect.Id == 0) break;
                    if (!catalog.Compatible(new Socket(effect.Type, effect.Rank)).Any(gem => gem.Id == effect.Id)) throw Invalid();
                    foreach (var a in catalog.Gems[effect.Id].Affixes) Add(a, 1);
                    break;
                case "talent":
                    if (Data.Talents["general"].Any(t => t.Id == effect.Id))
                    {
                        if (++generalTalent > rules.GeneralTalent) throw Invalid();
                    }
                    else if (++classTalent > rules.ClassTalent ||
                        !(Data.Talents.GetValueOrDefault(career.Name)?.Any(t => t.Id == effect.Id) ?? false)) throw Invalid();
                    break;
                default: throw Invalid();
            }
        }
        if (fixedCount + gems > rules.FixedGem) throw Invalid();
        return (affixes, stats);
    }

    public BuildView Apply(BuildView build, Catalog catalog, SoulBrand? brand)
    {
        if (brand is null) return build;
        var (affixes, stats) = Evaluate(catalog, build.Loadout.Career, brand);
        var combined = new Dictionary<string, int>(build.Attributes, StringComparer.Ordinal);
        var totals = new Dictionary<string, double>(build.Stats, StringComparer.Ordinal);
        foreach (var (name, level) in affixes)
            combined[name] = combined.GetValueOrDefault(name) + level;
        foreach (var (name, value) in stats) totals[name] = totals.GetValueOrDefault(name) + value;
        return build with { Brand = brand, Attributes = combined, Stats = totals };
    }

    public SoulBrand Suggest(Catalog catalog, Career career, int grade, string affinity, IReadOnlyDictionary<string, int> desired)
    {
        int rarity = Math.Clamp(grade - 3, 0, Data.Rarities.Length - 1);
        int level = Data.Rarities[rarity].Cap;
        var effects = new List<BrandEffect>();
        var residual = new Dictionary<string, int>(desired, StringComparer.Ordinal);
        int damage = affinity == "magic" ? 11 : 13;
        var basic = Data.Attrs.FirstOrDefault(a => a.Id == damage && Available(a.Cls, career.Name)) ?? Data.Attrs.First(a => a.Id == 1);
        effects.Add(new("stat", basic.Id, basic.V[rarity][1]));
        var fixedAffixes = Data.Affixes.Where(a => Available(a.Cls, career.Name))
            .Select(a => (a.Id, Name: AffixName(catalog, a.Name)))
            .Where(a => residual.GetValueOrDefault(a.Name) > 0)
            .OrderByDescending(a => residual[a.Name]).ThenBy(a => a.Id)
            .Take(Math.Min(Data.Rules.Fixed, level - 1));
        int fixedCount = 0;
        // Materialize before changing residual levels used in the ordering.
        foreach (var a in fixedAffixes.ToArray())
        {
            int points = Math.Min(Data.Rules.AffixLevels[^1], residual[a.Name]);
            effects.Add(new("affix", a.Id, points));
            residual[a.Name] -= points;
            fixedCount++;
        }
        var rankTwo = catalog.Compatible(new Socket(-1, 2));
        var usedColors = new HashSet<int>();
        for (int i = 0; effects.Count < level && i < Data.Rules.Gem && i + fixedCount < Data.Rules.FixedGem; ++i)
        {
            var pick = rankTwo.Where(g => !usedColors.Contains(g.Type)).Select(g =>
            {
                int useful = g.Affixes.GroupBy(a => a).Sum(group => Math.Min(group.Count(), residual.GetValueOrDefault(group.Key)));
                return (Gem: g, Useful: useful, Waste: g.Affixes.Length - useful);
            }).Where(g => g.Useful > 0).OrderByDescending(g => g.Useful).ThenBy(g => g.Waste).ThenBy(g => g.Gem.Id)
                .FirstOrDefault().Gem;
            if (pick == null) break;
            usedColors.Add(pick.Type);
            effects.Add(new("gem", pick.Id, Type: pick.Type, Rank: pick.Rank));
            foreach (string a in pick.Affixes) residual[a] = Math.Max(0, residual.GetValueOrDefault(a) - 1);
        }
        foreach (var stat in Data.Attrs.Where(a => a.Id != basic.Id && Available(a.Cls, career.Name))
                     .OrderBy(a => a.Id is 2 or 4 ? 0 : 1).ThenBy(a => a.Id).Take(level - effects.Count))
            effects.Add(new("stat", stat.Id, stat.V[rarity][1]));
        return new(rarity, level, [.. effects]);
    }
}
