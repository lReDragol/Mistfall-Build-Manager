import { language, setLanguage, t, term, effectText, catalogItemName, catalogItemLore, catalogGemName, talentName, talentDescription } from "./locale.js";
import { legacyItemName, legacyItemLore } from "./legacy-strings.js";

const $ = id => document.getElementById(id);
const slots = [10, 11, 0, 1, 2, 3, 4, 5, 6];
const BRAND_SLOT = Symbol("soul-brand");
const glyphs = ["⬡","▥","◇","▯","⌑","◈","◌"];
const rarityColors = ["#574b3c","#5b5149","#7b7b78","#2d9a45","#267aa5","#81459e","#c28a32","#d9b957"];
const perPage = 36;
const slotCache = new Map(), gemCache = new Map();
let catalog, current, savedId, bank = [], view = "classes", activeSlot = 10, right = "goals", page = 0;
let targets = new Map(), wineBoosts = {}, solverWeapon = "", busy = false, lastAuto = false;
let renderRevision = 0, scene, scenePromise;
let careerId, solverGrade=6, libraryBusy=false, libraryRevision=0, previews=new Map();
let importBuild, importWeapon=0, importRevision=0, importTimer, importBusy=false;
let attributeMode, metadataRow, routeRevision=0, autoImportName="";
let effectFilter="*", socketIndex=0, gemQuery="", gemFocus, saveAsCopy=false;
let rarityFilter=0, gearFocus;
let uiScale=0, scaleWrites=Promise.resolve();
let brandData, brandDraft, brandSlot=0, brandQuery="";
let focusUpgrade;
const scales=[100,115,130,145];
const FILTER=Symbol("gear effect");
const routes=["classes","library","import","editor","preview"];

function node(tag, attrs = {}, ...children) {
    const element = document.createElement(tag);
    for (const [name, value] of Object.entries(attrs)) {
        if (value == null) continue;
        if (name.startsWith("aria-")) element.setAttribute(name,String(value));
        else if (value !== false) element.setAttribute(name,value === true ? "" : String(value));
    }
    element.append(...children.filter(c => c != null));
    return element;
}
const option = (id, label) => node("option", {value:id}, label);
const empty = key => node("p", {class:"empty"}, t(key));
const icon = item => item?.icon ? node("img", {src:item.icon, alt:"", decoding:"async"}) : null;
function gearArt(item,slot) {
    const fallback=node("span",{class:"empty-glyph","aria-hidden":"true"},glyphs[slot]??"◇");
    const image=icon(item);
    if(!image) return item ? fallback : node("span",{"aria-hidden":"true"},"—");
    image.addEventListener("error",()=>image.replaceWith(fallback),{once:true});
    return image;
}
const affixInfo = (name,version=2) => (version===1 ? catalog.legacyAffixes?.[name] : catalog.affixes[name])
    ?? catalog.affixes[name] ?? catalog.legacyAffixes?.[name];
const affixCategory = (name,version) => affixInfo(name,version)?.category ?? "utility";
const affixIcon = (name,version) => node("span",{class:"affix-icon","data-category":affixCategory(name,version),"aria-hidden":"true"},
    icon(affixInfo(name,version))??"◇");
const selected = slot => current?.items?.[slot];
const affixOrder=["offense","defense","utility"];
const className = id => term("class", id);
const rarity = grade => term("rarity", grade);
const slotName = slot => term("slot", slot);
const itemName = item => item.missing ? t("missingItemId",{id:item.id})
    : catalogItemName(item.name) ?? (language==="ru" ? legacyItemName(item.name) : term("item", item.name));
const itemLore = item => catalogItemLore(item.description) ??
    (language==="ru" ? legacyItemLore(item.name):undefined) ?? item.description;
const affixName = name => term("affix", name);
const levelLabel = level => t("levelShort",{level});
const gemName = gem => catalogGemName(gem.name) ?? (language==="en"?gem.name:
    [term("gem",gem.type),gem.affixes.map(affixName).join(" · ")].filter(Boolean).join(" — "));
const groupKey = item => [item.name,item.grade,item.weapon].join("|");

async function api(path, value, method = value === undefined ? "GET" : "POST") {
    const options = {method};
    if (value !== undefined) {
        if(value instanceof FormData) options.body=value;
        else {
            options.headers = {"Content-Type":"application/json"};
            options.body = value instanceof File ? value : JSON.stringify(value);
        }
    }
    const response = await fetch("/api/" + path, options);
    if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new Error(body?.error || "internal-error");
    }
    return response.status === 204 ? null : response.json();
}

function message(id, key = "", kind = "", values = {}) {
    const output = $(id);
    output.textContent = key ? t(key, values) : "";
    output.dataset.kind = kind;
    output._message = {key, kind, values};
}

const autoScale=()=>screen.width>=2300 && innerWidth>=1280 ? 115 : 100;
function paintScale() {
    const percent=uiScale || autoScale();
    document.body.style.setProperty("--ui-zoom",String(percent/100));
    $("ui-scale").value=String(uiScale);
    $("ui-scale").options[0].textContent=t("scaleAuto")+" · "+autoScale()+"%";
}
function chooseScale(value) {
    uiScale=value;
    paintScale();
    scaleWrites=scaleWrites.then(()=>api("ui-scale",{value})).catch(error=>message("app-status",error.message,"error"));
}

function translate() {
    document.documentElement.lang = language;
    for (const label of document.querySelectorAll("[data-t]")) label.textContent = t(label.dataset.t);
    for (const input of document.querySelectorAll("[data-ph]")) {
        input.placeholder = t(input.dataset.ph);
        input.setAttribute("aria-label", input.placeholder);
    }
    for (const control of document.querySelectorAll("[data-label]")) control.setAttribute("aria-label",t(control.dataset.label));
    for (const control of document.querySelectorAll("[data-title]")) control.title=t(control.dataset.title);
    for (const label of document.querySelectorAll("[data-lang]"))
        label.setAttribute("aria-pressed", label.dataset.lang === language);
    for (const id of ["solver-status","code-status","preview-status","preview-totals-status","model-status","save-status","app-status","import-status","metadata-status","brand-status"]) {
        const old = $(id)._message;
        if (old) message(id, old.key, old.kind, old.values);
    }
    paintHeader();
    paintScale();
    if (view === "classes") paintClasses();
    if (view === "editor" && current) paintEditor();
    if (view === "library") paintLibrary();
    if (view === "import") paintImport();
    if (view === "preview") paintPreview();
    if ($("attributes-dialog").open) paintAttributeDialog();
}

function setOptions(select, pairs, value) {
    select.replaceChildren(...pairs.map(([id, label]) => option(id, label)));
    select.value = String(value ?? pairs[0]?.[0] ?? "");
    if (select.selectedIndex < 0 && pairs.length) select.selectedIndex = 0;
}

function paintHeader() {
    $("class-nav").hidden = view==="classes";
    $("main").dataset.view=view;
    $("class-name").textContent = careerId ? className(careerId) : "";
    if(view!=="library") $("catalog-file").closest("details").open=false;
    $("preview-link").hidden = !current || !["editor","preview"].includes(view);
    $("preview-link").href = view==="preview" ? "#editor" : "#preview";
    $("preview-link").textContent = t(view==="preview" ? "backEditor" : "preview");
    for (const link of document.querySelectorAll("[data-page]"))
        link.setAttribute("aria-current", link.dataset.page === (view==="preview"?"editor":view) ? "page" : "false");
}

function buildCount(count) {
    return t("buildCount-"+new Intl.PluralRules(language).select(count),{count});
}

function paintClasses() {
    const counts=new Map();
    for (const row of bank) counts.set(row.career,(counts.get(row.career)??0)+1);
    $("class-grid").replaceChildren(...Object.values(catalog.careers).map(c => {
        const button = node("button",{type:"button",class:"class-card","data-career":c.id},
            node("strong",{},className(c.id)),node("span",{},buildCount(counts.get(c.id)??0)));
        button.onclick = () => exclusive("app-status",async () => {
            if(current?.loadout.career!==c.id) resetEditor(await api("encode",{loadout:{career:c.id,equipment:{},activeWeapon:10}}));
            careerId=c.id;
            $("library-search").value="";
            if(location.hash==="#"+c.id+"/library") await navigate();
            else location.hash=c.id+"/library";
        });
        return button;
    }));
}

async function navigate() {
    const revision=++routeRevision;
    let next=location.hash.slice(1);
    const saved=next.startsWith("build/")?bank.find(row=>row.id===next.slice(6)):null;
    if (saved) {
        if (savedId!==saved.id) {
            const build=await api("decode",{code:saved.code,activeWeapon:saved.activeWeapon,brand:saved.brand});
            if (revision!==routeRevision) return;
            lastAuto=false;
            accept(build,{imported:true,id:saved.id});
        }
        next="editor";
    }
    const route=next.match(/^(\d+)\/(library|import|editor|preview)$/);
    if (route && catalog.careers[Number(route[1])]) {
        const id=Number(route[1]);
        if(current?.loadout.career!==id) {
            const build=await api("encode",{loadout:{career:id,equipment:{},activeWeapon:10}});
            if(revision!==routeRevision) return;
            resetEditor(build);
        }
        careerId=id;
        next=route[2];
    }
    view = careerId && routes.includes(next) ? next : "classes";
    for (const name of routes) $(name).hidden = name !== view;
    $("code-panel").hidden = view !== "editor";
    scene?.setVisible(view === "preview");
    paintHeader();
    if (view === "classes") paintClasses();
    if (view === "library") {
        await loadPreviews();
    }
    if (view === "editor") {
        paintEditor();
        if(focusUpgrade && saved?.id===focusUpgrade) $("upgrade-code").focus();
    }
    focusUpgrade=undefined;
    if (view === "import") paintImport();
    if (view === "preview") {
        paintPreview();
        openScene();
    }
}

function getSlot(career, slot, version) {
    const key = [career, slot, version].join("/");
    if (!slotCache.has(key)) slotCache.set(key, api("gear/" + career + "/" + slot + "?version=" + version)
        .catch(error => { slotCache.delete(key); throw error; }));
    return slotCache.get(key);
}

function getGems(socket, version) {
    const key = socket.type + "/" + socket.rank + "?version=" + version;
    if (!gemCache.has(key)) gemCache.set(key, api("gems/" + key)
        .catch(error => { gemCache.delete(key); throw error; }));
    return gemCache.get(key);
}

