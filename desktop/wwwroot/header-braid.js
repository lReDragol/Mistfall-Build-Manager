const canvas = document.getElementById("header-braid");
const motion = matchMedia("(prefers-reduced-motion: reduce)");
const gl = canvas?.getContext("webgl", {
    alpha: true, antialias: false, depth: false, stencil: false, premultipliedAlpha: true,
    powerPreference: "low-power"
});

const vertex = `
    attribute vec2 a_position;
    void main() { gl_Position = vec4(a_position, 0.0, 1.0); }
`;
const fragment = `
    precision highp float;
    uniform vec2 u_size;
    uniform float u_height;
    uniform float u_width;
    uniform float u_time;
    uniform float u_motion;
    float hash(float n) { return fract(sin(n * 12.9898 + 78.233) * 43758.5453); }
    void main() {
        float px = (gl_FragCoord.x / u_size.x - 0.5) * u_width;
        float y = (gl_FragCoord.y / u_size.y - 0.5) * u_height;
        float x = px / min(220.0, u_width * 0.24);
        float span = abs(px) * 2.0 / u_width;
        float taper = max(0.0, 1.0 - span * span);
        // The spatial envelope has zero slope where it reaches the ends of the divider.
        float spread = taper * taper * exp(-0.55 * x * x);
        float merge = 1.0 - smoothstep(0.045, 0.64, spread);
        float line = (1.0 - smoothstep(0.16, 1.03, abs(y))) * (0.24 + 0.08 * sqrt(spread)) * merge;
        vec2 halo = vec2(px / 120.0, y / 11.0);
        float aura = 0.062 * exp(-dot(halo, halo));
        vec3 amber = vec3(0.74, 0.46, 0.17);
        vec3 gold = vec3(1.0, 0.86, 0.57);
        float fiber = 0.0, front = -3.0;
        vec3 goldFront = gold;
        if (spread > 0.006 && abs(y) < 23.0) {
            for (int i = 0; i < 6; i++) {
                float strand = float(i);
                float dir = 1.0 - 2.0 * mod(strand, 2.0);
                // Every filament has its own phase, pitch and speed, including within each direction.
                float pitch = 3.05 + 0.19 * strand;
                float speed = 0.62 + 0.092 * strand;
                float phase = pitch * x + dir * speed * u_time + strand * 1.0472;
                float ripple = sin(0.9 * x - dir * speed * 0.47 * u_time + strand * 1.46);
                float angle = phase + 0.18 * ripple;
                float amplitude = 14.1 + 0.59 * strand;
                float center = (amplitude * sin(angle) - 1.2 * sin(3.0 * angle) + 1.5 * ripple) * spread;
                float depth = cos(angle);
                float distance = abs(y - center);
                float coverage = 1.0 - smoothstep(0.12, 1.12, distance);
                float score = depth - 2.8 * (1.0 - coverage);
                fiber = max(fiber, coverage * (0.70 + 0.18 * depth));
                if (score > front) {
                    front = score;
                    goldFront = mix(amber, gold, 0.52 + 0.27 * depth + 0.04 * strand);
                }
            }
        }
        float dust = 0.0;
        if (u_motion > 0.5 && abs(px) < 155.0 && abs(y) < 30.0) {
            for (int i = 0; i < 11; i++) {
                float id = float(i) + 1.0;
                float life = 2.0 + 2.0 * hash(id);
                float cycle = life + 0.55 + hash(id + 9.0);
                float clock = u_time + cycle * hash(id + 2.0);
                float age = mod(clock, cycle);
                float seed = id * 17.0 + floor(clock / cycle) * 43.0;
                float angle = 6.283185 * hash(seed + 1.0);
                vec2 drift = vec2(cos(angle) * 8.0, sin(angle) * 3.2);
                vec2 p = vec2((hash(seed + 2.0) - 0.5) * 226.0, (hash(seed + 3.0) - 0.5) * 30.0);
                p += drift * age + vec2(sin(age * 1.7 + seed) * 1.6, sin(age * 1.1 + seed) * 1.2);
                float opacity = smoothstep(0.0, 0.55, age) * (1.0 - smoothstep(life - 0.75, life, age));
                float radius = mix(0.7, 1.65, hash(seed + 4.0));
                dust = max(dust, (1.0 - smoothstep(0.0, radius, length(vec2(px, y) - p))) * opacity * 0.70);
            }
        }
        // Fade the subpixel filaments into the same continuous spine without adding their brightness.
        fiber *= smoothstep(0.017, 0.25, spread);
        float thread = max(line, fiber);
        vec3 rgb = mix(amber, goldFront, fiber / max(line + fiber, 0.0001));
        float amount = thread + aura + dust;
        gl_FragColor = vec4((rgb * thread + vec3(0.95, 0.72, 0.38) * aura + gold * dust)
                            / max(1.0, amount), min(1.0, amount));
    }
`;

