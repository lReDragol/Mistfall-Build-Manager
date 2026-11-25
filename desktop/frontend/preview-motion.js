import { Matrix4, Quaternion, Vector3 } from "three/webgpu";

// The pack preserves each original skin and stores the game's idle samples by
// joint name; clothing can therefore come and go without rebuilding the rig.
export function createMotionController() {
    const rigs = new WeakMap(), clips = new WeakMap();
    const q0 = new Quaternion(), q1 = new Quaternion(), position = new Vector3();
    const matrix = new Matrix4(), inverse = new Matrix4();
    let avatar, clip, key = "", time = 0, last = null, channels = [], attachments = [];

    function rig(root) {
        if (rigs.has(root)) return rigs.get(root);
        const byName = new Map(), joints = [], grips = [];
        root.updateMatrixWorld(true);
        root.traverse(node => {
            if (node.isSkinnedMesh) node.frustumCulled = false;
            const name = node.userData?.forgeJoint;
            if (node.isBone && typeof name === "string" && name.length <= 100) {
                const bone = { node, name, p: node.position.clone(), q: node.quaternion.clone(),
                    inverseBind: node.matrixWorld.clone().invert() };
                joints.push(bone);
                if (!byName.has(name)) byName.set(name, bone);
            }
            const anchor = node.userData?.forgeAnchor;
            if (typeof anchor?.bone === "string") {
                const tuple = (arr,len) => Array.isArray(arr) && arr.length === len && arr.every(Number.isFinite);
                const native = tuple(anchor.p,3) && tuple(anchor.q,4) && tuple(anchor.s,3);
                const local = native ? new Matrix4().compose(new Vector3(...anchor.p),
                    new Quaternion(...anchor.q).normalize(), new Vector3(...anchor.s)) : null;
                grips.push({ node, parent: node.parent, bone: anchor.bone, local,
                    p: node.position.clone(), q: node.quaternion.clone(), s: node.scale.clone(),
                    restWorld: node.matrixWorld.clone() });
            }
        });
        const result = { root, byName, joints, grips };
        rigs.set(root, result);
        return result;
    }

    function catalog(root) {
        if (clips.has(root)) return clips.get(root);
        const source = root.userData?.forgeMotion, result = new Map();
        if (source && typeof source === "object") for (const [name, raw] of Object.entries(source).slice(0, 8)) {
            const frames = raw?.frames, fps = raw?.fps;
            if (!Number.isInteger(frames) || frames < 2 || frames > 1200 || !Number.isFinite(fps) || fps < 1 ||
                fps > 120 || typeof raw?.tracks !== "object" || !raw.tracks) continue;
            const tracks = new Map();
            for (const [joint, array] of Object.entries(raw.tracks).slice(0, 320)) {
                const stride = joint === "Bip001" ? 7 : 4;
                if (!Array.isArray(array) || (array.length !== stride && array.length !== frames * stride) ||
                    !array.every(number => Number.isFinite(number) && Math.abs(number) < 8)) continue;
                tracks.set(joint, { values: new Float32Array(array), stride,
                    constant: array.length === stride, bones: [] });
            }
            if (tracks.size >= 15) result.set(name, { frames, fps, tracks });
        }
        clips.set(root, result);
        delete root.userData.forgeMotion; // keep the compact typed samples only
        return result;
    }

    function sample(frame) {
        const start = Math.floor(frame), next = Math.min(clip.frames - 1,start + 1), alpha = frame - start;
        for (const { values, stride, constant, bones } of channels) {
            const a = constant ? 0 : start * stride, b = constant ? 0 : next * stride;
            const r = stride - 4;
            q0.fromArray(values,a+r).normalize();
            if (!constant) q0.slerp(q1.fromArray(values,b+r).normalize(),alpha);
            if (r) position.set(values[a]+(values[b]-values[a])*alpha,
                values[a+1]+(values[b+1]-values[a+1])*alpha,
                values[a+2]+(values[b+2]-values[a+2])*alpha);
            for (const { node } of bones) {
                node.quaternion.copy(q0);
                // Keep the fitted parts' respective limb lengths and animate
                // only the shared pelvis translation.
                if (r) node.position.copy(position);
            }
        }
        avatar.root.updateMatrixWorld(true);
        for (const { grip, bone } of attachments) {
            if (grip.local) matrix.copy(bone.node.matrixWorld).multiply(grip.local);
            else matrix.copy(bone.node.matrixWorld).multiply(bone.inverseBind).multiply(grip.restWorld);
            matrix.premultiply(inverse.copy(grip.parent.matrixWorld).invert());
            matrix.decompose(grip.node.position,grip.node.quaternion,grip.node.scale);
        }
    }

    return {
        sync(root, models, weapon) {
            const set = root ? catalog(root) : null;
            const selected = set?.has(weapon) ? weapon : set?.keys().next().value;
            const nextClip = set?.get(selected);
            if (clip !== nextClip) { time = 0; last = null; }
            avatar = root ? rig(root) : null;
            clip = nextClip;
            key = clip ? selected : "";
            attachments = [];
            for (const track of channels) track.bones.length = 0;
            channels = clip ? [...clip.tracks.values()] : [];
            for (const model of models) {
                const data = rig(model);
                for (const joint of data.joints) {
                    joint.node.position.copy(joint.p);
                    joint.node.quaternion.copy(joint.q);
                    clip?.tracks.get(joint.name)?.bones.push(joint);
                }
                for (const grip of data.grips) {
                    grip.node.position.copy(grip.p); grip.node.quaternion.copy(grip.q); grip.node.scale.copy(grip.s);
                    const bone = avatar?.byName.get(grip.bone);
                    if (clip && bone) attachments.push({ grip,bone });
                }
            }
            if (clip) advance(0);
            return key;
        },
        step(now, playing) {
            if (!clip || !playing) { last = null; return false; }
            if (last === null) last = now;
            advance(Math.min(.05,Math.max(0,(now-last)*.001)));
            last = now;
            return true;
        },
        resetClock() { last = null; },
    };
    function advance(delta) {
        const end = clip.frames - 1;
        // Several native idle clips do not have identical endpoints. A
        // ping-pong sample avoids a hard jump back to their first key.
        time = (time + delta * clip.fps) % (2 * end);
        sample(time <= end ? time : 2 * end - time);
    }
}
