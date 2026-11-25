import { strict as assert } from "node:assert";
import { readFileSync } from "node:fs";
import { setLanguage, term, effectText, catalogItemName, catalogItemLore, catalogGemName, talentName, talentDescription } from "../wwwroot/locale.js";
import { talents as translatedTalents } from "../wwwroot/catalog-strings.js";

const read=path=>JSON.parse(readFileSync(new URL(path,import.meta.url),"utf8"));
const catalogs=[read("../../mistfall_data.json"),read("../../mistfall_season2.json")];
const talents=Object.values(read("../data/soulbrands.json").talents).flat();
const items=new Map(catalogs.flatMap(c=>Object.values(c.objets).flat()).map(item=>[item.n,item]));
const gemNames=new Set(catalogs.flatMap(c=>c.gemmes.map(g=>g.n)));
const affixLabels=new Set(catalogs.flatMap(c=>Object.keys(c.affixes)));
const phrases=new Set(catalogs.flatMap(c=>Object.values(c.affixes).flatMap(a=>[a.desc,...a.eff])).filter(Boolean));
for(const lang of ["ru","es"]){
    setLanguage(lang);
    for(const [name,item] of items){
        assert.ok(catalogItemName(name),lang+": item "+name);
        if(item.d) assert.ok(catalogItemLore(item.d),lang+": lore "+name);
    }
    for(const name of gemNames) assert.ok(catalogGemName(name),lang+": gem "+name);
    for(const label of affixLabels) assert.ok(term("affix",label,null),lang+": affix "+label);
    for(const phrase of phrases) assert.notEqual(effectText(phrase),phrase,lang+": effect "+phrase);
    for(const talent of talents){
        assert.ok(translatedTalents[talent.id]?.every(Boolean),lang+": talent "+talent.name);
        assert.ok(talentName(talent) && talentDescription(talent),lang+": rendered "+talent.name);
    }
}
setLanguage("en");
assert.equal(talentName(talents[0]),talents[0].name);
console.log({translatedItemNames:items.size,translatedGemNames:gemNames.size,localizedAffixLabels:affixLabels.size,
    translatedAffixPhrases:phrases.size,translatedTalents:talents.length});