function chooseSlot(slot) {
    if(busy) return;
    activeSlot = slot;
    socketIndex=0;
    gemQuery="";
    page = 0;
    $("gear-search").value = "";
    rarityFilter=0;
    effectFilter="*";
    if(view==="editor") {
        paintEditor();
        if(slot===BRAND_SLOT) $("edit-brand").focus({preventScroll:true});
    }
}

function equipmentTile(slot, item, attrs, onClick) {
    const button = node("button", {type:"button",class:"slot"+(item?" equipped":""),...attrs},
        item ? gearArt(item,slot) : node("span",{class:"empty-glyph","aria-hidden":"true"},glyphs[slot]??"♢"),
        node("span",{},slotName(slot)));
    button.style.setProperty("--rarity",rarityColors[item?.grade??0]);
    button.onclick=onClick;
    return button;
}

function brandTile(brand,{compact=false,named=false,editId=null}={}) {
    const info=brandData?.rarities[brand?.rarity];
    const label=t("soulBrand"), value=info?t("brand"+info.key)+" · "+levelLabel(brand.level):t("brandNone");
    const title=label+" · "+value;
    const image=info?gearArt(info):node("span",{class:"empty-glyph","aria-hidden":"true"},"♨");
    const interactive=Boolean(editId||info);
    const tile=node(interactive?"button":"div",{
        type:interactive?"button":null,id:editId,disabled:editId&&busy,"data-brand-slot":true,"aria-label":title,title,
        class:(named?"import-piece":compact?"card-slot":"slot"+(info?" equipped":""))+" brand-slot"
    },named?node("span",{class:"import-piece-icon"},image):image,
        named?node("span",{class:"import-piece-text"},node("small",{},label),node("strong",{},value)):
        compact?null:node("span",{},label+(info?" · "+levelLabel(brand.level):"")));
    tile.style.setProperty("--rarity",info?rarityColors[brand.rarity+3]:"var(--line)");
    if(editId) {
        if(editId==="edit-brand") tile.setAttribute("aria-pressed",activeSlot===BRAND_SLOT);
        tile.onclick=()=>{
            if(busy || (view==="editor" && activeSlot===BRAND_SLOT)) return;
            chooseSlot(BRAND_SLOT);
            if(view==="preview") location.hash="editor";
        };
    }
    else if(info) tile.onclick=()=>showDetail(label,[node("div",{class:"detail-lead"},gearArt(info),
        node("div",{},node("strong",{},t("brand"+info.key)),node("p",{class:"intro"},levelLabel(brand.level))))]);
    return tile;
}

function withBrand(tiles,brand) {
    const layout=[...tiles];
    layout.splice(slots.indexOf(4)+1,0,brand);
    return layout;
}

function paintActiveWeapon(root) {
    for(const button of root.querySelectorAll("[data-active]")) {
        const slot=Number(button.dataset.active);
        button.setAttribute("aria-pressed",slot===current.loadout.activeWeapon);
        button.setAttribute("aria-label",slotName(slot));
    }
}

function paintEditor() {
    if(!current) return;
    const {loadout} = current;
    const career = catalog.careers[loadout.career];
    const isBrand=activeSlot===BRAND_SLOT;
    $("slot-title").textContent = isBrand?t("soulBrand"):slotName(activeSlot);
    $("gear-effect-filter").hidden=isBrand;
    $("item-detail").hidden=isBrand;
    $("item-detail").parentElement.toggleAttribute("data-brand-active",isBrand);
    $("brand-form").hidden=!isBrand;
    $("gear-count").textContent = Object.keys(loadout.equipment).length + " / 9";
    $("brand-export-note").hidden=!current.brand;
    $("slot-grid").replaceChildren(...withBrand(slots.map(slot => {
        const item = selected(slot);
        const button = equipmentTile(slot,item,{
            "aria-pressed":slot === activeSlot, title:item ? itemName(item) : slotName(slot),
        },() => chooseSlot(slot));
        button.disabled = busy;
        return button;
    }),brandTile(current.brand,{editId:"edit-brand"})));
    paintActiveWeapon($("editor"));
    paintRarityFilter();
    paintEffectFilter();
    setOptions($("weapon"), career.weapons.map(name => [name,term("weapon",name)]), solverWeapon);
    solverWeapon = $("weapon").value;
    const affinity=catalog.affinities?.[loadout.career]?.[solverWeapon]??"physical";
    $("affinity").textContent=t(affinity+"Short");
    $("affinity").title=t(affinity);
    paintRarity();
    setOptions($("wine"), catalog.wines.map(w => [w.id,term("wine",w.id) + "  ·  " + w.slots + " / +" + w.per]), $("wine").value || catalog.wines[0]?.id);
    $("wine").disabled = !$("use-wine").checked;
    const hasGear=Object.keys(loadout.equipment).length>0;
    if (!$("code").dataset.dirty) $("code").value = hasGear ? current.code : "";
    const legacyCode=current.version!==catalog.version;
    $("copy-code").disabled=!hasGear || legacyCode;
    $("legacy-export-note").hidden=!legacyCode || !hasGear;
    $("weapon-export-note").hidden=Boolean(loadout.equipment[10] || !loadout.equipment[11]);
    $("code-version").textContent = "v" + current.version;
    const editing=bank.find(row=>row.id===savedId);
    $("edit-session").hidden=!editing;
    $("editing-label").textContent=editing?t("editingName",{name:editing.name}):"";
    $("save-build").textContent=t(editing?"applyChanges":"save");
    paintTargets();
    paintTotals();
    if(isBrand) paintBrandForm();
    paintItems();
}

function paintEffectFilter() {
    const name=effectFilter;
    const button=$("effect-open");
    button.replaceChildren(...(name!=="*"&&name!=="-"?[affixIcon(name,current.version)]:[]),
        name==="*"?t("allEffects"):name==="-"?t("noInnate"):affixName(name));
    $("effect-clear").hidden=name==="*";
}

function selectEffectFilter(name) {
    effectFilter=name;
    page=0;
    paintEffectFilter();
    $("item-grid").scrollTop=0;
    paintItems();
}

function rarityButtons(root, grades, value, select, solver=false) {
    root.replaceChildren(...grades.map(grade => {
        const name=grade ? rarity(grade) : t("allRarity");
        const button=node("button",{type:"button",class:"diamond-button",
            "aria-pressed":grade===value,"aria-label":name,title:solver && grade===7 ? name+" · "+t("holyHint"):name},node("i",{"aria-hidden":"true"}));
        button.style.setProperty("--rarity",rarityColors[grade]);
        button.onclick=()=>select(grade);
        return button;
    }));
}

function paintRarity() {
    const root=$("solver-rarity");
    $("rarity-name").textContent=rarity(solverGrade);
    rarityButtons(root,[3,4,5,6,7],solverGrade,grade=>{
        solverGrade=grade;
        if(lastAuto) optimize();
        else { paintRarity(); root.querySelector('[aria-pressed="true"]').focus(); }
    },true);
}

function paintRarityFilter() {
    const root=$("rarity-filter");
    $("rarity-filter-name").textContent=rarityFilter ? rarity(rarityFilter) : t("allRarity");
    rarityButtons(root,activeSlot===BRAND_SLOT?[0,3,4,5,6]:[0,1,2,3,4,5,6,7],rarityFilter,grade=>{
        rarityFilter=grade;
        paintRarityFilter();
        root.querySelector('[aria-pressed="true"]').focus();
        page=0;
        $("item-grid").scrollTop=0;
        paintItems();
    });
}

async function paintItems() {
    const revision = ++renderRevision;
    const {loadout, version} = current;
    const slot = activeSlot;
    if(slot===BRAND_SLOT) {
        paintBrandCatalog();
        return;
    }
    try {
        const available = await getSlot(loadout.career, slot, version);
        if (revision !== renderRevision) return;
        const q = $("gear-search").value.trim().toLocaleLowerCase(language);
        const grade = rarityFilter;
        const effect = effectFilter;
        const items = available.filter(item => (!grade || grade === item.grade) &&
            (effect === "*" || (effect === "-" && !item.innate) || effect === item.innate) &&
            (!q || [itemName(item), item.name, item.id, term("weapon", item.weapon ?? ""), item.innate && affixName(item.innate)]
                .join(" ").toLocaleLowerCase(language).includes(q)));
        const picked = selected(slot);
        const groups = new Map();
        for (const item of items) {
            const key = groupKey(item);
            if (!groups.has(key)) groups.set(key, []);
            groups.get(key).push(item);
        }
        const families = [...groups.values()];
        $("catalog-count").textContent = String(families.length);
        const numPages = Math.max(1, Math.ceil(families.length / perPage));
        page = Math.min(page, numPages - 1);
        const sublist = families.slice(page * perPage, (page + 1) * perPage);
        const grid=$("item-grid"), scroll=grid.scrollTop;
        grid.replaceChildren(...(sublist.length ? sublist.map(family => {
            const active = family.find(item => picked?.id === item.id);
            const item = active ?? family.find(candidate=>!candidate.innate) ?? family[0];
            const badge = effect!=="*" ? item.innate : null;
            const button = node("button", {type:"button", class:"gear-card", "aria-pressed":Boolean(active),
                title:itemName(item) + " · " + rarity(item.grade)},
            icon(item) ?? node("span",{class:"glyph"},"◇"), node("b",{},itemName(item)),
            node("small",{},badge ? affixIcon(badge,version) : null,
                badge ? affixName(badge) : family.length > 1 ? t("variants",{count:family.length}) : rarity(item.grade)));
            button.style.setProperty("--rarity",rarityColors[item.grade] ?? rarityColors[0]);
            button.disabled = busy;
            button.addEventListener("click", () => {
                if (!active) {
                    socketIndex=0; gemQuery=""; gearFocus=item.id;
                    changeKit(equipment => { equipment[slot] = {id:item.id,gems:[]}; }, item.weapon);
                }
            });
            return button;
        }) : [empty("noMatches")]));
        grid.scrollTop=scroll;
        if (!busy && gearFocus!==undefined) {
            if(picked?.id===gearFocus) grid.querySelector('[aria-pressed="true"]')?.focus({preventScroll:true});
            gearFocus=undefined;
        }
        const pager = $("item-pagination");
        pager.replaceChildren();
        if (numPages > 1) {
            const previous = node("button",{type:"button",disabled:page === 0,"aria-label":t("previousPage")},"‹");
            const next = node("button",{type:"button",disabled:page + 1 === numPages,"aria-label":t("nextPage")},"›");
            previous.onclick = () => { page--; $("item-grid").scrollTop=0; paintItems(); };
            next.onclick = () => { page++; $("item-grid").scrollTop=0; paintItems(); };
            pager.append(previous,node("span",{},(page + 1) + " / " + numPages),next);
        }
        await paintDetail(picked, slot, version, revision,
            picked ? available.filter(item => groupKey(item) === groupKey(picked)) : []);
    } catch (error) {
        if (revision === renderRevision) message("code-status", error.message, "error");
    }
}