if (gl) {
    let program, size, height, width, time, enabled, frame = 0, previous = -Infinity, cssHeight = 64, cssWidth = 1;
    const draw = (now, still = false) => {
        if (!program || gl.isContextLost()) return;
        gl.uniform2f(size, canvas.width, canvas.height);
        gl.uniform1f(height, cssHeight);
        gl.uniform1f(width, cssWidth);
        gl.uniform1f(enabled, still ? 0 : 1);
        gl.uniform1f(time, still ? 1.2 : now / 1000);
        gl.clear(gl.COLOR_BUFFER_BIT);
        gl.drawArrays(gl.TRIANGLES, 0, 3);
    };
    const run = now => {
        frame = 0;
        if (document.hidden || motion.matches || !program || gl.isContextLost()) return;
        if (now - previous >= 32) { draw(now); previous = now; }
        frame = requestAnimationFrame(run);
    };
    const sync = () => {
        cancelAnimationFrame(frame);
        frame = 0;
        if (document.hidden || !program || gl.isContextLost()) return;
        if (motion.matches) draw(0, true);
        else { previous = -Infinity; frame = requestAnimationFrame(run); }
    };
    const resize = () => {
        if (!program || gl.isContextLost()) return;
        const rect = canvas.getBoundingClientRect();
        const dpr = Math.min(window.devicePixelRatio || 1, 1.5);
        const w = Math.max(1, Math.round(rect.width * dpr));
        const h = Math.max(1, Math.round(rect.height * dpr));
        cssHeight = Math.max(1, rect.height);
        cssWidth = Math.max(1, rect.width);
        if (canvas.width !== w || canvas.height !== h) {
            canvas.width = w; canvas.height = h;
        }
        gl.viewport(0, 0, w, h);
        if (!document.hidden) draw(performance.now(), motion.matches);
    };
    const init = () => {
        const compile = (kind, source) => {
            const shader = gl.createShader(kind);
            if (!shader) return null;
            gl.shaderSource(shader, source);
            gl.compileShader(shader);
            if (gl.getShaderParameter(shader, gl.COMPILE_STATUS)) return shader;
            gl.deleteShader(shader);
            return null;
        };
        const vs = compile(gl.VERTEX_SHADER, vertex), fs = compile(gl.FRAGMENT_SHADER, fragment);
        const linked = gl.createProgram();
        if (vs && fs && linked) {
            gl.attachShader(linked, vs); gl.attachShader(linked, fs);
            gl.linkProgram(linked);
        }
        if (vs) gl.deleteShader(vs);
        if (fs) gl.deleteShader(fs);
        if (!linked || !gl.getProgramParameter(linked, gl.LINK_STATUS)) {
            if (linked) gl.deleteProgram(linked);
            return;
        }
        const buffer = gl.createBuffer();
        if (!buffer) { gl.deleteProgram(linked); return; }
        program = linked;
        gl.useProgram(program);
        gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
        gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);
        const position = gl.getAttribLocation(program, "a_position");
        gl.enableVertexAttribArray(position);
        gl.vertexAttribPointer(position, 2, gl.FLOAT, false, 0, 0);
        size = gl.getUniformLocation(program, "u_size");
        height = gl.getUniformLocation(program, "u_height");
        width = gl.getUniformLocation(program, "u_width");
        enabled = gl.getUniformLocation(program, "u_motion");
        time = gl.getUniformLocation(program, "u_time");
        gl.clearColor(0, 0, 0, 0);
        resize();
        canvas.dataset.render = "webgl";
        sync();
    };
    canvas.addEventListener("webglcontextlost", event => {
        event.preventDefault();
        program = null;
        delete canvas.dataset.render;
        sync();
    });
    canvas.addEventListener("webglcontextrestored", init);
    new ResizeObserver(resize).observe(canvas);
    window.addEventListener("resize", resize);
    document.addEventListener("visibilitychange", sync);
    motion.addEventListener("change", sync);
    init();
}
