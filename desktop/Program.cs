using System.Security.Cryptography;
using System.Text.Json;
using Microsoft.AspNetCore.Hosting.Server;
using Microsoft.AspNetCore.Hosting.Server.Features;
using Microsoft.Web.WebView2.Core;
using Microsoft.Web.WebView2.WinForms;

namespace MistfallForge;

internal static class Program
{
    [STAThread]
    private static int Main(string[] args)
    {
        string dataRoot = Environment.GetEnvironmentVariable("MISTFALL_FORGE_HOME")
            ?? Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), "MistfallForge");
        if (args.Contains("--self-test"))
        {
            AppHost.SelfTest();
            return 0;
        }
        if (args.Contains("--self-test-catalog-refresh"))
        {
            AppHost.SelfTestCatalogRefresh().GetAwaiter().GetResult();
            return 0;
        }
        bool serverOnly = args.Contains("--serve");
        bool first = true;
        using var instance = serverOnly ? null : new Mutex(true, "MistfallForgeDesktop", out first);
        if (!first)
        {
            MessageBox.Show("Mistfall Forge уже запущен.", "Mistfall Forge");
            return 0;
        }
        WebApplication? app = null;
        try
        {
            (app, Uri entry) = AppHost.Start(dataRoot);
            if (serverOnly)
            {
                Console.WriteLine(entry.AbsoluteUri);
                app.WaitForShutdown();
            }
            else
            {
                ApplicationConfiguration.Initialize();
                Application.Run(new ForgeWindow(entry, dataRoot));
            }
            return 0;
        }
        catch (Exception ex)
        {
            if (serverOnly) Console.Error.WriteLine(ex.Message);
            else MessageBox.Show(ex.Message, "Mistfall Forge", MessageBoxButtons.OK, MessageBoxIcon.Error);
            return 1;
        }
        finally
        {
            if (app != null)
            {
                app.StopAsync(TimeSpan.FromSeconds(2)).GetAwaiter().GetResult();
                app.DisposeAsync().AsTask().GetAwaiter().GetResult();
            }
        }
    }
}

internal sealed class ForgeWindow : Form
{
    public ForgeWindow(Uri entry, string dataRoot)
    {
        Text = "Mistfall Forge";
        Width = 1480;
        Height = 940;
        MinimumSize = new(900, 660);
        StartPosition = FormStartPosition.CenterScreen;
        BackColor = System.Drawing.Color.FromArgb(8, 11, 9);
        using var process = System.Diagnostics.Process.GetCurrentProcess();
        if (process.MainModule?.FileName is { } applicationPath)
            Icon = System.Drawing.Icon.ExtractAssociatedIcon(applicationPath);
        var view = new WebView2 { Dock = DockStyle.Fill, DefaultBackgroundColor = BackColor };
        Controls.Add(view);
        Shown += async (_, _) =>
        {
            try
            {
                var env = await CoreWebView2Environment.CreateAsync(userDataFolder: Path.Combine(dataRoot, "WebView2"));
                await view.EnsureCoreWebView2Async(env);
                var web = view.CoreWebView2;
                web.Settings.IsStatusBarEnabled = false;
                web.Settings.AreDefaultContextMenusEnabled = false;
                web.Settings.AreDevToolsEnabled = false;
                web.Settings.IsZoomControlEnabled = false;
                web.NavigationStarting += (_, args) => args.Cancel = !Uri.TryCreate(args.Uri, UriKind.Absolute, out var nav) ||
                    nav.Scheme != entry.Scheme || nav.Host != entry.Host || nav.Port != entry.Port;
                web.NewWindowRequested += (_, args) => args.Handled = true;
                web.WebMessageReceived += (_, args) =>
                {
                    if (!Uri.TryCreate(args.Source, UriKind.Absolute, out var source) ||
                        source.GetLeftPart(UriPartial.Authority) != entry.GetLeftPart(UriPartial.Authority) ||
                        args.WebMessageAsJson != "\"open-data-folder\"") return;
                    try
                    {
                        Directory.CreateDirectory(dataRoot);
                        System.Diagnostics.Process.Start(new System.Diagnostics.ProcessStartInfo(dataRoot) { UseShellExecute = true });
                    }
                    catch (Exception ex)
                    {
                        MessageBox.Show(this, ex.Message, Text, MessageBoxButtons.OK, MessageBoxIcon.Error);
                    }
                };
                web.Navigate(entry.AbsoluteUri);
            }
            catch (Exception ex)
            {
                MessageBox.Show("Не удалось открыть WebView2. Проверьте установку Microsoft Edge WebView2 Runtime.\n\n" +
                    ex.Message, Text, MessageBoxButtons.OK, MessageBoxIcon.Error);
                Close();
            }
        };
    }
}