function statValue(name, value) {
    const percent = ["blockRate","physicalIncrease","magicalIncrease","physicalReduction","magicalReduction","criticalReduction",
        "brandStat8","brandStat9","brandStat17","brandStat21","brandStat31","brandStat32","brandStat42"].includes(name);
    return new Intl.NumberFormat(language,{maximumFractionDigits:2, style:percent ? "percent" : "decimal"}).format(value);
}

function brandStatLabel(attr) {
    const key={atk:"attack",def:"defence",hp:"maxHealth",cres:"criticalReduction",mdmg:"magicalIncrease",
        mres:"magicalReduction",pdmg:"physicalIncrease",pres:"physicalReduction"}[attr.stat]??"brandStat"+attr.id;
    return t(key);
}

const brandKinds={stat:"brandKindStat",affix:"brandKindAffix",gem:"brandKindGem",talent:"brandKindTalent"};
const brandAffixKey=name=>name==="Deft"&&!catalog.affixes.Deft ? "Sleight of Hand" :
    name==="Skypiercing"&&!catalog.affixes.Skypiercing ? "Sky Piercer" : name;
const socketIcon=({rank,type})=>{
    const code={1:"A",2:"D",3:"B",4:"C"}[type];
    return code?gearArt({icon:"/icons/gem/SPR_UI_EquipGemHole_Gem_"+rank+"_"+code+".webp"}):null;
};
const brandNumber=(val,pct)=>"+"+new Intl.NumberFormat(language,{maximumFractionDigits:1}).format(val)+(pct?" %":"");
function brandButton(id,label,pressed,onClick,className="",...content) {
    const button=node("button",{type:"button",id,class:className,"aria-pressed":pressed,"aria-label":label},...content);
    button.onclick=onClick;
    return button;
}

const draftBrand=()=>brandDraft?{...brandDraft,effects:brandDraft.effects.filter(Boolean)}:null;
const brandIsDirty=()=>JSON.stringify(draftBrand())!==JSON.stringify(current?.brand??null);
function resetBrandDraft() {
    brandDraft=current?.brand?structuredClone(current.brand):null;
    brandSlot=0;
    brandQuery="";
    message("brand-status");
}
function paintBrandActions() {
    const dirty=brandIsDirty();
    $("brand-actions").hidden=!dirty;
    $("brand-apply").disabled=!dirty || busy;
}

function selectBrand(rarity) {
    if(busy || rarity===(brandDraft?.rarity??-1)) return;
    if(rarity<0) brandDraft=null;
    else {
        const prior=brandDraft, level=Math.min(prior?.level??1,brandData.rarities[rarity].max);
        const effects=(prior?.effects??[]).slice(0,level);
        for(const effect of effects) if(effect?.kind==="stat" && effect.id) {
            const [lo,normal,hi]=brandData.attrs.find(a=>a.id===effect.id).v[rarity];
            if(!(effect.value>=lo && effect.value<=hi)) effect.value=normal;
        }
        brandDraft={rarity,level,effects};
    }
    brandQuery="";
    message("brand-status");
    paintBrandCatalog();
    paintBrandForm(rarity<0?(brandIsDirty()?"brand-apply":"edit-brand"):"brand-rarity-"+rarity);
}

function brandChoices(target,choices,active,onPick,{searchKey="brandSearch",emptyChoice,gemVersion}={}) {
    const search=node("input",{type:"search",value:brandQuery,placeholder:t(searchKey),"aria-label":t(searchKey)});
    search.onkeydown=event=>{if(event.key==="Enter") event.preventDefault();};
    const list=node("div",{class:"brand-choice-list"+(gemVersion?" gem-list":"")});
    const priorScroll=Number(target.dataset.scroll)||0;
    const render=()=>{
        const query=search.value.trim().toLocaleLowerCase(language);
        const matches=choices.filter(c=>!query||(c.label+" "+(c.search??"")).toLocaleLowerCase(language).includes(query));
        const button=c=>{
            const id="brand-choice-"+c.id;
            const content=gemVersion ? [gemLine(c.gem,gemVersion,t("emptySocket"))] :
                [c.art?.(),node("strong",{},c.label), c.note?node("small",{},c.note):null];
            return brandButton(id,c.label,c.id===active,()=>{if(c.id!==active) onPick(c,id);},
                gemVersion?"gem-row":"brand-option",...content);
        };
        list.replaceChildren(...(emptyChoice?[button(emptyChoice)]:[]),...matches.map(button),...(matches.length?[]:[empty("noMatches")]));
    };
    search.oninput=()=>{brandQuery=search.value;render();list.scrollTop=0;};
    target.append(search,list);
    render();
    list.scrollTop=priorScroll;
}

function paintBrandCatalog() {
    const q=$("gear-search").value.trim().toLocaleLowerCase(language), grid=$("item-grid"), scroll=grid.scrollTop;
    const cards=brandData.rarities.map((info,i)=>{
        const label=t("brand"+info.key), grade=i+3, gradeText=rarity(grade);
        if ((rarityFilter && rarityFilter!==grade) ||
            (q && ![label,info.name,gradeText].join(" ").toLocaleLowerCase(language).includes(q))) return null;
        const btn=brandButton("brand-rarity-"+i,label,i===brandDraft?.rarity,()=>selectBrand(i),
            "gear-card brand-card",gearArt(info),node("b",{},label),node("small",{},gradeText));
        btn.style.setProperty("--rarity",rarityColors[grade]);
        btn.disabled=busy;
        return btn;
    }).filter(Boolean);
    $("catalog-count").textContent=String(cards.length);
    $("item-pagination").replaceChildren();
    grid.replaceChildren(...(cards.length?cards:[empty("noMatches")]));
    grid.scrollTop=scroll;
}

