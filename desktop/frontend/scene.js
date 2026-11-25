import * as T from "three/webgpu";
import { color, positionLocal, smoothstep, float } from "three/tsl";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { createMotionController } from "./preview-motion.js";

const motion = matchMedia("(prefers-reduced-motion: reduce)");
function material(color, metalness = .5, roughness = .43) {
    return new T.MeshStandardMaterial({ color, metalness, roughness });
}
const steel = material(0x566d76,.68);
const gold = material(0xe6bd81,.69,.33);

function add(parent, geometry, surface, x, y, z, sx=1, sy=1, sz=1) {
    const part = new T.Mesh(geometry, surface);
    part.position.set(x,y,z);
    part.scale.set(sx,sy,sz);
    parent.add(part);
    return part;
}
const box = (p,m,x,y,z,a,b,c) => add(p,new T.BoxGeometry(a,b,c),m,x,y,z);
function rod(p,m,from,to,r1,r2=r1,sides=8) {
    const a=new T.Vector3(...from), b=new T.Vector3(...to), mid=a.clone().add(b).multiplyScalar(.5);
    const mesh=add(p,new T.CylinderGeometry(r2,r1,a.distanceTo(b),sides),m,mid.x,mid.y,mid.z);
    mesh.quaternion.setFromUnitVectors(new T.Vector3(0,1,0),b.sub(a).normalize());
    return mesh;
}
function bands(p,m,x,y,z,r,width) {
    const ring=add(p,new T.TorusGeometry(r,width,6,18),m,x,y,z);
    ring.rotation.x=Math.PI/2;
    return ring;
}

function disposeGroup(root, disposeTextures=false) {
    const skeletons=new Set();
    root.traverse(part => {
        if(part.skeleton) skeletons.add(part.skeleton);
        part.geometry?.dispose();
        if(!part.material) return;
        for(const surface of Array.isArray(part.material)?part.material:[part.material]) {
            if(disposeTextures) for (const value of Object.values(surface))
                if (value?.isTexture) value.dispose();
            surface.dispose();
        }
    });
    for(const skeleton of skeletons) skeleton.dispose();
    root.removeFromParent();
}

