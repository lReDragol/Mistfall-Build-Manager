// Build the compact Forge localization from unpacked game data, not from live game files.
// Usage: node desktop/scripts/catalog-locales.mjs PATH_TO_EXPORTED_CONFIG_TABLES
import {readFileSync,writeFileSync} from "node:fs";
import {resolve} from "node:path";

if(!process.argv[2]) throw new Error("Pass the directory containing the exported I18NText.json and item tables.");
const read=file=>JSON.parse(readFileSync(file,"utf8"));
const game=name=>read(resolve(process.argv[2],name+".json"));
const legacy=read("mistfall_data.json"), season=read("mistfall_season2.json");
const brands=read("desktop/data/soulbrands.json");
const actionNames={
    Major_Action:["основная атака","ataque principal"],
    Minor_Action:["дополнительная атака","ataque secundario"],
    Fn:["способность класса","habilidad de clase"]
};
const clean=(x,lang)=>String(x??"")
    .replace(/<action\s+name="([^"]+)"\s*\/>/gi,(_,name)=>" ["+(actionNames[name]?.[lang]??name)+"]")
    .replace(/<br\s*\/?>/gi,"\n").replace(/<[^>\n]*>/g,"").replace(/[ \t]{2,}/g," ").trim();
const normalize=x=>clean(x).toLowerCase().replace(/\s+/g," ").replace(/’/g,"'").replace(/\s+%/g,"%").replace(/[.]+$/,"");
const all=game("I18NText");
const text=new Map(all.map(row=>[row.id,row]));
const byEnglish=new Map();
for(const row of all) if(row.english){
    const key=normalize(row.english);
    if(!byEnglish.has(key)) byEnglish.set(key,row);
}
const local=row=>row?[clean(row.russian,0),clean(row.spanish,1)]:["",""];
const extra=new Map(Object.entries({
    "Increase Physical Resistance.":["Повышает физическое сопротивление.","Aumenta la resistencia física."],
    "Increase Magic Resistance.":["Повышает магическое сопротивление.","Aumenta la resistencia mágica."],
    "Increase Critical Damage.":["Повышает критический урон.","Aumenta el daño crítico."],
    "Increase Defense Penetration.":["Повышает пробивание защиты.","Aumenta la penetración de defensa."],
    "Increase Melee Weapon Damage. Upon reaching a certain level, increases Melee Weapon Damage for each nearby enemy, up to 3 stacks.":
        ["Повышает урон оружия ближнего боя. С определённого уровня урон дополнительно растёт за каждого врага поблизости, до 3 зарядов.",
         "Aumenta el daño de las armas cuerpo a cuerpo. A cierto nivel, lo aumenta por cada enemigo cercano, hasta 3 acumulaciones."],
    "Reduce Skill Energy Cost.":["Снижает расход энергии на умения.","Reduce el coste de energía de las habilidades."],
    "Reduce the Block Energy Cost.":["Снижает расход энергии при блокировании.","Reduce el coste de energía al bloquear."],
    "Increase Energy Recovery Speed.":["Повышает скорость восстановления энергии.","Aumenta la velocidad de recuperación de energía."],
    "Casting skills in the air increases Physical Damage and Magic Damage. Upon reaching a certain level, aerial casting also reduces Skill Energy Cost.":
        ["Применение умений в воздухе повышает физический и магический урон. С определённого уровня также снижается расход энергии на такие умения.",
         "Lanzar habilidades en el aire aumenta el daño físico y mágico. A cierto nivel, también reduce el coste de energía de las habilidades aéreas."],
    "Headshot Damage +15%.":["Урон при попадании в голову +15%.","Daño por disparo a la cabeza +15 %."],
    "Recover Health equal to 9% of Maximum Health. Attack +6%.":["Восстановление 9% максимального здоровья. Атака +6%.","Recupera un 9 % de la salud máxima. Ataque +6 %."]
}));
for(const n of [8,9.6,11.2]) extra.set(
    `Physical Resistance +${n}%. Magic Resistance +${n}%. Resists minor impacts beyond 5 m.`,
    [`Физическое и магическое сопротивление +${String(n).replace(".",",")}%. Защита от слабых ударов с расстояния более 5 м.`,
     `Resistencia física y mágica +${String(n).replace(".",",")} %. Resiste impactos menores a más de 5 m.`]);
for(const n of [8,10]) extra.set(`Recover Energy by ${n}. Reduces Cooldown by 1s.`,
    [`Восстанавливает ${n} энергии. Снижает время перезарядки на 1 с.`,`Recupera ${n} de energía. Reduce la recarga en 1 s.`]);
for(const n of [6,7.2,8.4]) extra.set(`Physical Damage +${n}%. Magic Damage +${n}%. +2% per stack.`,
    [`Физический и магический урон +${String(n).replace(".",",")}%. По +2% за заряд.`,
     `Daño físico y mágico +${String(n).replace(".",",")} %. +2 % por acumulación.`]);