function paintBrandForm(focus="") {
    const d=brandDraft, r=brandData.rarities[d?.rarity], version=catalog.version;
    $("brand-title").textContent=r?t("brand"+r.key):t("soulBrand");
    $("brand-grade").textContent=r?rarity(d.rarity+3):"";
    $("brand-remove").hidden=!r;
    $("brand-empty").hidden=Boolean(r);
    $("brand-config").hidden=!r;
    paintBrandActions();
    const fields=$("brand-effects"), editor=$("brand-effect-editor");
    const scroll=focus.startsWith("brand-choice-") ? editor.querySelector(".brand-choice-list")?.scrollTop??0 : 0;
    editor.replaceChildren();
    fields.replaceChildren();
    if(!r) { if(focus) $(focus)?.focus(); return; }
    brandSlot=Math.min(brandSlot,d.level-1);
    const career=catalog.careers[current.loadout.career].name;
    const allowed=x=>!x.cls||x.cls.includes(career);
    const attrs=brandData.attrs.filter(allowed), affixes=brandData.affixes.filter(allowed),
        talents=[...(brandData.talents[career]??[]),...brandData.talents.general];
    const nameFor=e=>{
        if(!e) return t("none");
        if(e.kind==="stat" && e.id) return brandStatLabel(attrs.find(a=>a.id===e.id));
        if(e.kind==="affix" && e.id) return affixName(brandAffixKey(affixes.find(a=>a.id===e.id).name));
        if(e.kind==="gem" && e.type) return socketLabel(e);
        if(e.kind==="talent" && e.id) {
            const talent=talents.find(a=>a.id===e.id);
            return talent?talentName(talent):t(brandKinds.talent);
        }
        return t(brandKinds[e.kind]);
    };
    const describeSlot=e=>{
        const name=nameFor(e);
        if(e?.kind==="affix" && e.id) return name+" +"+e.value;
        if(e?.kind==="stat" && e.id && Number.isFinite(e.value))
            return name+" "+brandNumber(e.value,attrs.find(a=>a.id===e.id).pct);
        return name;
    };
    const levels=$("brand-level");
    levels.replaceChildren(...Array.from({length:r.max},(_,i)=>{
        const level=i+1;
        return brandButton("brand-level-"+level,t("brandLevel")+" "+level,level===d.level,()=>{
            d.level=level;
            d.effects=d.effects.slice(0,level);
            brandQuery="";
            paintBrandForm("brand-level-"+level);
        },level>r.cap?"brand-reshape":"",level);
    }));
    $("brand-cap").textContent=t("brandCap",{cap:r.cap,max:r.max});
    for(let i=0;i<d.level;i++){
        const title=t("brandEffect",{index:i+1}), summary=describeSlot(d.effects[i]);
        fields.append(brandButton("brand-slot-"+i,title+" · "+summary,i===brandSlot,()=>{
            brandSlot=i;
            brandQuery="";
            paintBrandForm("brand-slot-"+i);
        },"brand-effect-slot",node("small",{},title),node("strong",{},summary)));
    }
    const e=d.effects[brandSlot], kind=e?.kind, index=brandSlot;
    const title=t("brandEffect",{index:index+1});
    const update=(value,id)=>{
        d.effects[index]=value;
        message("brand-status");
        paintBrandForm(id);
    };
    const types=node("div",{class:"brand-types brand-segments",role:"group","aria-label":title});
    for(const [type,key] of Object.entries(brandKinds)){
        const label=t(key);
        types.append(brandButton("brand-kind-"+type,label,type===kind,()=>{
            if(type===kind) return;
            brandQuery="";
            update({kind:type,id:0,value:0,type:0,rank:1},"brand-kind-"+type);
        },"",label));
    }
    const remove=e?node("button",{type:"button",class:"text-button",id:"brand-clear"},t("brandClear")):null;
    if(remove) remove.onclick=()=>{brandQuery="";update(null,"brand-slot-"+index);};
    editor.append(node("div",{class:"brand-effect-header"},node("h3",{},title),remove),types);
    const pick=(choices,apply)=>{
        const target=node("div",{class:"brand-options","data-scroll":scroll});
        editor.append(target);
        brandChoices(target,choices,e.id,apply);
    };
    if(kind==="stat"){
        pick(attrs.map(a=>({id:a.id,label:brandStatLabel(a),search:a.name,note:brandNumber(a.v[d.rarity][1],a.pct)})),
            (a,id)=>update({...e,id:a.id,value:attrs.find(x=>x.id===a.id).v[d.rarity][1]},id));
        const attr=attrs.find(a=>a.id===e.id);
        if(attr){
            const [lo,,hi]=attr.v[d.rarity];
            const input=node("input",{type:"number",inputmode:"decimal",required:true,min:lo,max:hi,step:attr.pct?".1":"1",
                value:Number.isFinite(e.value)?e.value:"","aria-label":brandStatLabel(attr)});
            input.oninput=()=>{
                e.value=input.valueAsNumber;
                $("brand-slot-"+index).lastElementChild.textContent=describeSlot(e);
                $("brand-slot-"+index).setAttribute("aria-label",title+" · "+describeSlot(e));
                paintBrandActions();
            };
            editor.append(node("label",{class:"brand-value"},node("span",{},brandStatLabel(attr)),input,
                node("span",{},brandNumber(lo,attr.pct)+" – "+brandNumber(hi,attr.pct))));
        }
    } else if(kind==="affix"){
        pick(affixes.map(a=>{
            const name=brandAffixKey(a.name);
            return {id:a.id,label:affixName(name),search:a.name,art:()=>affixIcon(name,version)};
        }),(a,id)=>update({...e,id:a.id,value:e.value||1},id));
        if(e.id) {
            const [lo,hi]=brandData.rules.affixLevels;
            editor.append(node("div",{class:"brand-segments",role:"group","aria-label":t("brandLevel")},
                ...Array.from({length:hi-lo+1},(_,i)=>{
                    const v=i+lo, id="brand-points-"+v;
                    return brandButton(id,"+"+v,e.value===v,()=>update({...e,value:v},id),"","+"+v);
                })));
        }
    } else if(kind==="talent"){
        pick(talents.map(a=>({id:a.id,label:talentName(a),search:a.name})).sort((a,b)=>a.label.localeCompare(b.label,language)),
            (a,id)=>update({...e,id:a.id},id));
        const talent=talents.find(a=>a.id===e.id);
        const desc=talent&&talentDescription(talent);
        if(desc) editor.append(node("p",{class:"intro"},desc));
    } else if(kind==="gem"){
        const sockets=[1,2].flatMap(rank=>[1,2,3,4,-1].map(type=>({type,rank})));
        editor.append(node("div",{class:"brand-socket-list",role:"group","aria-label":t("brandKindGem")},...sockets.map(s=>{
            const label=socketLabel(s), id="brand-socket-"+s.type+"-"+s.rank;
            return brandButton(id,label,s.type===e.type && s.rank===e.rank,()=>{
                if(s.type===e.type && s.rank===e.rank) return;
                brandQuery="";
                update({...e,...s,id:0},id);
            },"brand-option brand-socket",node("span",{},
                socketIcon(s)??node("span",{class:"empty-glyph","aria-hidden":"true"},"◇"),
                node("small",{},t("gemRank")+" "+s.rank)),node("strong",{},term("gem",s.type)));
        })));
        if(e.type){
            const target=node("div",{class:"brand-options","data-scroll":scroll},empty("loadingGems"));
            editor.append(target);
            getGems(e,version).then(gems=>{
                if(!target.isConnected) return;
                target.replaceChildren();
                const choices=gems.map(gem=>({id:gem.id,gem,label:gemName(gem),search:[gem.name,gem.affixes.map(affixName).join(" ")].join(" ")}));
                choices.sort((a,b)=>a.label.localeCompare(b.label,language));
                brandChoices(target,choices,e.id,(c,id)=>update({...e,id:c.id},id),{
                    searchKey:"gemSearch",emptyChoice:{id:0,label:t("emptySocket")},gemVersion:version
                });
                if(focus.startsWith("brand-choice-")) $(focus)?.focus({preventScroll:true});
            }).catch(error=>{if(target.isConnected) target.replaceChildren(node("p",{class:"message","data-kind":"error"},t(error.message)));});
        }
    } else editor.append(node("p",{class:"intro"},t("brandChooseKind")));
    if(focus) $(focus)?.focus({preventScroll:focus.startsWith("brand-choice-")});
}

function statPills(stats) {
    return Object.entries(stats).filter(([,v]) => v !== 0).map(([name,value]) =>
        node("span",{},t(name) + " ",node("b",{},statValue(name,value))));
}
async function paintDetail(item, slot, version, revision, variants) {
    const host = $("item-detail");
    if (!item) { host.replaceChildren(empty("chooseItem")); return; }
    const remove = node("button",{type:"button",class:"quiet",disabled:busy},t("clearSlot"));
    remove.onclick = () => changeKit(equipment => { delete equipment[slot]; });
    host.replaceChildren(node("div",{class:"item-heading"},node("div",{},node("h3",{},itemName(item)),
        node("p",{class:"gear-innate"},rarity(item.grade), item.innate ? node("span",{},t("innate")+":") : null,
            item.innate ? affixChip(item.innate,version) : node("span",{},t("noInnate")))),remove),
        node("div",{class:"stats"},...statPills(item.stats)));
    if (item.missing) { host.append(node("p",{class:"message"},t("unknownItem"))); return; }
    if (variants.length > 1) {
        const pick = node("select",{disabled:busy});
        setOptions(pick, variants.map(variant => [variant.id,(variant.innate ? affixName(variant.innate) : t("noInnate"))
            + " · " + (variant.sockets.map(socket => term("gem",socket.type) + " " + socket.rank).join(", ") || "—")
            + " · #" + variant.id]), item.id);
        pick.onchange = () => { socketIndex=0; gemQuery=""; changeKit(equipment => { equipment[slot] = {id:Number(pick.value),gems:[]}; },item.weapon); };
        host.append(node("label",{class:"variant"},t("variant"),pick));
    }
    if (!item.sockets.length) { host.append(node("p",{class:"message"},t("noSockets"))); return; }
    socketIndex=Math.min(socketIndex,item.sockets.length-1);
    const workspace=node("div",{class:"socket-workspace"});
    host.append(workspace);
    await paintSocketWorkspace(workspace,item,slot,version,revision);
}

const socketLabel = socket => term("gem",socket.type)+" · "+t("gemRank")+" "+socket.rank;
const affixChip = (name,version) => node("span",{class:"affix-chip","data-category":affixCategory(name,version)},
    affixIcon(name,version),node("span",{},affixName(name)));
function gemLine(gem,version,emptyText=t("none")) {
    return node("span",{class:"gem-content",title:gem?gemName(gem):null},gem ? icon(gem) : null,gem
        ? node("span",{},node("strong",{},term("gem",gem.type)+" · "+t("gemRank")+" "+gem.rank),
            node("span",{class:"gem-effects"},...gem.affixes.map(name=>affixChip(name,version))))
        : node("span",{class:"intro"},emptyText));
}

async function paintSocketWorkspace(host,item,slot,version,revision) {
    const index=socketIndex, chosen=item.sockets[index], currentIds=current.loadout.equipment[slot].gems;
    const equipped=current.equippedGems?.[slot]??[];
    const socketButtons=item.sockets.map((socket,i) => {
        const gem=equipped[i];
        const button=node("button",{type:"button",class:"socket-card","aria-pressed":i===index,disabled:busy},
            node("strong",{},socketLabel(socket)),
            gem ? node("span",{class:"gem-effects"},...(gem.affixes.map(name=>affixChip(name,version))))
                : node("span",{class:"intro"},currentIds[i]?"#"+currentIds[i]:t("socketEmpty")));
        button.onclick=()=>{
            socketIndex=i; gemQuery="";
            paintSocketWorkspace(host,item,slot,version,revision).catch(error=>message("code-status",error.message,"error"));
            host.querySelector('.socket-card[aria-pressed="true"]')?.focus();
        };
        return button;
    });
    const search=node("input",{type:"search",value:gemQuery,placeholder:t("gemSearch"),"aria-label":t("gemSearch")});
    const results=node("div",{class:"gem-list","aria-live":"polite"},empty("loadingGems"));
    const count=node("span",{class:"counter"});
    host.replaceChildren(node("section",{class:"socket-rail"},node("h3",{},t("equippedSockets")),...socketButtons),
        node("section",{class:"gem-browser"},node("div",{class:"section-head"},node("h3",{},t("chooseGem")),count),search,results));
    const gems=await getGems(chosen,version);
    if(revision!==renderRevision || socketIndex!==index || !results.isConnected) return;
    const order=(gem)=>gem.affixes.map(affixName).join(" + ");
    const sorted=[...gems].sort((a,b)=>b.rank-a.rank||order(a).localeCompare(order(b),language)||a.id-b.id);
    function paintGems() {
        const query=gemQuery.trim().toLocaleLowerCase(language);
        const visible=sorted.filter(gem=>!query||[order(gem),gem.affixes.join(" "),gemName(gem),gem.name,gem.id].join(" ").toLocaleLowerCase(language).includes(query));
        const active=currentIds[index]??0;
        count.textContent=String(visible.length);
        function choice(gem) {
            const id=gem?.id??0;
            const button=node("button",{type:"button",class:"gem-row","data-gem-id":id,"aria-pressed":id===active,disabled:busy},
                gemLine(gem,version,t("emptySocket")));
            button.onclick=()=>{
                if(id===active) return;
                gemFocus=id;
                changeKit(equipment=>{
                    const piece=equipment[slot];
                    piece.gems=Array.from({length:item.sockets.length},(_,i)=>i===index?id:piece.gems[i]||0);
                });
            };
            return button;
        }
        results.replaceChildren(choice(null),...visible.map(choice),...(visible.length?[]:[empty("noMatches")]));
    }
    search.oninput=()=>{ gemQuery=search.value; paintGems(); results.scrollTop=0; };
    paintGems();
    if (gemFocus!==undefined && !busy) {
        results.querySelector("[data-gem-id='"+gemFocus+"']")?.focus({preventScroll:true});
        gemFocus=undefined;
    }
}