export async function createPreview(host, report) {
    const renderer = new T.WebGPURenderer({antialias:true,alpha:true,
        forceWebGL:new URLSearchParams(location.search).get("renderer")==="webgl"});
    try { await renderer.init(); }
    catch(error) { renderer.dispose(); throw error; }
    renderer.setPixelRatio(Math.min(devicePixelRatio || 1,2));
    renderer.toneMapping=T.ACESFilmicToneMapping;
    renderer.toneMappingExposure=1;
    renderer.setClearColor(0x0e1c23,0);
    host.append(renderer.domElement);
    const scene=new T.Scene();
    const camera = new T.PerspectiveCamera(35,1,.05,35);
    const orbit=new OrbitControls(camera,renderer.domElement);
    orbit.enablePan=false;
    orbit.minDistance=2.6;
    orbit.maxDistance=6.4;
    orbit.minPolarAngle=.59;
    orbit.maxPolarAngle=Math.PI*.54;
    orbit.enableDamping=true;
    orbit.dampingFactor=.14;
    // A side key and restrained fill keep the relief visible on pale fabric.
    scene.add(new T.HemisphereLight(0xf3eee5,0x5c514b,.98));
    for(const [color,intensity,xyz] of [[0xfff3e3,2.55,[2.8,3.7,2.6]],[0xd3e0f3,.75,[-3,2.8,1.2]],[0xb8d4d3,1.65,[0,3,-3]]]) {
        const light=new T.DirectionalLight(color,intensity);
        light.position.set(...xyz); scene.add(light);
    }
    const altar=new T.Group();
    const stone=material(0x243744,.3,.6);
    rod(altar,stone,[0,-.19,0],[0,-.03,0],.91,.84,12);
    rod(altar,steel,[0,-.06,0],[0,-.033,0],.86,.86,12);
    bands(altar,gold,0,-.024,0,.77,.009);
    bands(altar,steel,0,-.024,0,.67,.005);
    for(let j=0;j<12;j++) {
        const a=j*Math.PI/6;
        const tile=box(altar,j%3===0?gold:steel,Math.cos(a)*.75,-.009,Math.sin(a)*.75,.040,.012,.098);
        tile.rotation.y=-a+Math.PI/2;
    }
    scene.add(altar);
    const platform=new T.GridHelper(16,32,0x525345,0x42423a);
    platform.position.y=-.19;
    platform.material.transparent=true;
    platform.material.opacity=.16;
    scene.add(platform);
    const halo=new T.MeshBasicNodeMaterial({transparent:true,depthWrite:false});
    halo.colorNode=color(0x796747);
    halo.opacityNode=float(1).sub(smoothstep(float(.55),float(2.85),positionLocal.xy.length())).mul(.13);
    const haze=add(scene,new T.PlaneGeometry(6,6),halo,0,-.18,0);
    haze.rotation.x=-Math.PI/2;

    const spark=new T.OctahedronGeometry(.009);
    const sparkMat=new T.MeshBasicMaterial({color:0xfad291,transparent:true,opacity:.6});
    const drift=Array.from({length:46},(_,i) => ({a:i*2.39996,r:.53+(i%13)*.074,h:((i*37)%101)/39,
        sx:.5+(i%8)*.15,sy:.7+(i%7)*.28}));
    const particles=new T.InstancedMesh(spark,sparkMat,drift.length);
    particles.frustumCulled=false;
    particles.instanceMatrix.setUsage(T.DynamicDrawUsage);
    const pose=new T.Object3D();
    scene.add(particles);

    const animator=createMotionController();
    let visible=false, enabledParticles=true, enabledMotion=!motion.matches, loop=false, dirty=true, previousBuild=null;
    const displayed=new Set();
    const manual=new Map();
    let files=new Map(), cache=new Map();
    let manualGeneration=0, packGeneration=0;
    const manager=new T.LoadingManager();
    manager.setURLModifier(url=>{
        if(!/^(blob:|data:)/.test(url)) throw new Error("Embedded GLB resources required");
        return url;
    });
    const loader=new GLTFLoader(manager);
    const anisotropy=Math.min(8,renderer.getMaxAnisotropy() || 1);
    function updateSize() {
        const width=host.clientWidth, height=host.clientHeight;
        if(width<1 || height<1) return;
        renderer.setSize(width,height,false);
        camera.aspect=width/height;
        camera.updateProjectionMatrix();
        dirty=true;
    }
    const observer=new ResizeObserver(updateSize);
    observer.observe(host);
    function resetCamera() {
        orbit.target.set(0,.97,0);
        camera.position.set(.88,1.48,3.77);
        orbit.update();
        dirty=true;
    }
    orbit.addEventListener("change",()=>{ dirty=true; });
    function frame(time) {
        if(!visible || document.hidden) { animator.resetClock(); return; }
        if(orbit.update()) dirty=true;
        if(animator.step(time,enabledMotion)) dirty=true;
        particles.visible=enabledParticles;
        if(enabledParticles && (dirty || !motion.matches)) {
            const t=motion.matches?1.4:time*.00023;
            drift.forEach((part,i) => {
                pose.position.set(Math.cos(part.a+t)*part.r,(part.h+t*.46)%2.73,Math.sin(part.a+t)*part.r);
                pose.rotation.y=part.a+t;
                pose.scale.set(part.sx,part.sy,.7);
                pose.updateMatrix();
                particles.setMatrixAt(i,pose.matrix);
            });
            particles.instanceMatrix.needsUpdate=true;
            if(!motion.matches) dirty=true;
        }
        if(dirty) { dirty=false; renderer.render(scene,camera); }
    }
    function setVisible(next) {
        if(visible!==next) animator.resetClock();
        visible=next;
        if(visible && !loop) { loop=true; updateSize(); renderer.setAnimationLoop(frame); }
        if(!visible && loop) { loop=false; renderer.setAnimationLoop(null); }
    }
    async function loadGlb(file) {
        if(file.size<12 || file.size>80*1024*1024 || !/\.glb$/i.test(file.name))
            throw new Error("Invalid GLB");
        const bytes=await file.arrayBuffer();
        const header=new DataView(bytes);
        if(header.getUint32(0,true)!==0x46546c67 || header.getUint32(4,true)!==2 ||
            header.getUint32(8,true)!==bytes.byteLength) throw new Error("Invalid GLB header");
        const {scene:root}=await loader.parseAsync(bytes,"");
        let mesh=false;
        root.traverse(part=>{
            if(!part.isMesh) return;
            mesh=true;
            for(const surface of Array.isArray(part.material)?part.material:[part.material]) {
                for(const map of [surface?.map,surface?.normalMap,surface?.roughnessMap,surface?.metalnessMap,surface?.aoMap]) {
                    if(map?.generateMipmaps && map.magFilter===T.LinearFilter && map.minFilter===T.LinearMipmapLinearFilter)
                        map.anisotropy=anisotropy;
                }
            }
        });
        if(!mesh) { disposeGroup(root,true); throw new Error("GLB contains no mesh"); }
        return root;
    }
    function packed(key) {
        if(!files.has(key)) return {state:"missing"};
        if(cache.has(key)) return cache.get(key);
        const currentCache=cache;
        const entry={state:"loading"};
        cache.set(key,entry);
        loadGlb(files.get(key)).then(model=>{
            if(currentCache!==cache || cache.get(key)!==entry) { disposeGroup(model,true); return; }
            entry.model=model;
            entry.state="ready";
        },()=>{ entry.state="error"; }).then(()=>{
            if(currentCache===cache) setLoadout(previousBuild);
        });
        return entry;
    }
    function setLoadout(build) {
        if(!build) return;
        previousBuild=build;
        const career=build.loadout.career;
        const needed=new Set(), visibleModels=new Set(), equipmentModels=new Map(), status={slots:{}};
        function use(manualKey,packKey) {
            const model=manual.get(manualKey);
            if(model) { visibleModels.add(model); return {state:"ready",model}; }
            needed.add(packKey);
            const entry=packed(packKey);
            if(entry.model) visibleModels.add(entry.model);
            return entry;
        }
        const body=use("base:"+career,"characters:"+career);
        status.body=body.state;
        for(const slot of [0,1,2,3,4,5,6,10,11]) {
            const item=build.items[slot];
            if(!item) continue;
            if(slot>=10 && slot!==build.loadout.activeWeapon) { status.slots[slot]="inactive"; continue; }
            const entry=use(slot+":"+item.id,"items:"+item.id);
            status.slots[slot]=entry.state;
            equipmentModels.set(slot,entry.model);
        }
        // Original exports contain separate mesh components. Hide the base segment only
        // once the replacement is ready, so sparse packs and pending requests don't cut holes.
        const avatar=body.model;
        if(avatar) avatar.traverse(node=>{
            const slot=node.userData?.forgeEquipmentSlot;
            if(Number.isInteger(slot) && slot>=0 && slot<=4) node.visible=status.slots[slot]!=="ready";
            if(node.userData?.forgeFace===true) node.visible=equipmentModels.get(0)?.userData?.forgeHelmetFull!==true;
        });
        for(const model of displayed) if(!visibleModels.has(model)) {
            model.removeFromParent();
            displayed.delete(model);
        }
        for(const model of visibleModels) if(!displayed.has(model)) {
            scene.add(model);
            displayed.add(model);
        }
        for(const [key,entry] of cache) if(!needed.has(key)) {
            if(entry.model) disposeGroup(entry.model,true);
            cache.delete(key);
        }
        const weapon=build.items[build.loadout.activeWeapon]?.weapon;
        const activeClip=animator.sync(avatar,displayed,weapon);
        host.dataset.clip=activeClip;
        status.hasMotion=Boolean(activeClip);
        dirty=true;
        report(status);
    }
    resetCamera();
    function setPack(next) {
        const previous=cache;
        files=next;
        cache=new Map();
        setLoadout(previousBuild);
        for(const entry of previous.values()) if(entry.model) disposeGroup(entry.model,true);
        return next.size;
    }
    return {
        backend:renderer.backend.isWebGPUBackend?"WebGPU":"WebGL 2",
        setVisible,setLoadout,resetCamera,
        setParticles(on){enabledParticles=on;dirty=true;},
        setMotion(on){enabledMotion=on;animator.resetClock();dirty=true;},
        async assignPack(fileList) {
            const generation=++packGeneration;
            const next=new Map();
            let aliasFile;
            for(const file of fileList) {
                if(/^[^/]+\/item-aliases\.json$/i.test(file.webkitRelativePath) && file.size<=256*1024)
                    aliasFile=file;
                const match=file.webkitRelativePath.match(/^[^/]+\/(characters|items)\/(\d+)\.glb$/i);
                if(!match) continue;
                const key=match[1].toLowerCase()+":"+Number(match[2]);
                if(next.has(key)) throw new Error("Duplicate model ID");
                next.set(key,file);
            }
            if(!next.size) throw new Error("No ID-named exports found");
            if(aliasFile) {
                const aliases=JSON.parse(await aliasFile.text());
                if(!aliases || Array.isArray(aliases) || typeof aliases!=="object") throw new Error("Invalid item index");
                for(const [key,id] of Object.entries(aliases)) {
                    const variant=Number(key), file=next.get("items:"+id);
                    if(!Number.isSafeInteger(variant) || variant<=0 || String(variant)!==key ||
                        !Number.isSafeInteger(id) || !file || next.has("items:"+key)) continue;
                    if(file.aliasSource) continue;
                    next.set("items:"+key,{name:file.name,size:file.size,arrayBuffer:()=>file.arrayBuffer(),aliasSource:true});
                }
            }
            if(generation!==packGeneration) return 0;
            return setPack(next);
        },
        assignLocalPack(entries) {
            const next=new Map();
            for(const {kind,id,size} of entries) {
                if(!["characters","items"].includes(kind) || !Number.isSafeInteger(id) || id<=0 ||
                    !Number.isSafeInteger(size) || size<20 || size>80*1024*1024) continue;
                const key=kind+":"+id;
                next.set(key,{name:id+".glb",size,async arrayBuffer(){
                    const response=await fetch("/api/models/"+kind+"/"+id);
                    if(!response.ok) throw new Error("Local model unavailable");
                    const bytes=await response.arrayBuffer();
                    if(bytes.byteLength!==size) throw new Error("Local model changed");
                    return bytes;
                }});
            }
            if(!next.size) return 0;
            return setPack(next);
        },
        async assignModel(key,file) {
            if(!/^(?:base|0|1|2|3|4|5|6|10|11):\d+$/.test(key)) throw new Error("Invalid model target");
            const generation=manualGeneration;
            const model=await loadGlb(file);
            if(generation!==manualGeneration) { disposeGroup(model,true); return false; }
            const old=manual.get(key);
            manual.set(key,model);
            setLoadout(previousBuild);
            if(old) disposeGroup(old,true);
            return true;
        },
        clearModels() {
            manualGeneration++;
            packGeneration++;
            const originals=[...manual.values(),...[...cache.values()].flatMap(entry=>entry.model?[entry.model]:[])];
            manual.clear();
            files=new Map();
            cache=new Map();
            setLoadout(previousBuild);
            for(const model of originals) disposeGroup(model,true);
        },
    };
}