for(const n of [3,6,9,12]) extra.set(`Charging Speed +${n}%.`,
    [`Скорость заряда +${n}%.`,`Velocidad de carga +${n} %.`]);
const put=(map,key,value)=>{if(value.some(Boolean)) map[key]=value;};
const escaped=s=>s.replace(/[.*+?^${}()|[\]\\]/g,"\\$&");
const templates=[];
for(const skill of game("AffixSkill")){
    for(const id of [skill.desId,...skill.levelDes]) {
        const row=text.get(id);
        if(!row?.english?.includes("{")) continue;
        const parts=normalize(row.english).split(/(\{[^}]+\})/);
        const keys=[];
        const source=parts.map((part,i)=>{
            if(i%2===0) return escaped(part);
            keys.push(part.toLowerCase());
            return "(\\?|[-+]?\\d+(?:[.,]\\d+)?)";
        }).join("");
        templates.push({re:new RegExp("^"+source+"$"),row,keys});
    }
}
function translatePhrase(english,nativeRows=[]){
    if(!english) return ["",""];
    if(extra.has(english)) return extra.get(english);
    const key=normalize(english);
    const literal=nativeRows.find(row=>normalize(row?.english)===key)??byEnglish.get(key);
    if(literal) return local(literal);
    for(const {re,row,keys} of templates){
        const match=re.exec(key);
        if(!match) continue;
        const values=Object.fromEntries(keys.map((p,i)=>[p,match[i+1].replace(".",",")]));
        return local(row).map(s=>{
            const translated=s.replace(/\{[^}]+\}/g,key=>values[key.toLowerCase()]??key);
            return translated.includes("{")?"":translated;
        });
    }
    return ["",""];
}
const names={}, lore={}, gems={}, affixes={}, effects={}, talents={};
const remaining={items:new Set(),lore:new Set(),affixes:new Set(),effects:new Set(),talents:new Set(),gems:new Set()};
const items=new Map([...game("ItemArmor"),...game("ItemWeapon")].map(row=>[+row.id,row]));
const gemItems=new Map(game("ItemAffixGem").map(row=>[+row.id,row]));
const talentItems=new Map(game("Talent").map(row=>[+row.id,row]));
const add=(dict,key,langs,kind)=>{
    if (langs.every(Boolean)) remaining[kind].delete(key);
    else if(!dict[key]?.every(Boolean)) remaining[kind].add(key);
    put(dict,key,langs);
};
for(const db of [legacy,season]){
    for(const item of Object.values(db.objets).flat()){
        const row=items.get(+item.id), name=text.get(row?.nameId), desc=text.get(row?.descId);
        if(!names[item.n]?.every(Boolean)){
            const exact=byEnglish.get(normalize(item.n));
            add(names,item.n,local(exact??name),"items");
        }
        if(item.d && !lore[item.d]?.every(Boolean)){
            const translation=translatePhrase(item.d,[desc]);
            add(lore,item.d,translation.some(Boolean)?translation:local(desc),"lore");
        }
    }
    for(const gem of db.gemmes){
        const row=gemItems.get(+gem.id);
        add(gems,gem.n,local(text.get(row?.nameId)),"gems");
    }
    for(const {desc,eff} of Object.values(db.affixes)){
        if(desc&&!affixes[desc]?.every(Boolean)) add(affixes,desc,translatePhrase(desc),"affixes");
        for(const phrase of eff) if(phrase&&!effects[phrase]?.every(Boolean)) add(effects,phrase,translatePhrase(phrase),"effects");
    }
}
for(const talent of Object.values(brands.talents).flat()){
    const row=talentItems.get(talent.id);
    const [ru,es]=local(text.get(row?.nameId)??byEnglish.get(normalize(talent.name)));
    const desc=row?.gamepadDescId&&normalize(text.get(row.gamepadDescId)?.english)===normalize(talent.desc)
        ? text.get(row.gamepadDescId) : text.get(row?.descId);
    const description=translatePhrase(talent.desc,[desc]);
    const [ruDesc,esDesc]=description.some(Boolean)?description:local(desc);
    if([ru,es,ruDesc,esDesc].some(v=>!v)) remaining.talents.add(talent.id+" "+talent.name+" | "+talent.desc);
    talents[talent.id]=[ru,es,ruDesc,esDesc];
}
const format=dict=>"{\n"+Object.entries(dict).sort((a,b)=>a[0].localeCompare(b[0],"en")).map(([k,v])=>
    "  "+JSON.stringify(k)+": "+JSON.stringify(v)).join(",\n")+"\n}";
let result="// Selected labels, lore and effects used by the bundled Forge catalogs.\n";
for(const [key,dict] of Object.entries({names,lore,gems,affixes,effects,talents}))
    result+="export const "+key+" = "+format(dict)+";\n";
writeFileSync("desktop/wwwroot/catalog-strings.js",result);
for(const [key,values] of Object.entries(remaining))
    console.log(key,values.size,JSON.stringify([...values]));