function paintTargets() {
    $("target-list").replaceChildren(...(targets.size ? [...targets].map(([name,level]) => {
        const info = catalog.affixes[name];
        const input = node("select",{"aria-label":affixName(name) + " · " + t("level")});
        setOptions(input,Array.from({length:info.cap},(_,i) => [i+1,levelLabel(i+1)]),level);
        input.onchange = () => { targets.set(name,Number(input.value)); goalChanged(); };
        const change=node("button",{type:"button",class:"target-name",title:t("chooseTarget")},affixName(name));
        change.onclick = () => openAttributes(name);
        const remove = action("×","removeTarget",() => { targets.delete(name); goalChanged(); paintTargets(); $("target-add").focus(); });
        remove.setAttribute("aria-label",t("removeTarget")+" · "+affixName(name));
        return node("div",{class:"target-row","data-category":affixCategory(name)},affixIcon(name),change,input,remove);
    }) : [empty("needTargets")]));
    $("target-add").disabled = busy || targets.size>=catalog.maxTargets;
    $("target-add").title = targets.size>=catalog.maxTargets?t("maxTargets",{max:catalog.maxTargets}):t("addTarget");
    $("solve").disabled = busy || !targets.size;
}

function goalChanged() {
    lastAuto=false;
    wineBoosts={};
    message("solver-status");
    paintTotals();
}

function attributeRows(values, boosts={},version=2) {
    const display={...values};
    for (const [name,level] of Object.entries(boosts)) display[name]=(display[name]??0)+level;
    const entries=Object.entries(display).filter(([,v])=>v>0).sort((a,b)=>b[1]-a[1]||affixName(a[0]).localeCompare(affixName(b[0]),language));
    return entries.length ? entries.map(([name,level]) => {
        const info=affixInfo(name,version);
        const bar=node("span",{class:"attribute-bar","aria-hidden":"true"},
            ...Array.from({length:7},(_,i)=>node("i",{class:i<(values[name]??0)?"full":i<level?"bonus":""})));
        const effect=effectText(info?.effects[Math.min(info.cap,level)-1]);
        const row=node("button",{type:"button",class:"attribute-row","data-category":affixCategory(name,version),
            title:[affixName(name),effect,t("details")].filter(Boolean).join(" · ")},
            affixIcon(name,version),
            node("span",{class:"attribute-middle"},node("span",{},affixName(name)),bar),
            node("span",{class:"attribute-level"},levelLabel(level),boosts[name]?node("small",{}," +"+boosts[name]):null));
        row.onclick=()=>showAttribute(name,level,version,boosts[name]);
        return row;
    }) : [empty("missingEffect")];
}

function action(symbol,label,callback,extra="") {
    const button=node("button",{type:"button",class:"square-action "+extra,"aria-label":t(label),title:t(label)},symbol);
    button.onclick=callback;
    return button;
}

function weaponSwitch(active, callback) {
    return [10,11].map(slot => {
        const button=node("button",{type:"button","aria-label":slotName(slot),"aria-pressed":active===slot},slot===10?"I":"II");
        button.onclick=()=>callback(slot,button);
        return button;
    });
}

function showDetail(title,content) {
    $("detail-title").textContent=title;
    $("detail-content").replaceChildren(...content);
    if(!$("detail-dialog").open) $("detail-dialog").showModal();
}

function showAttribute(name,level=0,version=2,bonus=0) {
    const info=affixInfo(name,version);
    if(!info) { showDetail(affixName(name),[empty("missingEffect")]); return; }
    showDetail(affixName(name),[
        node("div",{class:"detail-lead"},affixIcon(name,version),node("div",{},node("strong",{},t("category-"+info.category)),
            node("p",{class:"intro"},effectText(info.description)))),
        bonus?node("p",{class:"bonus-note"},t("wineBonus",{count:bonus})):node("span"),
        node("ol",{class:"effect-steps"},...Array.from({length:info.cap},(_,i)=>
            node("li",{class:i===Math.min(level,info.cap)-1?"current":""},node("b",{},levelLabel(i+1)),effectText(info.effects[i])||"—")))
    ]);
}

function openAttributes(mode) {
    attributeMode=mode;
    $("attribute-search").value="";
    paintAttributeDialog();
    $("attributes-dialog").showModal();
    $("attribute-search").focus();
}

function paintAttributeDialog() {
    const browse=attributeMode===null, filter=attributeMode===FILTER;
    const version=filter ? current.version : 2;
    const query=$("attribute-search").value.trim().toLocaleLowerCase(language);
    $("attributes-title").textContent=t(filter?"filterEffects":browse?"allAffixes":"chooseTarget");
    const groups=new Map(affixOrder.map(key=>[key,[]]));
    const source=filter&&version===1?catalog.legacyAffixes : browse?{...catalog.legacyAffixes,...catalog.affixes}:catalog.affixes;
    const affixes=Object.values(source).sort((a,b)=>affixName(a.name).localeCompare(affixName(b.name),language));
    const finishFilter=name=>{ $("attributes-dialog").close(); selectEffectFilter(name); $("effect-open").focus(); };
    for(const info of affixes) {
        if (!browse && !filter && targets.has(info.name) && attributeMode!==info.name) continue;
        if (query && !(affixName(info.name)+" "+info.name).toLocaleLowerCase(language).includes(query)) continue;
        const choice=node("button",{type:"button",title:effectText(info.description),"data-category":info.category},
            affixIcon(info.name,version),node("span",{},affixName(info.name)));
        choice.onclick=()=>{
            if (browse) { showAttribute(info.name); return; }
            if (filter) { finishFilter(info.name); return; }
            const previous=attributeMode;
            if(previous && previous!==info.name) {
                targets=new Map([...targets].map(([key,level])=>key===previous?[info.name,Math.min(level,info.cap)]:[key,level]));
            } else if(!previous && targets.size<catalog.maxTargets) targets.set(info.name,1);
            goalChanged();
            $("attributes-dialog").close();
            paintTargets();
            $("target-add").focus();
        };
        (groups.get(info.category)??groups.get("utility")).push(choice);
    }
    const sections=[...groups].filter(([,items])=>items.length).map(([category,items])=>
        node("section",{},node("h3",{},t("category-"+category)),node("div",{class:"attribute-grid"},...items)));
    const quick=filter ? node("div",{class:"effect-options"},...["*","-"].map(name=>{
        const button=node("button",{type:"button","aria-pressed":effectFilter===name},t(name==="*"?"allEffects":"noInnate"));
        button.onclick=()=>finishFilter(name); return button;
    })) : null;
    $("attribute-choices").replaceChildren(...[quick,...(sections.length?sections:[empty("noMatches")])].filter(Boolean));
}

function paintTotals() {
    $("mode-goals").setAttribute("aria-pressed", right === "goals");
    $("mode-totals").setAttribute("aria-pressed", right === "totals");
    $("goals-panel").hidden = right !== "goals";
    $("totals-panel").hidden = right !== "totals";
    paintBuildTotals($("stat-list"),$("affix-list"));
}

function paintBuildTotals(stats,affixes) {
    stats.replaceChildren(...statPills(current.stats));
    affixes.replaceChildren(...attributeRows(current.attributes,wineBoosts,current.version));
}

function accept(build, {imported=false, id=undefined, boosts={}, resetBrand=false} = {}) {
    const refreshBrand=imported || resetBrand || current?.loadout.career!==build.loadout.career ||
        JSON.stringify(current?.brand??null)!==JSON.stringify(build.brand??null);
    current = build;
    if(refreshBrand) resetBrandDraft();
    careerId = build.loadout.career;
    if (id !== undefined) savedId = id;
    wineBoosts = boosts;
    delete $("code").dataset.dirty;
    if (imported) {
        socketIndex=0; gemQuery=""; effectFilter="*"; rarityFilter=0;
        targets = new Map(Object.entries(build.attributes).filter(([n]) => catalog.affixes[n])
            .sort((a,b) => b[1] - a[1]).slice(0,catalog.maxTargets).map(([n,l]) => [n,Math.min(catalog.affixes[n].cap,l)]));
        solverWeapon = build.items[build.loadout.activeWeapon]?.weapon ?? "";
        if (build.items[build.loadout.activeWeapon]?.grade >= 3) solverGrade = build.items[build.loadout.activeWeapon].grade;
        $("use-wine").checked=false;
        $("auto-brand").checked=false;
        $("second").checked = Boolean(build.items[10] && build.items[11]);
        right = "goals";
        activeSlot = build.loadout.activeWeapon;
    }
    paintHeader();
    if(view==="editor" && !busy) paintEditor();
    if (view === "preview") paintPreview();
}

function resetEditor(build) {
    savedId=undefined; targets.clear(); solverWeapon=""; solverGrade=6; activeSlot=10; page=0; right="goals"; lastAuto=false;
    $("gear-search").value=""; rarityFilter=0; effectFilter="*"; socketIndex=0; gemQuery="";
    $("use-wine").checked=false; $("second").checked=false; $("auto-brand").checked=false;
    message("solver-status"); message("code-status");
    accept(build,{resetBrand:true});
}

async function exclusive(output, call) {
    if (busy) return;
    busy = true;
    $("editor").inert = true;
    $("code-panel").inert = true;
    $("classes").inert=true;
    try { await call(); }
    catch (error) { message(output, error.message, "error"); }
    finally {
        busy = false;
        $("editor").inert = false;
        $("code-panel").inert = false;
        $("classes").inert=false;
        if (view==="editor") paintEditor();
    }
}

async function changeKit(change, weapon, active = current.loadout.activeWeapon) {
    const output=view==="preview" ? "preview-totals-status" : "code-status";
    await exclusive(output,async () => {
        const loadout = structuredClone(current.loadout);
        change(loadout.equipment);
        loadout.activeWeapon = active;
        if (weapon) solverWeapon = weapon;
        lastAuto = false;
        const build = await api("encode",{loadout,version:current.version,brand:current.brand});
        message(output);
        accept(build);
    });
}

