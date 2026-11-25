using System.Diagnostics;

namespace MistfallForge;

internal record OptimizeRequest(int Career, int ActiveWeapon, string Weapon, int Grade, int Wine,
    bool SecondWeapon, Dictionary<string, int> Targets, SoulBrand? Brand = null, bool AutoBrand = false);
internal record OptimizeResult(BuildView Build, Dictionary<string, int> Wine, Dictionary<string, int> Targets,
    string Affinity, bool Exact, double Milliseconds);

internal sealed class Optimizer(Catalog catalog, GearCode codec, SoulBrands? brands = null)
{
    public const int MaxTargets = 16;
    private record Candidate(ulong Vector, Piece Piece, int Penalty, int Extra, int Used, int Grade);
    private record State(State? Previous, Candidate? Pick, int Penalty, int Extra, int Used, int Grade)
    {
        public (int, int, int, int) Cost => (Penalty, Extra, Used, -Grade);
    }

    public OptimizeResult Solve(OptimizeRequest request, CancellationToken cancel)
    {
        var watch = Stopwatch.StartNew();
        if (!catalog.Careers.TryGetValue(request.Career, out var career) ||
            !career.Weapons.Contains(request.Weapon)) throw new ArgumentException("choose-weapon");
        if (request.Grade is < 3 or > 7 || request.Targets is null)
            throw new ArgumentException("invalid-targets");
        if (request.Targets.Count is 0 or > MaxTargets)
            throw new ArgumentException("invalid-targets");
        string[] names = request.Targets.Keys.ToArray();
        if (names.Any(name => !catalog.Affixes.ContainsKey(name))) throw new ArgumentException("invalid-targets");
        var index = names.Select((name, i) => (name, i)).ToDictionary(x => x.name, x => x.i);
        int[] desired = names.Select(name => Math.Clamp(request.Targets[name], 1, catalog.Affixes[name].Cap)).ToArray();
        int[] maxDigits = desired.Select(level => level + 1).ToArray();
        var wine = catalog.Wines.FirstOrDefault(w => w.Id == request.Wine) ?? new Wine(0, "", 0, 0);
        string affinity = catalog.Affinity(request.Career, request.Weapon);
        var goals = names.Select((name, i) => (name, desired[i])).ToDictionary(x => x.name, x => x.Item2);
        var brand = request.AutoBrand ? brands?.Suggest(catalog, career, request.Grade, affinity, goals) : request.Brand;
        var fixedEffects = brands?.Evaluate(catalog, request.Career, brand).Affixes ?? [];
        var (initial, _) = AttributeVector(fixedEffects.SelectMany(pair => Enumerable.Repeat(pair.Key, pair.Value)));
        int weaponSlot = request.ActiveWeapon == 11 ? 11 : 10;
        int[] slots = [0, 1, 2, 3, 4, 5, 6, weaponSlot];
        var socketOptions = new Dictionary<Socket, (ulong Vector, int Gem, int Extra)[]>();
        var states = new Dictionary<ulong, State> { [initial] = new(null, null, 0, 0, 0, 0) };
        int width = names.Length >= 7 ? 900 : names.Length == 6 ? 1800 : names.Length == 5 ? 3200 : 5000;

        foreach (int slot in slots)
        {
            cancel.ThrowIfCancellationRequested();
            var candidates = SlotCandidates(slot);
            if (candidates.Length == 0) throw new ArgumentException("no-items");
            Dictionary<ulong, State> next = new();
            foreach (var (vector, state) in states)
            {
                cancel.ThrowIfCancellationRequested();
                foreach (var candidate in candidates)
                {
                    ulong combined = Add(vector, candidate.Vector);
                    var cost = (state.Penalty + candidate.Penalty, state.Extra + candidate.Extra,
                        state.Used + candidate.Used, -(state.Grade + candidate.Grade));
                    if (next.TryGetValue(combined, out var existing) && existing.Cost.CompareTo(cost) <= 0) continue;
                    next[combined] = new(state, candidate, cost.Item1, cost.Item2, cost.Item3, -cost.Item4);
                }
            }
            states = next.Count <= width ? next : next.OrderBy(entry =>
            {
                var rank = Difference(entry.Key);
                var s = entry.Value;
                return (rank.Over, rank.Remaining, rank.Missing, s.Penalty, s.Extra, s.Used, -s.Grade);
            }).Take(width).ToDictionary();
        }

        var best = states.MinBy(entry =>
        {
            var d = Difference(entry.Key);
            int tier = d.Over == 0 && d.Missing == 0 ? 0 : d.Over == 0 && d.Remaining == 0 ? 1 : 2;
            return (tier, d.Over, d.Remaining, d.Missing, d.MaxDeficit, entry.Value.Penalty,
                entry.Value.Extra, entry.Value.Used, -entry.Value.Grade);
        });
        Dictionary<int, Piece> equipment = new();
        State path = best.Value;
        for (int i = slots.Length - 1; i >= 0; i--, path = path.Previous!)
            equipment[slots[i]] = path.Pick!.Piece;
        if (request.SecondWeapon)
        {
            int other = weaponSlot == 10 ? 11 : 10;
            var filler = catalog.ForSlot(request.Career, other).Where(g => g.Grade <= request.Grade)
                .OrderByDescending(g => g.Weapon != request.Weapon && g.Grade >= 3)
                .ThenByDescending(g => g.Grade).ThenByDescending(g => g.Sockets.Length).FirstOrDefault();
            if (filler != null) equipment[other] = new Piece(filler.Id, []);
        }
        var build = codec.Encode(new Loadout(request.Career, equipment, weaponSlot));
        if (brands != null) build = brands.Apply(build, catalog, brand);
        Dictionary<string, int> boosts = new(StringComparer.Ordinal);
        int remaining = wine.Slots;
        if (Difference(best.Key).Over == 0)
        {
            var priority = Enumerable.Range(0, names.Length)
                .OrderByDescending(i => desired[i] - Digit(best.Key, i)).ToArray();
            for (int level = 1; level <= wine.Per; level++)
            foreach (int i in priority)
            {
                if (remaining == 0 || desired[i] - Digit(best.Key, i) < level) continue;
                boosts[names[i]] = level;
                remaining--;
            }
        }
        bool exact = goals.All(goal => build.Attributes.GetValueOrDefault(goal.Key) + boosts.GetValueOrDefault(goal.Key) == goal.Value);
        return new(build, boosts, goals, affinity, exact, watch.Elapsed.TotalMilliseconds);

        static int Digit(ulong vector, int index) => (int)((vector >> (4 * index)) & 15);

        ulong Add(ulong left, ulong right)
        {
            while (right != 0)
            {
                int position = System.Numerics.BitOperations.TrailingZeroCount(right) & ~3;
                ulong digit = (right >> position) & 15;
                ulong value = Math.Min((ulong)maxDigits[position / 4], ((left >> position) & 15) + digit);
                left = (left & ~(15UL << position)) | (value << position);
                right &= ~(15UL << position);
            }
            return left;
        }

        (int Over, int Remaining, int Missing, int MaxDeficit) Difference(ulong vector)
        {
            int overshoot = 0, missing = 0, coverable = 0, max = 0;
            for (int i = 0; i < desired.Length; i++)
            {
                int delta = desired[i] - Digit(vector, i);
                if (delta < 0) { overshoot -= delta; continue; }
                missing += delta;
                coverable += Math.Min(delta, wine.Per);
                max = Math.Max(max, delta);
            }
            return (overshoot, missing - Math.Min(wine.Slots, coverable), missing, max);
        }

        (ulong Vector, int Extra) AttributeVector(IEnumerable<string> attributes)
        {
            ulong vector = 0;
            int extra = 0;
            foreach (string attribute in attributes)
            {
                if (index.TryGetValue(attribute, out int i))
                    vector = Add(vector, 1UL << (4 * i));
                else extra++;
            }
            return (vector, extra);
        }

        (ulong Vector, int Gem, int Extra)[] GemOptions(Socket socket)
        {
            if (socketOptions.TryGetValue(socket, out var found)) return found;
            var options = new Dictionary<ulong, (ulong, int, int)> { [0] = (0, 0, 0) };
            foreach (Gem gem in catalog.Compatible(socket))
            {
                var (vector, extra) = AttributeVector(gem.Affixes);
                if (vector == 0) continue;
                if (!options.TryGetValue(vector, out var old) || (extra, gem.Id).CompareTo((old.Item3, old.Item2)) < 0)
                    options[vector] = (vector, gem.Id, extra);
            }
            return socketOptions[socket] = options.Values.ToArray();
        }

        Candidate[] SlotCandidates(int slot)
        {
            int grade = request.Grade == 7 && slot != weaponSlot ? 6 : request.Grade;
            var items = catalog.ForSlot(request.Career, slot).Where(item => item.Grade == grade &&
                (slot != weaponSlot || item.Weapon == request.Weapon));
            Dictionary<ulong, Candidate> bestByVector = new();
            foreach (Gear item in items)
            {
                cancel.ThrowIfCancellationRequested();
                var (innate, offTarget) = AttributeVector(item.Innate == null ? [] : [item.Innate]);
                var rolls = new Dictionary<ulong, (int[] Gems, int Extra, int Used)> { [innate] = ([], offTarget, 0) };
                foreach (Socket socket in item.Sockets)
                {
                    Dictionary<ulong, (int[] Gems, int Extra, int Used)> next = new();
                    foreach (var (vector, roll) in rolls)
                    foreach (var option in GemOptions(socket))
                    {
                        ulong combined = Add(vector, option.Vector);
                        int extra = roll.Extra + option.Extra;
                        int used = roll.Used + (option.Gem == 0 ? 0 : 1);
                        if (next.TryGetValue(combined, out var old) && (old.Extra, old.Used).CompareTo((extra, used)) <= 0)
                            continue;
                        next[combined] = ([.. roll.Gems, option.Gem], extra, used);
                    }
                    rolls = next;
                }
                int penalty = slot is 5 or 6 ? AccessoryPenalty(item, affinity) : 0;
                foreach (var (vector, roll) in rolls)
                {
                    if (bestByVector.TryGetValue(vector, out var old) &&
                        (old.Penalty, old.Extra, old.Used, old.Piece.Id).CompareTo((penalty, roll.Extra, roll.Used, item.Id)) <= 0) continue;
                    bestByVector[vector] = new(vector, new Piece(item.Id, roll.Gems), penalty, roll.Extra, roll.Used, item.Grade);
                }
            }
            return bestByVector.Values.ToArray();
        }
    }

    private static int AccessoryPenalty(Gear item, string affinity)
    {
        var (preferred, other) = affinity == "magic" ? ("magical", "physical") : ("physical", "magical");
        bool Has(string kind) => item.Stats.GetValueOrDefault(kind + "Increase") > 0 ||
            item.Stats.GetValueOrDefault(kind + "Reduction") > 0;
        return Has(preferred) ? 0 : Has(other) ? 2 : 1;
    }
}