internal static class AppHost
{
    private static readonly string Root = AppContext.BaseDirectory;
    private static readonly JsonSerializerOptions Json = new(JsonSerializerDefaults.Web);
    private static readonly SemaphoreSlim SolverGate = new(1);
    private sealed record CatalogState(Catalog Catalog, GearCode Codec, Optimizer Optimizer);
    private record CodeRequest(string Code, int ActiveWeapon, SoulBrand? Brand = null);
    private record EncodeRequest(Loadout Loadout, int Version = 2, SoulBrand? Brand = null);
    private record LanguageRequest(string Value);
    private record ScaleRequest(int Value);
    private record BuildPreview(Guid Id, int Version, Dictionary<int, Gear>? Items, Dictionary<int, Gem?[]>? EquippedGems,
        Dictionary<string, int>? First, Dictionary<string, int>? Second, string? Error);

    public static (WebApplication, Uri) Start(string dataRoot)
    {
        var icons = IndexIcons();
        string downloadedIcons = Path.Combine(dataRoot,"catalog-icons");
        Dictionary<string,string> CatalogIcons()
        {
            var available=new Dictionary<string,string>(icons,StringComparer.OrdinalIgnoreCase);
            if (!Directory.Exists(downloadedIcons)) return available;
            foreach (var path in Directory.EnumerateFiles(downloadedIcons))
            {
                string file=Path.GetFileName(path);
                if (CatalogUpdate.SafeFile(file)) available[file]="/catalog-icons/"+Uri.EscapeDataString(file);
            }
            return available;
        }
        var baseline = LoadBundled("mistfall_season2.json", icons);
        var legacy = LoadBundled("mistfall_data.json", icons);
        var brands = LoadSoulBrands();
        string cache = Path.Combine(dataRoot, "catalog.json");
        string previousData = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), "MistfallBuildManager");
        string oldCache = Path.Combine(previousData, "mistfall_season2.json");
        CatalogState Create(Catalog catalog)
        {
            var codec = new GearCode(catalog, legacy);
            return new(catalog, codec, new Optimizer(catalog, codec, brands));
        }
        CatalogState state = Create(baseline);
        foreach (var candidate in new[] { cache, oldCache })
        {
            if (!File.Exists(candidate)) continue;
            try
            {
                using var stream = File.OpenRead(candidate);
                var catalog = new Catalog(stream, CatalogIcons());
                if (catalog.Preserves(baseline) && string.CompareOrdinal(catalog.Generated, baseline.Generated) >= 0)
                {
                    state = Create(catalog);
                    break;
                }
            }
            catch (Exception ex) when (ex is IOException or JsonException or InvalidOperationException
                or KeyNotFoundException or FormatException or ArgumentException) { }
        }
        var library = new Library(dataRoot, Path.Combine(previousData, "builds.json"));
        string languagePath = Path.Combine(dataRoot, "language.txt");
        string scalePath = Path.Combine(dataRoot, "ui-scale.txt");
        var updateGate = new SemaphoreSlim(1);
        var preferenceGate = new object();
        var builder = WebApplication.CreateBuilder(new WebApplicationOptions { ContentRootPath = Root, Args = [] });
        builder.WebHost.UseUrls("http://127.0.0.1:0")
            .ConfigureKestrel(options => options.Limits.MaxRequestBodySize = 4 * 1024 * 1024);
        builder.Logging.ClearProviders();
        var app = builder.Build();
        string token = Convert.ToHexString(RandomNumberGenerator.GetBytes(32));
        string sessionRoute = "/open/" + token;
        app.Use(async (context, next) =>
        {
            if (context.Request.Host.Host != "127.0.0.1")
            {
                context.Response.StatusCode = 400;
                return;
            }
            context.Response.Headers["X-Content-Type-Options"] = "nosniff";
            context.Response.Headers["Referrer-Policy"] = "no-referrer";
            context.Response.Headers["Content-Security-Policy"] =
                "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; " +
                "img-src 'self' data: blob:; connect-src 'self' blob:; worker-src 'self' blob:; frame-ancestors 'none'; base-uri 'none'";
            if (context.Request.Path == sessionRoute)
            {
                context.Response.Cookies.Append("mistfall_session", token, new CookieOptions { HttpOnly = true, SameSite = SameSiteMode.Strict });
                context.Response.Redirect("/");
                return;
            }
            if (context.Request.Path.StartsWithSegments("/api"))
            {
                if (context.Request.Cookies["mistfall_session"] != token)
                {
                    context.Response.StatusCode = 403;
                    return;
                }
                if (!HttpMethods.IsGet(context.Request.Method) &&
                    context.Request.Headers.Origin.ToString() != $"http://{context.Request.Host}")
                {
                    context.Response.StatusCode = 403;
                    return;
                }
                context.Response.Headers.CacheControl = "no-store";
            }
            try { await next(context); }
            catch (ArgumentException ex) { await Fail(400, ex.Message); }
            catch (OperationCanceledException) when (context.RequestAborted.IsCancellationRequested) { }
            catch (Exception ex)
            {
                if (app.Environment.IsDevelopment()) Console.Error.WriteLine(ex);
                await Fail(500, "internal-error");
            }
            async Task Fail(int status, string error)
            {
                if (context.Response.HasStarted) return;
                context.Response.StatusCode = status;
                await context.Response.WriteAsJsonAsync(new { error });
            }
        });
        app.UseDefaultFiles();
        app.UseStaticFiles();
        app.MapGet("/catalog-icons/{file}", async (string file, CancellationToken cancel) =>
        {
            if (!CatalogUpdate.SafeFile(file)) return Results.NotFound();
            string path=Path.Combine(downloadedIcons,file);
            if (!File.Exists(path) || new FileInfo(path).Length>1024*1024) return Results.NotFound();
            var bytes=await File.ReadAllBytesAsync(path,cancel);
            return CatalogUpdate.ImageType(bytes) is { } mime ? Results.Bytes(bytes,mime) : Results.NotFound();
        });
        app.MapGet("/api/catalog", () =>
        {
            var catalog = Volatile.Read(ref state).Catalog;
            var affinities = catalog.Careers.Values.ToDictionary(c => c.Id,
                c => c.Weapons.ToDictionary(w => w, w => catalog.Affinity(c.Id, w)));
            return new { catalog.Careers, catalog.Affixes, LegacyAffixes = legacy.Affixes, catalog.Wines, catalog.Generated, catalog.Version, Affinities = affinities, Optimizer.MaxTargets };
        });
        Catalog Table(int? version) => version == legacy.Version ? legacy : Volatile.Read(ref state).Catalog;
        app.MapGet("/api/gear/{career:int}/{slot:int}", (int career, int slot, int? version) =>
            Table(version).ForSlot(career, slot));
        app.MapGet("/api/gems/{type:int}/{rank:int}", (int type, int rank, int? version) =>
            Table(version).Compatible(new Socket(type, rank)));
        app.MapGet("/api/soul-brands", () => brands.Data);
        var modelFiles = new Lazy<Dictionary<(string, int), LocalModels.Entry>>(() =>
            LocalModels.Index(Path.Combine(dataRoot, "models"), Path.Combine(Root, "models"))
                .ToDictionary(file => (file.Kind, file.Id)));
        app.MapGet("/api/models", () =>
            modelFiles.Value.Values.Select(file => new { file.Kind, file.Id, file.Size }));
        app.MapGet("/api/models/{kind}/{id:int}", (string kind, int id) =>
        {
            if (!modelFiles.Value.TryGetValue((kind, id), out var file)) return Results.NotFound();
            var info = new FileInfo(file.Path);
            if (!info.Exists || info.Length != file.Size || (info.Attributes & FileAttributes.ReparsePoint) != 0)
                return Results.NotFound();
            return Results.File(file.Path, "model/gltf-binary");
        });
        app.MapPost("/api/decode", (CodeRequest request) =>
        {
            var active = Volatile.Read(ref state);
            return brands.Apply(active.Codec.Decode(request.Code, request.ActiveWeapon), active.Catalog, request.Brand);
        });
        app.MapPost("/api/upgrade-code", (CodeRequest request) =>
        {
            var active = Volatile.Read(ref state);
            var result = active.Codec.Upgrade(request.Code, request.ActiveWeapon);
            return result with { Build = brands.Apply(result.Build, active.Catalog, request.Brand) };
        });
        app.MapPost("/api/encode", (EncodeRequest request) =>
        {
            var active = Volatile.Read(ref state);
            return brands.Apply(active.Codec.Encode(request.Loadout, request.Version), active.Catalog, request.Brand);
        });
        app.MapPost("/api/optimize", async (OptimizeRequest request, CancellationToken cancellation) =>
        {
            if (!await SolverGate.WaitAsync(0, cancellation)) return Results.Conflict(new { error = "solver-busy" });
            try { return Results.Ok(Volatile.Read(ref state).Optimizer.Solve(request, cancellation)); }
            finally { SolverGate.Release(); }
        });
        app.MapGet("/api/builds", () => library.List(Volatile.Read(ref state).Codec));
        app.MapGet("/api/build-previews/{career:int}", (int career) =>
        {
            var active = Volatile.Read(ref state);
            return library.List(active.Codec).Where(row => row.Career == career).Select(row =>
            {
                try
                {
                    var first = active.Codec.Decode(row.Code, 10);
                    var table = first.Version == legacy.Version ? legacy : active.Catalog;
                    var second = table.Inspect(first.Loadout with { ActiveWeapon = 11 }, first.Code);
                    first = brands.Apply(first, active.Catalog, row.Brand);
                    second = brands.Apply(second, active.Catalog, row.Brand);
                    return new BuildPreview(row.Id, first.Version, first.Items, first.EquippedGems, first.Attributes, second.Attributes, null);
                }
                catch (ArgumentException ex) { return new BuildPreview(row.Id, 0, null, null, null, null, ex.Message); }
            }).ToArray();
        });
        app.MapPost("/api/builds", (SaveRequest request) =>
        {
            var active = Volatile.Read(ref state);
            return library.Save(request, active.Codec, build => brands.Evaluate(active.Catalog, build.Loadout.Career, request.Brand));
        });
        app.MapDelete("/api/builds/{id:guid}", (Guid id) =>
        {
            library.Delete(id, Volatile.Read(ref state).Codec);
            return Results.NoContent();
        });
        app.MapGet("/api/language", () =>
        {
            lock (preferenceGate)
            {
                string stored = File.Exists(languagePath) ? File.ReadAllText(languagePath).Trim() : "";
                return new { value = stored is "ru" or "en" or "es" ? stored : "ru" };
            }
        });
        app.MapPost("/api/language", (LanguageRequest request) =>
        {
            if (request.Value is not ("ru" or "en" or "es")) return Results.BadRequest();
            lock (preferenceGate)
            {
                Directory.CreateDirectory(dataRoot);
                File.WriteAllText(languagePath, request.Value);
            }
            return Results.NoContent();
        });
        static bool ValidScale(int value) => value is 0 or 100 or 115 or 130 or 145;
        app.MapGet("/api/ui-scale", () =>
        {
            lock (preferenceGate)
            {
                return new { value = File.Exists(scalePath) && int.TryParse(File.ReadAllText(scalePath), out int stored)
                    && ValidScale(stored) ? stored : 0 };
            }
        });
        app.MapPost("/api/ui-scale", (ScaleRequest request) =>
        {
            if (!ValidScale(request.Value)) return Results.BadRequest(new { error = "invalid-scale" });
            lock (preferenceGate)
            {
                Directory.CreateDirectory(dataRoot);
                File.WriteAllText(scalePath, request.Value.ToString(System.Globalization.CultureInfo.InvariantCulture));
            }
            return Results.NoContent();
        });
        app.MapPost("/api/catalog", async (HttpRequest request, CancellationToken cancel) =>
        {
            if (!request.HasJsonContentType()) return Results.BadRequest(new { error = "invalid-catalog" });
            await updateGate.WaitAsync(cancel);
            try
            {
                using var json = await JsonDocument.ParseAsync(request.Body, cancellationToken: cancel);
                var text = json.RootElement.GetRawText();
                using var contents = new MemoryStream(System.Text.Encoding.UTF8.GetBytes(text));
                var catalog = new Catalog(contents, CatalogIcons());
                var previous = Volatile.Read(ref state).Catalog;
                if (!catalog.Preserves(previous) || string.CompareOrdinal(catalog.Generated, previous.Generated) < 0)
                    return Results.BadRequest(new { error = "catalog-version" });
                Directory.CreateDirectory(dataRoot);
                string pending = cache + "." + Guid.NewGuid().ToString("N");
                try
                {
                    await File.WriteAllTextAsync(pending, text, cancel);
                    File.Move(pending, cache, true);
                    Volatile.Write(ref state, Create(catalog));
                }
                finally { if (File.Exists(pending)) File.Delete(pending); }
                return Results.Ok(new { catalog.Version, catalog.Generated });
            }
            catch (Exception ex) when (ex is JsonException or InvalidDataException or InvalidOperationException
                or KeyNotFoundException or FormatException or ArgumentException)
            {
                return Results.BadRequest(new { error = "invalid-catalog" });
            }
            finally { updateGate.Release(); }
        });
        app.MapPost("/api/catalog/refresh", async (CancellationToken cancel) =>
        {
            if (!await updateGate.WaitAsync(0,cancel)) return Results.Conflict(new { error = "catalog-busy" });
            try
            {
                var (pack,images)=await CatalogUpdate.Fetch(legacy,cancel);
                using var contents=new MemoryStream(pack);
                var active=Volatile.Read(ref state).Catalog;
                var known=CatalogIcons();
                var candidate=new Catalog(contents,known);
                if (!candidate.Preserves(active) || string.CompareOrdinal(candidate.Generated,active.Generated)<0)
                    return Results.BadRequest(new { error="catalog-version" });
                int found=await CatalogUpdate.CacheImages(images,downloadedIcons,known,cancel);
                if (found>0) { contents.Position=0; candidate=new Catalog(contents,CatalogIcons()); }
                Directory.CreateDirectory(dataRoot);
                string pending=cache+"."+Guid.NewGuid().ToString("N");
                try
                {
                    await File.WriteAllBytesAsync(pending,pack,cancel);
                    File.Move(pending,cache,true);
                    Volatile.Write(ref state,Create(candidate));
                }
                finally { if (File.Exists(pending)) File.Delete(pending); }
                return Results.Ok(new { candidate.Version, candidate.Generated, NewIcons=found });
            }
            catch (Exception ex) when (ex is HttpRequestException or IOException ||
                ex is OperationCanceledException && !cancel.IsCancellationRequested)
            {
                return Results.BadRequest(new { error="catalog-download" });
            }
            catch (Exception ex) when (ex is JsonException or ArgumentException or InvalidOperationException or
                KeyNotFoundException or FormatException or OverflowException or IndexOutOfRangeException)
            {
                return Results.BadRequest(new { error="invalid-catalog" });
            }
            finally { updateGate.Release(); }
        });
        app.MapPost("/api/catalog/pack", async (HttpContext context, CancellationToken cancel) =>
        {
            var limit=context.Features.Get<Microsoft.AspNetCore.Http.Features.IHttpMaxRequestBodySizeFeature>();
            if(limit is { IsReadOnly:false }) limit.MaxRequestBodySize=40*1024*1024;
            if(!context.Request.HasFormContentType) return Results.BadRequest(new { error="invalid-catalog" });
            if(!await updateGate.WaitAsync(0,cancel)) return Results.Conflict(new { error="catalog-busy" });
            try
            {
                var form=await context.Request.ReadFormAsync(cancel);
                var pack=form.Files.GetFile("catalog");
                if(form.Files.Count>321 || pack is not { Length:>0 and <= 4*1024*1024 })
                    return Results.BadRequest(new { error="invalid-catalog" });
                using var content=new MemoryStream();
                await pack.CopyToAsync(content,cancel);
                content.Position=0;
                var candidate=new Catalog(content,CatalogIcons());
                var active=Volatile.Read(ref state).Catalog;
                if(!candidate.Preserves(active) || string.CompareOrdinal(candidate.Generated,active.Generated)<0)
                    return Results.BadRequest(new { error="catalog-version" });
                int newIcons=0;
                var seen=new HashSet<string>(StringComparer.OrdinalIgnoreCase);
                foreach(var file in form.Files.Where(f=>f.Name=="icon"))
                {
                    string name=file.FileName;
                    if(file.Length is <=0 or >1024*1024 || !CatalogUpdate.SafeFile(name) ||
                        (!candidate.ReferencedIcons.Contains(name) && !candidate.ReferencedIcons.Contains(Path.GetFileNameWithoutExtension(name))) ||
                        !seen.Add(name)) continue;
                    using var image=new MemoryStream();
                    await file.CopyToAsync(image,cancel);
                    var bytes=image.ToArray();
                    if(CatalogUpdate.ImageType(bytes)==null) continue;
                    await CatalogUpdate.CacheIcon(downloadedIcons,name,bytes,cancel);
                    newIcons++;
                }
                if(newIcons>0) { content.Position=0; candidate=new Catalog(content,CatalogIcons()); }
                Directory.CreateDirectory(dataRoot);
                string pending=cache+"."+Guid.NewGuid().ToString("N");
                try
                {
                    var bytes=content.ToArray();
                    var existing=File.Exists(cache) ? await File.ReadAllBytesAsync(cache,cancel) : null;
                    if (existing is null || !bytes.AsSpan().SequenceEqual(existing))
                    {
                        await File.WriteAllBytesAsync(pending,bytes,cancel);
                        File.Move(pending,cache,true);
                    }
                    Volatile.Write(ref state,Create(candidate));
                }
                finally { if(File.Exists(pending)) File.Delete(pending); }
                return Results.Ok(new { candidate.Version, candidate.Generated, NewIcons=newIcons });
            }
            catch(Exception ex) when(ex is IOException or UnauthorizedAccessException or JsonException or ArgumentException or InvalidOperationException or
                KeyNotFoundException or FormatException or OverflowException)
            {
                return Results.BadRequest(new { error="invalid-catalog" });
            }
            finally { updateGate.Release(); }
        });
        app.Start();
        var addresses = app.Services.GetRequiredService<IServer>().Features.Get<IServerAddressesFeature>()!;
        return (app, new Uri(addresses.Addresses.Single() + sessionRoute));
    }

    private static Dictionary<string, string> IndexIcons()
    {
        string root = Path.Combine(Root, "wwwroot", "icons");
        Dictionary<string, string> files = new(StringComparer.OrdinalIgnoreCase);
        foreach (string path in Directory.GetFiles(root, "*", SearchOption.AllDirectories).Order())
        {
            if (Path.GetExtension(path) is not (".png" or ".webp")) continue;
            files.TryAdd(Path.GetFileName(path), "/icons/" +
                string.Join('/', Path.GetRelativePath(root, path).Split(Path.DirectorySeparatorChar).Select(Uri.EscapeDataString)));
        }
        return files;
    }

    private static Catalog LoadBundled(string file, IReadOnlyDictionary<string, string> icons)
    {
        using var stream = File.OpenRead(Path.Combine(Root, "data", file));
        return new Catalog(stream, icons);
    }

    private static SoulBrands LoadSoulBrands() => SoulBrands.Load(Path.Combine(Root, "data", "soulbrands.json"));

    public static async Task SelfTestCatalogRefresh()
    {
        var icons=IndexIcons();
        var legacy=LoadBundled("mistfall_data.json",icons);
        var baseline=LoadBundled("mistfall_season2.json",icons);
        var (bytes,images)=await CatalogUpdate.Fetch(legacy,CancellationToken.None);
        using var stream=new MemoryStream(bytes);
        var fresh=new Catalog(stream,icons);
        if (!fresh.Preserves(baseline) || string.CompareOrdinal(fresh.Generated,baseline.Generated)<0)
            throw new InvalidOperationException("Wiki catalog would change existing Gear Code mappings or downgrade the database.");
        Console.WriteLine($"Wiki catalog: {fresh.Items.Count} item IDs, {fresh.Affixes.Count} attributes, {images.Count} icon references.");
    }

    public static void SelfTest()
    {
        var icons = IndexIcons();
        var catalog = LoadBundled("mistfall_season2.json", icons);
        var legacy = LoadBundled("mistfall_data.json", icons);
        var codec = new GearCode(catalog, legacy);
        const string nativeCode = "BXkY0tHWGsKnQI4UQxo3WNq75U";
        var build = codec.Decode(nativeCode, 10);
        if (build.Version != 2 || build.Items[10].Id != 3071408 || build.Items[10].Icon == null ||
            !build.Loadout.Equipment[10].Gems.SequenceEqual(new[] { 224101, 223101, 222101 }) ||
            !build.EquippedGems[10].Select(g => g?.Id).SequenceEqual(new int?[] { 224101, 223101, 222101 }) ||
            codec.Encode(build.Loadout).Code != nativeCode)
            throw new InvalidOperationException("Season 2 fixture failed");
        const string weaponTwoOnly = "fytbnHPctSc4OUV6XWqgjXU";
        var partial = codec.Decode(weaponTwoOnly, 0);
        if (partial.Version != 2 || partial.Loadout.Career != 14 || partial.Loadout.ActiveWeapon != 11 ||
            partial.Items.Count != 1 || partial.Items[11].Id != 3050801 || partial.Items[11].Innate != "Strife" ||
            partial.Loadout.Equipment[11].Gems is not [0] || codec.Encode(partial.Loadout).Code != weaponTwoOnly)
            throw new InvalidOperationException("Weapon II-only Gear Code fixture failed");
        var moved = codec.Encode(new Loadout(14, new() { [10] = new(3050801, []) }));
        if (moved.Code != "fytbnHPctSc4OUV6nErjSXg" || moved.EquippedGems[10] is not [null])
            throw new InvalidOperationException("Weapon I-only Gear Code fixture failed");
        var old = codec.Encode(new Loadout(12, new() { [10] = new(3010401, []) }), 1);
        if (codec.Decode(old.Code, 10).Items[10].Id != 3010401 || codec.Decode(old.Code, 10).Version != 1)
            throw new InvalidOperationException("Season 1 fixture failed");
        const string legacySeer = "5H68cBdc3RS9gvmxT9ArXT1lRxgMDGZoq5honFXnYvZlQ";
        var legacyKit = codec.Decode(legacySeer, 10);
        var upgrade = codec.Upgrade(legacySeer, 10);
        var upgraded = codec.Decode(upgrade.Build.Code, 10);
        if (legacyKit.Version != 1 || legacyKit.Loadout.Career != 14 || legacyKit.Items[10].Id != 3050702 ||
            codec.Encode(legacyKit.Loadout, 1).Code != legacySeer ||
            upgraded.Version != 2 || upgraded.Loadout.Equipment.Count != 9 ||
            upgrade.RemappedGems < 1 || upgrade.ChangedSlots.Length < 1 ||
            legacyKit.Loadout.Equipment.Any(pair => !upgraded.Loadout.Equipment.TryGetValue(pair.Key, out var piece) ||
                piece.Id != pair.Value.Id || piece.Gems.Count(id => id != 0) != pair.Value.Gems.Count(id => id != 0)) ||
            codec.Upgrade(upgraded.Code, 10).Build.Code != upgraded.Code)
            throw new InvalidOperationException("Legacy Seer upgrade fixture failed");
        const string picturedSeer = "S58i1H4ASu5j2MxcO2Ge7JrzRaPi77P4VogD7XhWg2kTAmv3zLtX9M";
        var pictured = codec.Decode(picturedSeer, 10);
        var picturedSlots = new Dictionary<int, int> {
            [0] = 1160508, [1] = 1260507, [2] = 1360502, [3] = 1460509, [4] = 1560505,
            [5] = 1660102, [6] = 1760401, [10] = 3060804, [11] = 3010701
        };
        string[] picturedAffixes = ["Tenacious", "Side by Side", "Valor", "Wrath", "Seeker", "Fervor", "Seamless", "Blessing"];
        if (pictured.Version != 2 || pictured.Loadout.Career != 14 || pictured.Items.Count != 9 ||
            picturedSlots.Any(pair => pictured.Items[pair.Key].Id != pair.Value) ||
            pictured.Attributes.Count != picturedAffixes.Length ||
            picturedAffixes.Any(name => pictured.Attributes.GetValueOrDefault(name) != 4) ||
            codec.Encode(pictured.Loadout).Code != picturedSeer)
            throw new InvalidOperationException("Pictured Seer S2 fixture failed");
        const string acceptedInGame = "1e7pBRgbo01n6TDqHxpDuWEGS8jhju6CvoxsSxhlcKxhiGIAFdpY";
        var inGame = codec.Decode(acceptedInGame, 10);
        if (inGame.Version != 2 || inGame.Loadout.Career != 14 || inGame.Items.Count != 9 ||
            inGame.Items[10].Id != 3050708 || inGame.Items[0].Id != 1130508 ||
            inGame.Attributes.GetValueOrDefault("Wrath") != 4 || inGame.Attributes.GetValueOrDefault("Seeker") != 4 ||
            codec.Encode(inGame.Loadout).Code != acceptedInGame)
            throw new InvalidOperationException("In-game confirmed Gear Code fixture failed");
        var brands = LoadSoulBrands();
        var manual = new SoulBrand(3, 4, [new("stat", 11, 3.8), new("affix", 201, 2), new("gem", 222106, Type: 2, Rank: 1), new("talent", 601004)]);
        var withBrand = brands.Apply(pictured, catalog, manual);
        if (withBrand.Code != picturedSeer || withBrand.Attributes.GetValueOrDefault("Valor") != 6 ||
            withBrand.Attributes.GetValueOrDefault("Seeker") != 5 ||
            Math.Abs(withBrand.Stats.GetValueOrDefault("magicalIncrease") - pictured.Stats.GetValueOrDefault("magicalIncrease") - .038) > 1e-8)
            throw new InvalidOperationException("Soul Brand totals fixture failed");
        try
        {
            brands.Apply(pictured, catalog, new(3, 2, [new("stat", 13, 3.8)]));
            throw new InvalidOperationException("Soul Brand allowed a stat forbidden for a Seer");
        }
        catch (ArgumentException ex) when (ex.Message == "invalid-brand") { }
        if (legacy.Affixes["Elusive"] is not { Category: "utility", Icon: not null } ||
            catalog.Affixes["Aegis"] is not { Category: "defense", Icon: not null } || catalog.Affixes["Valor"].Category != "offense")
            throw new InvalidOperationException("Attribute appearance fixture failed");
        var restored = codec.Decode("2nLRaAUNMc9eyBpzOmw4i73E8", 10);
        if (restored.Items.Values.All(item => item.Id != 3070904 || item.Missing || item.Icon == null || item.Sockets.Length != 2) ||
            legacy.GetItem(1660403) is not { Missing: false, Sockets.Length: 3 } ||
            legacy.GetItem(1760401).Icon?.EndsWith("/T_UI_Icon_Equip_1220017.webp", StringComparison.Ordinal) != true ||
            pictured.Items[6].Icon is null)
            throw new InvalidOperationException("Legacy item overrides fixture failed");
        var solver = new Optimizer(catalog, codec);
        var result = solver.Solve(new(12, 11, "Javelin", 7, 0, true, new() { ["Dominion"] = 3 }), CancellationToken.None);
        if (!result.Exact || result.Build.Items[11].Grade != 7 || result.Build.Items[0].Grade != 6 ||
            result.Build.Items[10].Weapon != "Bow")
            throw new InvalidOperationException("Optimizer fixture failed");
        var timing = solver.Solve(new(12, 10, "Javelin", 6, 0, false,
            new() { ["Fervid"] = 3, ["Valor"] = 4, ["Aegis"] = 4, ["Swift"] = 3, ["Tenacious"] = 3, ["Resilience"] = 3 }),
            CancellationToken.None);
        if (!timing.Exact) throw new InvalidOperationException("Six-target fixture failed");
        var brandSolver = new Optimizer(catalog, codec, brands);
        var planned = brandSolver.Solve(new(14, 10, "Catalyst", 6, 0, false,
            new() { ["Valor"] = 4, ["Eloquence"] = 4, ["Tenacious"] = 4 }, AutoBrand: true), CancellationToken.None);
        var plannedGear = codec.Decode(planned.Build.Code, 10);
        if (!planned.Exact || planned.Build.Brand is not { Rarity: 3, Level: 5 } ||
            planned.Build.Attributes.GetValueOrDefault("Eloquence") != 4 ||
            plannedGear.Attributes.GetValueOrDefault("Eloquence") >= 4)
            throw new InvalidOperationException("Soul Brand optimizer fixture failed");
        Console.WriteLine($"Season 1/2 codec, in-game confirmed Seer, legacy migration, Soul Brand and optimizer passed. Six targets: {timing.Milliseconds:F0} ms.");
    }
}