async function optimize(sample = false, active = current?.loadout.activeWeapon) {
    if (!current || (!sample && !targets.size)) return;
    await exclusive("solver-status",async () => {
        const demo = current.loadout.career === 12;
        const career = current.loadout.career;
        const chosen = catalog.careers[career].weapons;
        const goal = sample ? {Valor:4,Aegis:4,Dominion:3} : Object.fromEntries(targets);
        const activeWeapon = sample ? 10 : active;
        message("solver-status","solving");
        const result = await api("optimize",{career,activeWeapon,
            weapon:sample ? (demo ? "Javelin" : chosen[0]) : solverWeapon,
            grade:sample ? 6 : solverGrade, wine:sample || !$("use-wine").checked ? 0 : Number($("wine").value),
            secondWeapon:sample || $("second").checked, targets:goal, brand:current.brand,
            autoBrand:!sample && $("auto-brand").checked});
        targets = new Map(Object.entries(result.targets));
        if (sample) {
            savedId = undefined;
            solverWeapon = result.build.items[10].weapon;
            solverGrade=6;
            $("use-wine").checked=false;
            $("second").checked = true;
            activeSlot = 10;
            $("gear-search").value = "";
            page = 0;
        }
        lastAuto = true;
        accept(result.build,{boosts:result.wine});
        message("solver-status",result.exact ? "found" : "closest",result.exact ? "success" : "");
        $("solver-status").append(" · " + t(result.affinity) + " · " + Math.round(result.milliseconds) + " ms");
    });
}

async function loadPreviews() {
    const revision=++libraryRevision, career=careerId;
    libraryBusy=true;
    previews=new Map();
    paintLibrary();
    try {
        const rows=await api("build-previews/"+career);
        if(revision===libraryRevision) previews=new Map(rows.map(row=>[row.id,row]));
    } catch(error) { if(revision===libraryRevision) message("app-status",error.message,"error"); }
    finally {
        if(revision===libraryRevision) {
            libraryBusy=false;
            if(view==="library" && career===careerId) paintLibrary();
        }
    }
}

function upsertSaved(result) {
    bank = bank.some(row=>row.id===result.id) ? bank.map(row=>row.id===result.id?result:row) : [...bank,result];
    paintHeader();
}

function tileGrid(items={},active=10,equipped={},version=2,named=false,brand=null) {
    return node("div",{class:named?"import-loadout":"card-equipment"},...withBrand(slots.map(slot=>{
        const item=items[slot], title=slotName(slot)+" · "+(item?itemName(item):t("none"));
        const image=gearArt(item,slot);
        const tile=node(item?"button":"div",{type:item?"button":null,
            class:(named?"import-piece":"card-slot")+(!named && slot===active&&item?" is-active":""),
            "aria-label":title,title},named?node("span",{class:"import-piece-icon"},image):image,
            named?node("span",{class:"import-piece-text"},node("small",{},slotName(slot)),node("strong",{},item?itemName(item):t("none"))):null);
        tile.style.setProperty("--rarity",item?rarityColors[item.grade]: "var(--line)");
        if(item) tile.onclick=()=>{
            const gems=equipped[slot]??[], contribution={};
            if(item.innate) contribution[item.innate]=1;
            for(const gem of gems) for(const name of gem?.affixes??[]) contribution[name]=(contribution[name]??0)+1;
            showDetail(itemName(item),[
                node("div",{class:"detail-lead"},node("span",{class:"detail-item-art"},gearArt(item,slot)),node("div",{},node("strong",{},slotName(slot)),
                    node("p",{class:"intro"},rarity(item.grade)))),
                node("div",{class:"stats"},...statPills(item.stats)),
                itemLore(item)?node("p",{class:"intro"},itemLore(item)):null,
                item.innate?node("p",{class:"gear-innate"},t("innate"),affixChip(item.innate,version)):null,
                node("div",{class:"detail-sockets"},...item.sockets.map((socket,index)=>node("div",{},
                    node("strong",{},socketLabel(socket)),gemLine(gems[index],version,t("emptySocket"))))),
                Object.keys(contribution).length?node("section",{},node("h3",{},t("itemContribution")),
                    ...attributeRows(contribution,{},version)):null
            ].filter(Boolean));
        };
        return tile;
    }),brandTile(brand,{compact:!named,named})));
}

function showSaved(row,summary) {
    const values=(row.activeWeapon===11 ? summary?.second : summary?.first)??{};
    const legacyCode=summary?.version && summary.version!==catalog.version;
    showDetail(row.name,[
        node("p",{class:"intro"},className(row.career)+" · "+slotName(row.activeWeapon)),
        node("div",{class:"detail-build"},tileGrid(summary?.items??{},row.activeWeapon,summary?.equippedGems,summary?.version,false,row.brand),
            node("div",{class:"attribute-list"},...attributeRows(values,{},summary?.version))),
        node("label",{class:"detail-code"},t("gearCode"),node("input",{value:row.code,readonly:true,"aria-label":t("gearCode")})),
        node("div",{class:"dialog-actions"},node("button",{type:"button",class:"detail-copy"},t(legacyCode?"upgradeCode":"copyCode")))
    ].filter(Boolean));
    $("detail-content").querySelector(".detail-copy").onclick=async event=>{
        if (legacyCode) { $("detail-dialog").close(); openUpgrade(row); return; }
        try { await navigator.clipboard.writeText(row.code); event.target.textContent=t("copied"); }
        catch { event.target.textContent=t("internal-error"); }
    };
}

function openUpgrade(row) {
    focusUpgrade=row.id;
    location.hash="build/"+row.id;
}

function paintLibrary() {
    const search=$("library-search");
    search.placeholder=t("classSearch",{name:className(careerId)});
    search.setAttribute("aria-label",search.placeholder);
    const query=search.value.trim().toLocaleLowerCase(language);
    const rows=bank.filter(row=>row.career===careerId && (!query || [
        row.name,row.code,...Object.keys(previews.get(row.id)?.first??{}).map(affixName),
        ...Object.keys(previews.get(row.id)?.second??{}).map(affixName)
    ].join(" ").toLocaleLowerCase(language).includes(query)));
    if (libraryBusy) { $("library-grid").replaceChildren(empty("loadingBuilds")); return; }
    $("library-grid").replaceChildren(...(rows.length ? rows.map(row => {
        const summary=previews.get(row.id);
        const values=(row.activeWeapon===11?summary?.second:summary?.first)??{};
        const open=action("✎","editBuild",()=>{location.hash="build/"+row.id;});
        const legacyCode=summary?.version && summary.version!==catalog.version;
        const copy=action("↗",legacyCode?"upgradeCode":"copyCode",()=>{
            if(legacyCode) openUpgrade(row);
            else if(summary?.items) copyText(row.code,"app-status");
        });
        copy.disabled=!summary?.items;
        const info=action("i","details",()=>showSaved(row,summary));
        const edit=action("✎","editMetadata",()=>{
            metadataRow=row;
            $("metadata-name").value=row.name; $("metadata-code").value=row.code;
            message("metadata-status"); $("metadata-dialog").showModal(); $("metadata-name").select();
        },"tiny-action");
        const remove=action("×","delete",async ()=>{
            if (!window.confirm(t("confirmDelete",{name:row.name}))) return;
            try {
                await api("builds/" + row.id,undefined,"DELETE");
                if (savedId===row.id) savedId=undefined;
                bank=bank.filter(x=>x.id!==row.id);
                paintHeader(); paintLibrary();
            } catch(error) { message("app-status",error.message,"error"); }
        },"danger");
        const setActive=async (slot,button)=>{
            if(slot===row.activeWeapon || button.parentNode.inert || !summary?.items) return;
            const switcher=button.parentNode;
            switcher.inert=true;
            try {
                const result=await api("builds",{...row,activeWeapon:slot});
                upsertSaved(result);
                if(savedId===row.id && current?.code===row.code) {
                    const draft=current;
                    const decoded=await api("decode",{code:row.code,activeWeapon:slot,brand:draft.brand});
                    if (current===draft && savedId===row.id) {
                        lastAuto=false;
                        accept(decoded,{imported:true,id:row.id});
                    }
                }
                if(view==="library") {
                    paintLibrary();
                    $("library-grid").querySelector('[data-build="'+row.id+'"] [aria-pressed="true"]')?.focus();
                }
            } catch(error) { message("app-status",error.message,"error"); }
            finally { switcher.inert=false; }
        };
        const attrs=summary?.items ? attributeRows(values,{},summary.version) : [node("p",{class:"message","data-kind":"error"},t(summary?.error??"internal-error"))];
        return node("article",{class:"saved-card","data-build":row.id},
            node("div",{class:"saved-title"},node("h3",{title:row.name},row.name),
                legacyCode?node("span",{class:"counter",title:t("legacyCodeNote")},"v"+summary.version):null,edit),
            node("div",{class:"saved-equipment"},
                node("p",{class:"card-meta"},t("activeCount",{count:Object.keys(values).length})),
                tileGrid(summary?.items??{},row.activeWeapon,summary?.equippedGems,summary?.version,false,row.brand)),
            node("section",{class:"card-attributes"},
                node("div",{class:"section-head compact-head"},node("h3",{},t("attributes")),
                    node("div",{class:"weapon-switch",role:"group","aria-label":t("active")},...weaponSwitch(row.activeWeapon,setActive))),
                node("div",{class:"attribute-list"},...attrs)),
            node("div",{class:"saved-actions"},info,open,copy,remove));
    }) : [empty(query ? "noMatches" : "noSaved")]));
}

function paintImport() {
    $("import-result").hidden=!importBuild;
    if(!importBuild) return;
    $("import-class").textContent=className(importBuild.loadout.career);
    $("import-gear").replaceChildren(tileGrid(importBuild.items,importWeapon,importBuild.equippedGems,importBuild.version,true,importBuild.brand));
    $("import-weapons").replaceChildren(...weaponSwitch(importWeapon,slot=>{
        if(slot===importWeapon || importBusy) return;
        importWeapon=slot;
        decodeImport();
    }));
    $("import-weapons").hidden=!(importBuild.items[10] && importBuild.items[11]);
    $("import-affixes").replaceChildren(...attributeRows(importBuild.attributes,{},importBuild.version));
    const valid=!importBusy;
    $("import-edit").disabled=$("import-save").disabled=!valid;
    $("legacy-import-note").hidden=importBuild.version===catalog.version;
    $("upgrade-import").disabled=!valid;
}

