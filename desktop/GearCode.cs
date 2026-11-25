using System.Numerics;

namespace MistfallForge;

internal record GearUpgrade(BuildView Build, int[] ChangedSlots, int RemappedGems);

internal sealed class GearCode(Catalog current, Catalog legacy)
{
    private const string Alphabet = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz";

    public BuildView Decode(string? input, int activeWeapon)
    {
        if (input is null || input.Length > 640) throw new ArgumentException("code-length");
        var code = string.Concat(input.Where(c => !char.IsWhiteSpace(c)));
        if (code.Length is 0 or > 320) throw new ArgumentException("code-length");
        BigInteger number = BigInteger.Zero;
        foreach (char c in code)
        {
            int index = Alphabet.IndexOf(c);
            if (index < 0) throw new ArgumentException("code-character");
            number = number * 62 + index;
        }
        var buffer = number.ToByteArray(isUnsigned: true, isBigEndian: true);
        int position = 0;
        int Read(int width)
        {
            if (position + width > buffer.Length * 8) throw new ArgumentException("code-truncated");
            int value = 0;
            for (int i = 0; i < width; i++, position++)
                value |= ((buffer[position / 8] >> (position % 8)) & 1) << i;
            return value;
        }
        if (Read(24) != current.Head) throw new ArgumentException("code-header");
        int version = Read(10);
        Catalog table = version == current.Version ? current :
            version == legacy.Version ? legacy : throw new ArgumentException("code-version");
        int career = Read(4);
        if (!table.Careers.ContainsKey(career)) throw new ArgumentException("code-class");
        Dictionary<int, Piece> gear = new();
        foreach (int slot in table.Slots)
        {
            int[] ids = table.Native(career, slot);
            int index = Read(10);
            if (index >= ids.Length) throw new ArgumentException("code-item");
            int id = ids[index];
            if (id == 0) continue;
            int[] gems = new int[table.Holes.GetValueOrDefault(id)];
            for (int i = 0; i < gems.Length; i++)
            {
                int gemIndex = Read(10);
                if (gemIndex >= table.GemIds.Length) throw new ArgumentException("code-gem");
                gems[i] = table.GemIds[gemIndex];
            }
            gear[slot] = new(id, gems);
        }
        int active = activeWeapon is 10 or 11 ? activeWeapon :
            !gear.ContainsKey(10) && gear.ContainsKey(11) ? 11 : 10;
        return table.Inspect(new Loadout(career, gear, active), code);
    }

    public BuildView Encode(Loadout loadout, int version = 2)
    {
        Catalog table = version == current.Version ? current :
            version == legacy.Version ? legacy : throw new ArgumentException("code-version");
        if (loadout.Equipment is null || !table.Careers.ContainsKey(loadout.Career) ||
            loadout.ActiveWeapon is not (10 or 11) || loadout.Equipment.Keys.Except(table.Slots).Any())
            throw new ArgumentException("code-class");
        var buffer = new byte[64];
        Dictionary<int, Piece> equipment = new();
        int position = 0;
        void Write(int width, int value)
        {
            for (int i = 0; i < width; i++, position++)
                buffer[position / 8] |= (byte)(((value >> i) & 1) << (position % 8));
        }
        Write(24, table.Head);
        Write(10, table.Version);
        Write(4, loadout.Career);
        foreach (int slot in table.Slots)
        {
            loadout.Equipment.TryGetValue(slot, out var piece);
            int id = piece?.Id ?? 0;
            int index = Array.IndexOf(table.Native(loadout.Career, slot), id);
            if (index == -1) throw new ArgumentException("code-item");
            Write(10, index);
            if (id == 0) continue;
            var gems = piece?.Gems ?? [];
            int holes = table.Holes.GetValueOrDefault(id);
            if (gems.Length > holes) throw new ArgumentException("code-gem");
            var writtenGems = new int[holes];
            for (int i = 0; i < holes; i++)
            {
                int gem = i < gems.Length ? gems[i] : 0;
                int gemIndex = Array.IndexOf(table.GemIds, gem);
                if (gemIndex == -1) throw new ArgumentException("code-gem");
                Write(10, gemIndex);
                writtenGems[i] = gem;
            }
            equipment[slot] = new(id, writtenGems);
        }
        BigInteger number = new(buffer.AsSpan(0, (position + 7) / 8), isUnsigned: true, isBigEndian: true);
        var code = new Stack<char>();
        while (number != BigInteger.Zero)
        {
            number = BigInteger.DivRem(number, 62, out var remainder);
            code.Push(Alphabet[(int)remainder]);
        }
        return table.Inspect(loadout with { Equipment = equipment }, new string(code.ToArray()));
    }