function showUpgrade(output,result) {
    const slots=result.changedSlots.map(slotName).join(", ");
    message(output,slots?"upgradedEffects":"upgradedCode",slots?"":"success",{version:result.build.version,slots});
}

async function upgradeImport() {
    if(!importBuild || importBusy || importBuild.version===catalog.version) return;
    const original=importBuild;
    importBusy=true;
    $("import-code").readOnly=true;
    paintImport();
    try {
        const result=await api("upgrade-code",{code:original.code,activeWeapon:importWeapon});
        $("import-code").value=result.build.code;
        importBuild=result.build;
        importWeapon=result.build.loadout.activeWeapon;
        showUpgrade("import-status",result);
    } catch(error) { message("import-status",error.message,"error"); }
    finally { importBusy=false; $("import-code").readOnly=false; paintImport(); }
}

async function decodeImport() {
    clearTimeout(importTimer);
    if(importBusy) return;
    const revision=++importRevision;
    const code=$("import-code").value.replace(/\s/g,"");
    if(importBuild?.code!==code) importBuild=undefined;
    message("import-status",code?"decoding":"importHint");
    paintImport();
    if(!code) return;
    try {
        const build=await api("decode",{code,activeWeapon:importWeapon});
        if(revision!==importRevision) return;
        if(!Object.keys(build.items).length) throw new Error("emptyLoadout");
        importBuild=build;
        importWeapon=build.loadout.activeWeapon;
        if (!$("import-name").value.trim() || $("import-name").value===autoImportName) {
            const parts=Object.entries(build.attributes).sort((a,b)=>b[1]-a[1]).slice(0,3);
            autoImportName=parts.map(([name,level])=>affixName(name)+" "+level).join(" + ")||className(build.loadout.career);
            $("import-name").value=autoImportName;
        }
        message("import-status","importReady","success",{name:className(build.loadout.career)});
    } catch(error) { if(revision===importRevision) message("import-status",error.message,"error"); }
    if(revision===importRevision) paintImport();
}

async function saveImport() {
    if(!importBuild || importBusy) return;
    const name=$("import-name");
    if(!name.value.trim()) { message("import-status","build-name","error"); name.focus(); return; }
    importBusy=true; $("import-code").readOnly=true; name.readOnly=true; paintImport();
    try {
        const result=await api("builds",{name:name.value,code:importBuild.code,activeWeapon:importWeapon});
        upsertSaved(result);
        message("import-status","savedOk","success");
    } catch(error) { message("import-status",error.message,"error"); }
    finally { importBusy=false; $("import-code").readOnly=false; name.readOnly=false; paintImport(); }
}

function paintPreview() {
    if (!current) return;
    $("preview-name").textContent = className(current.loadout.career);
    $("preview-gear").replaceChildren(...withBrand(slots.map(slot => {
        const item = selected(slot);
        return equipmentTile(slot,item,{
            "data-model-slot":slot,"data-active-gear":slot===current.loadout.activeWeapon?"true":null,
        },() => { if(!busy) { chooseSlot(slot); location.hash="editor"; } });
    }),brandTile(current.brand,{editId:"preview-brand"})));
    paintPreviewGear();
    paintActiveWeapon($("preview"));
    paintBuildTotals($("preview-stats"),$("preview-affixes"));
    setOptions($("model-target"),[["base",t("baseModel")+" · ID "+current.loadout.career],
        ...slots.filter(s => selected(s)).map(s => [s,slotName(s)+" · "+itemName(selected(s))+" · ID "+selected(s).id])],$("model-target").value);
    scene?.setLoadout(current);
}

function paintPreviewGear(states={}) {
    for(const button of $("preview-gear").children) {
        if (button.hasAttribute("data-brand-slot")) continue;
        const slot=Number(button.dataset.modelSlot), item=selected(slot), state=states[slot];
        const active=slot===current.loadout.activeWeapon;
        button.dataset.modelState=state??"";
        const gearLabel=[slotName(slot),item?itemName(item):t("none"),active?t("active"):null].filter(Boolean).join(" · ");
        button.setAttribute("aria-label",gearLabel);
        button.title=[gearLabel,item?"ID "+item.id:null,state?t("mesh-"+state):null,t("edit")].filter(Boolean).join(" · ");
    }
}

function reportModels(status) {
    const body=status.body;
    $("motion-option").hidden=!status.hasMotion;
    const states=Object.values(status.slots).filter(state=>state!=="inactive");
    const lacking=states.filter(state=>state==="missing" || state==="error").length;
    message("model-coverage",lacking && body==="ready" ? "modelIncomplete" : "", "", {count:lacking});
    message("preview-status",body==="ready" ? "" : body==="error" ? "modelError" : body==="loading" ? "loadingModel" : "bodyMissing",
        body==="error"?"error":"",{name:className(current.loadout.career)});
    paintPreviewGear(status.slots);
}

async function openScene() {
    if (!scenePromise) {
        message("preview-status","loadingScene");
        const entries=api("models").catch(()=>[]);
        scenePromise = import("./scene.js").then(async ({createPreview}) => {
            const preview=await createPreview($("viewport"),reportModels);
            const count=preview.assignLocalPack(await entries);
            if(count) message("model-status","packLoaded","success",{count});
            return preview;
        });
    }
    try {
        scene = await scenePromise;
        scene.setVisible(view === "preview");
        scene.setParticles($("particles").checked);
        scene.setMotion($("animate-model").checked);
        $("viewport").dataset.renderer = scene.backend;
        message("preview-status");
        scene.setLoadout(current);
    } catch {
        message("preview-status","noGpu","error");
    }
}

async function copyText(text, output, success="copied") {
    try { await navigator.clipboard.writeText(text); message(output,success,"success"); }
    catch { message(output,"internal-error","error"); }
}

function prepareSave(asCopy) {
    if (brandIsDirty()) {
        if(activeSlot!==BRAND_SLOT) chooseSlot(BRAND_SLOT);
        message("brand-status","brandPending","error");
        $("brand-apply").focus();
        return;
    }
    if ((!Object.keys(current.loadout.equipment).length && !current.brand) || $("code").dataset.dirty) {
        message("code-status",$("code").dataset.dirty ? "load" : "chooseItem","error");
        return;
    }
    const editing=bank.find(x=>x.id===savedId);
    saveAsCopy=asCopy;
    $("build-name").value=editing ? editing.name+(asCopy?" ("+t("copySuffix")+")":"") : className(current.loadout.career);
    $("save-submit").textContent=t(asCopy?"saveCopy":editing?"applyChanges":"saveAction");
    message("save-status"); $("save-dialog").showModal(); $("build-name").select();
}

async function save(copy) {
    const input = $("build-name");
    if (!input.reportValidity()) return;
    const buttons = [...$("save-form").querySelectorAll("button")];
    for (const b of buttons) b.disabled = true;
    try {
        const result = await api("builds",{id:copy ? null : savedId, name:input.value, code:current.code,activeWeapon:current.loadout.activeWeapon,brand:current.brand});
        savedId = result.id;
        upsertSaved(result);
        $("save-dialog").close();
        message("code-status","savedOk","success");
        paintEditor();
    } catch (error) { message("save-status",error.message,"error"); }
    finally { for (const b of buttons) b.disabled = false; }
}