    public GearUpgrade Upgrade(string? input, int activeWeapon)
    {
        var old = Decode(input, activeWeapon);
        if (old.Version == current.Version) return new(old, [], 0);
        var knownGems = current.GemIds.ToHashSet();
        var equipment = new Dictionary<int, Piece>();
        var changed = new List<int>();
        int remapped = 0;
        foreach (var (slot, piece) in old.Loadout.Equipment)
        {
            var previous = legacy.GetItem(piece.Id);
            var item = current.GetItem(piece.Id);
            if (item.Missing || !current.Native(old.Loadout.Career, slot).Contains(piece.Id) ||
                item.Sockets.Length != current.Holes.GetValueOrDefault(piece.Id))
                throw new ArgumentException("upgrade-item");
            var occupied = piece.Gems.Select((id, index) => (Id: id, Index: index)).Where(pair => pair.Id != 0).ToArray();
            if (occupied.Length > item.Sockets.Length) throw new ArgumentException("upgrade-gem");
            int[] pending = new int[item.Sockets.Length], best = [];
            int bestScore = int.MinValue;
            void Fit(int index, int score)
            {
                if (index == occupied.Length)
                {
                    if (score > bestScore) { bestScore = score; best = (int[])pending.Clone(); }
                    return;
                }
                var (id, sourceIndex) = occupied[index];
                var original = legacy.Gems.GetValueOrDefault(id);
                for (int targetIndex = 0; targetIndex < pending.Length; ++targetIndex)
                {
                    if (pending[targetIndex] != 0) continue;
                    var socket = item.Sockets[targetIndex];
                    foreach (var gem in current.Compatible(socket))
                    {
                        if (!knownGems.Contains(gem.Id)) continue;
                        bool sameEffects = original != null && gem.Type == original.Type && gem.Rank == original.Rank &&
                            SameEffects(gem.Affixes, original.Affixes);
                        if (!sameEffects && gem.Id != id) continue;
                        pending[targetIndex] = gem.Id;
                        Fit(index + 1, score + (sameEffects ? 100 : 0) + (gem.Id == id ? 10 : 0) +
                            (sourceIndex == targetIndex ? 1 : 0));
                        pending[targetIndex] = 0;
                    }
                }
            }
            Fit(0, 0);
            if (bestScore == int.MinValue) throw new ArgumentException("upgrade-gem");
            equipment.Add(slot, new(piece.Id, best));
            remapped += occupied.Length - best.Where(id => id != 0).Intersect(occupied.Select(pair => pair.Id)).Sum(id =>
                Math.Min(best.Count(x => x == id), occupied.Count(pair => pair.Id == id)));
            if (previous.Missing || !SameEffects(Effects(legacy, previous, piece.Gems), Effects(current, item, best))) changed.Add(slot);
        }
        return new(Encode(old.Loadout with { Equipment = equipment }, current.Version), [.. changed], remapped);
    }

    private static bool SameEffects(IEnumerable<string> first, IEnumerable<string> second) =>
        first.Order(StringComparer.Ordinal).SequenceEqual(second.Order(StringComparer.Ordinal), StringComparer.Ordinal);

    private static IEnumerable<string> Effects(Catalog catalog, Gear item, int[] gems)
    {
        if (item.Innate is { Length: > 0 } innate) yield return innate;
        foreach (int id in gems)
            if (id != 0 && catalog.Gems.TryGetValue(id, out var gem))
                foreach (string affix in gem.Affixes) yield return affix;
    }
}