function connect() {
    window.addEventListener("hashchange",()=>navigate().catch(error=>message("app-status",error.message,"error")));
    document.querySelector(".skip-link").onclick=event=>{event.preventDefault(); $("main").focus();};
    window.addEventListener("resize",paintScale);
    $("ui-scale").disabled=false;
    $("ui-scale").onchange=()=>chooseScale(Number($("ui-scale").value));
    window.addEventListener("keydown",event=>{
        if(!event.ctrlKey || event.altKey || event.metaKey) return;
        if(event.key==="0") { event.preventDefault(); chooseScale(0); return; }
        const step=event.key==="+"||event.key==="=" ? 1 : event.key==="-" ? -1 : 0;
        if(!step) return;
        event.preventDefault();
        const currentScale=uiScale || autoScale();
        chooseScale(scales[Math.max(0,Math.min(scales.length-1,scales.indexOf(currentScale)+step))]);
    });
    document.querySelectorAll("[data-lang]").forEach(button => button.onclick = async () => {
        setLanguage(button.dataset.lang);
        translate();
        try { await api("language",{value:language}); }
        catch(error) { message("app-status",error.message,"error"); }
    });
    $("sample").onclick = () => optimize(true);
    $("brand-remove").onclick=()=>selectBrand(-1);
    $("brand-cancel").onclick=()=>{
        resetBrandDraft();
        paintBrandCatalog();
        const selectedCard="brand-rarity-"+brandDraft?.rarity;
        paintBrandForm($(selectedCard)?selectedCard:"edit-brand");
    };
    $("brand-form").onsubmit=event=>{
        event.preventDefault();
        if(busy || activeSlot!==BRAND_SLOT || !brandIsDirty()) return;
        const draft=draftBrand();
        if(draft?.effects.some(e=>e.kind==="gem"?!e.type:!e.id)) { message("brand-status","brandIncomplete","error"); return; }
        if(draft?.effects.some(e=>{
            if(e.kind!=="stat") return false;
            const attr=brandData.attrs.find(a=>a.id===e.id), [min,,max]=attr.v[draft.rarity];
            const steps=e.value*(attr.pct?10:1);
            return !Number.isFinite(steps) || e.value<min || e.value>max || Math.abs(steps-Math.round(steps))>1e-6;
        })) { message("brand-status","brandInvalidValue","error"); return; }
        if($("code").dataset.dirty) { message("brand-status","loadBeforeCopy","error"); return; }
        const original=current;
        const previousSlot=brandSlot;
        let applied=false;
        exclusive("brand-status",async()=>{
            const result=await api("encode",{loadout:original.loadout,version:original.version,brand:draft});
            if(current!==original) return;
            lastAuto=false;
            $("auto-brand").checked=false;
            accept(result,{resetBrand:true});
            brandSlot=previousSlot;
            applied=true;
        }).then(()=>{
            if(applied && view==="editor" && activeSlot===BRAND_SLOT)
                ($("brand-slot-"+brandSlot) ?? $("edit-brand")).focus({preventScroll:true});
        });
    };
    $("reset").onclick = () => exclusive("code-status",async () => {
        const build = await api("encode",{loadout:{career:current.loadout.career,equipment:{},activeWeapon:10}});
        const editing=savedId;
        resetEditor(build);
        savedId=editing;
    });
    for (const button of document.querySelectorAll("[data-active]"))
        button.onclick = () => {
            const slot=Number(button.dataset.active);
            if (slot===current.loadout.activeWeapon) return;
            if(view!=="preview" && lastAuto && targets.size) optimize(false,slot);
            else changeKit(() => {},selected(slot)?.weapon,slot);
        };
    $("mode-goals").onclick = () => { right="goals"; paintTotals(); };
    $("mode-totals").onclick = () => { right="totals"; paintTotals(); };
    $("gear-search").addEventListener("input",() => {
        page=0; $("item-grid").scrollTop=0; paintItems();
    });
    $("effect-open").onclick=()=>openAttributes(FILTER);
    $("effect-clear").onclick=()=>{selectEffectFilter("*"); $("effect-open").focus();};
    $("target-add").onclick = () => { if(targets.size<catalog.maxTargets) openAttributes(""); };
    $("all-affixes").onclick = () => openAttributes(null);
    $("attribute-search").oninput = paintAttributeDialog;
    $("solve").onclick = () => optimize();
    $("weapon").onchange = () => { solverWeapon=$("weapon").value; if(lastAuto) optimize(); else paintEditor(); };
    for (const id of ["use-wine","wine","second"]) $(id).onchange = () => {
        $("wine").disabled=!$("use-wine").checked;
        if(lastAuto) optimize();
        else { wineBoosts={}; paintTotals(); }
    };
    $("code").oninput = () => { $("code").dataset.dirty="1"; };
    $("code-form").onsubmit = event => {
        event.preventDefault();
        const code=$("code").value;
        exclusive("code-status",async () => {
            const build = await api("decode",{code,activeWeapon:current.loadout.activeWeapon});
            savedId=undefined; lastAuto=false;
            accept(build,{imported:true});
            message("code-status","codeLoaded","success");
        });
    };
    $("copy-code").onclick = () => {
        if ($("code").dataset.dirty) { message("code-status","loadBeforeCopy","error"); return; }
        if (current.version===catalog.version && Object.keys(current.loadout.equipment).length)
            copyText(current.code,"code-status","copiedForGame");
    };
    $("upgrade-code").onclick=()=>exclusive("code-status",async()=>{
        if($("code").dataset.dirty) { message("code-status","loadBeforeCopy","error"); return; }
        const original=current;
        const result=await api("upgrade-code",{code:original.code,activeWeapon:original.loadout.activeWeapon,brand:original.brand});
        if(current!==original) return;
        lastAuto=false;
        accept(result.build,{imported:true});
        showUpgrade("code-status",result);
    });
    $("upgrade-import").onclick=upgradeImport;
    $("move-weapon").onclick=()=>{
        if(selected(10) || !selected(11)) return;
        const weapon=selected(11).weapon;
        chooseSlot(10);
        changeKit(equipment=>{ equipment[10]=equipment[11]; delete equipment[11]; },weapon,10);
    };
    $("save-build").onclick = () => prepareSave(false);
    $("edit-copy").onclick=()=>prepareSave(true);
    $("edit-discard").onclick=()=>{
        const original=bank.find(row=>row.id===savedId);
        if(!original || busy) return;
        if((original.code!==current.code || original.activeWeapon!==current.loadout.activeWeapon ||
            JSON.stringify(original.brand??null)!==JSON.stringify(current.brand??null) || brandIsDirty() || $("code").dataset.dirty)
            && !window.confirm(t("discardConfirm"))) return;
        exclusive("code-status",async()=>{
            const build=await api("encode",{loadout:{career:original.career,equipment:{},activeWeapon:10}});
            resetEditor(build);
            location.hash="library";
        });
    };
    $("save-form").onsubmit = event => { event.preventDefault(); save(saveAsCopy); };
    $("save-cancel").onclick = () => $("save-dialog").close();
    $("library-search").oninput = paintLibrary;
    $("import-code").oninput = () => {
        ++importRevision; importBuild=undefined;
        importWeapon=0;
        clearTimeout(importTimer);
        if (!$("import-code").value.trim()) { decodeImport(); return; }
        message("import-status","decoding"); paintImport();
        importTimer=setTimeout(decodeImport,180);
    };
    $("import-form").onsubmit = event => { event.preventDefault(); decodeImport(); };
    $("import-save").onclick=saveImport;
    $("import-name").onkeydown=event=>{if(event.key==="Enter" && !$("import-save").disabled) saveImport();};
    $("import-edit").onclick=()=>{
        if(!importBuild || importBusy) return;
        savedId=undefined; lastAuto=false;
        accept(importBuild,{imported:true});
        location.hash="editor";
    };
    $("metadata-cancel").onclick=()=>$("metadata-dialog").close();
    $("metadata-form").onsubmit=async event=>{
        event.preventDefault();
        const row=metadataRow, form=$("metadata-form");
        if(!row || form.inert) return;
        form.inert=true;
        try {
            const result=await api("builds",{id:row.id,name:$("metadata-name").value,code:$("metadata-code").value,activeWeapon:row.activeWeapon,brand:row.brand});
            upsertSaved(result);
            if(result.code!==row.code && savedId===row.id) savedId=undefined;
            $("metadata-dialog").close();
            if(view==="library") await loadPreviews();
        } catch(error) { message("metadata-status",error.message,"error"); }
        finally { form.inert=false; }
    };
    if(window.chrome?.webview) {
        $("data-folder").hidden=false;
        $("data-folder").onclick=()=>window.chrome.webview.postMessage("open-data-folder");
    }
    $("camera-reset").onclick = () => scene?.resetCamera();
    $("particles").onchange = () => scene?.setParticles($("particles").checked);
    $("animate-model").checked = !matchMedia("(prefers-reduced-motion: reduce)").matches;
    $("animate-model").onchange = () => scene?.setMotion($("animate-model").checked);
    $("model-pack").onchange = async () => {
        const input=$("model-pack");
        if(scene && input.files.length) {
            try {
                const count=await scene.assignPack(input.files);
                if(count) message("model-status","packLoaded","success",{count});
            } catch { message("model-status","packError","error"); }
        }
        input.value="";
    };
    $("model-file").onchange = async () => {
        const [file] = $("model-file").files;
        if (!scene || !file) return;
        const selectedTarget=$("model-target").value;
        const target=selectedTarget==="base" ? "base:"+current.loadout.career : selectedTarget + ":" + selected(Number(selectedTarget))?.id;
        $("model-file").disabled=true;
        try { if(await scene.assignModel(target,file)) message("model-status","modelLoaded","success"); }
        catch { message("model-status","modelError","error"); }
        finally { $("model-file").value=""; $("model-file").disabled=false; }
    };
    $("reset-models").onclick = () => { scene?.clearModels(); message("model-status"); };
    async function reloadCatalog(iconCount) {
        catalog = await api("catalog");
        slotCache.clear(); gemCache.clear();
        if(current) {
            const currentBuild = await api("encode",{loadout:current.loadout,version:current.version,brand:current.brand});
            targets = new Map([...targets].filter(([name]) => catalog.affixes[name])
                .map(([name,level])=>[name,Math.min(level,catalog.affixes[name].cap)]));
            accept(currentBuild);
        }
        if(view==="library") await loadPreviews();
        if(view==="import") await decodeImport();
        if(view==="classes") paintClasses();
        paintHeader();
        message("app-status",iconCount===undefined?"catalogOk":"catalogWithIcons","success",{count:iconCount});
    }
    $("refresh-catalog").onclick=()=>exclusive("app-status",async()=>{
        $("refresh-catalog").disabled=true;
        message("app-status","catalogDownloading");
        try { const result=await api("catalog/refresh",{}); await reloadCatalog(result.newIcons); }
        finally { $("refresh-catalog").disabled=false; }
    });
    $("catalog-file").onchange=()=>{
        const [file]=$("catalog-file").files;
        $("catalog-file").value="";
        if(file) exclusive("app-status",async()=>{ await api("catalog",file); await reloadCatalog(); });
    };
    $("catalog-pack").onchange=()=>{
        const files=[...$("catalog-pack").files];
        $("catalog-pack").value="";
        if(!files.length) return;
        exclusive("app-status",async()=>{
            const catalogs=files.filter(file=>/^[^/]+\/[^/]+\.json$/i.test(file.webkitRelativePath));
            const file=catalogs.find(x=>x.name==="mistfall_season2.json")??(catalogs.length===1?catalogs[0]:null);
            if(!file || file.size>4*1024*1024) throw new Error("catalogPackMissing");
            let data;
            try { data=JSON.parse(await file.text()); } catch { throw new Error("invalid-catalog"); }
            if(!data || typeof data!=="object") throw new Error("invalid-catalog");
            const names=new Set([...Object.values(data.objets??{}).flat(),...(Array.isArray(data.gemmes)?data.gemmes:[]),
                ...Object.values(data.affixes??{})].map(x=>String(x?.ic??"").toLowerCase()).filter(Boolean));
            const form=new FormData();
            form.append("catalog",file);
            let bytes=file.size, count=0;
            for(const image of files) {
                const name=image.name.toLowerCase();
                if(!/^[^/]+\/icons\/[^]+\.(png|webp)$/i.test(image.webkitRelativePath)||image.size>1024*1024||
                    (!names.has(name)&&!names.has(name.replace(/\.(png|webp)$/,"")))) continue;
                if(++count>320 || (bytes+=image.size)>38*1024*1024) throw new Error("invalid-catalog");
                form.append("icon",image,image.name);
            }
            const result=await api("catalog/pack",form);
            await reloadCatalog(result.newIcons);
        });
    };
}

try {
    const response = await Promise.all([api("catalog"),api("language"),api("builds"),api("ui-scale"),api("soul-brands")]);
    catalog=response[0]; setLanguage(response[1].value); bank=response[2];
    uiScale=response[3].value;
    brandData=response[4];
    connect();
    translate();
    await navigate();
    document.documentElement.dataset.ready="1";
} catch(error) {
    message("app-status",error.message,"error");
}
