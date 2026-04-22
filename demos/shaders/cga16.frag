// CGA 16-colour Palette Shader
// =============================================================================
// Quantises every pixel to the IBM CGA 16-colour palette.
// This recreates the look of DOS-era games and early PC graphics from the
// mid-1980s.  The palette includes the notorious "CGA brown" (dark yellow).
//
// Uniforms
//   u_texture   – source image / video frame (sampler2D)
//   u_pixelate  – pixel-block size (1 = off, 3-4 works well for CGA feel)
//   u_dither    – Bayer dither strength (0.0 = off, 1.0 = full)
//
// Palette source: color_tools data/palettes/cga16.json
// =============================================================================

#version 330 core

in  vec2  v_texcoord;
out vec4  fragColor;

uniform sampler2D u_texture;
uniform float     u_pixelate;  // default 3.0
uniform float     u_dither;    // default 0.0

// ---------------------------------------------------------------------------
// CGA 16-colour palette
// ---------------------------------------------------------------------------
const int CGA_SIZE = 16;
const vec3 CGA_PALETTE[16] = vec3[16](
    vec3(0.0000, 0.0000, 0.0000),  // black              #000000
    vec3(0.0000, 0.0000, 0.6667),  // dark blue          #0000aa
    vec3(0.0000, 0.6667, 0.0000),  // dark green         #00aa00
    vec3(0.0000, 0.6667, 0.6667),  // dark cyan          #00aaaa
    vec3(0.6667, 0.0000, 0.0000),  // dark red           #aa0000
    vec3(0.6667, 0.0000, 0.6667),  // dark magenta       #aa00aa
    vec3(0.6667, 0.3333, 0.0000),  // brown              #aa5500
    vec3(0.6667, 0.6667, 0.6667),  // light grey         #aaaaaa
    vec3(0.3333, 0.3333, 0.3333),  // dark grey          #555555
    vec3(0.3333, 0.3333, 1.0000),  // bright blue        #5555ff
    vec3(0.3333, 1.0000, 0.3333),  // bright green       #55ff55
    vec3(0.3333, 1.0000, 1.0000),  // bright cyan        #55ffff
    vec3(1.0000, 0.3333, 0.3333),  // bright red         #ff5555
    vec3(1.0000, 0.3333, 1.0000),  // bright magenta     #ff55ff
    vec3(1.0000, 1.0000, 0.3333),  // bright yellow      #ffff55
    vec3(1.0000, 1.0000, 1.0000)   // white              #ffffff
);

// ---------------------------------------------------------------------------
// Bayer 4×4 ordered dither (normalised to [-0.5, 0.5])
// ---------------------------------------------------------------------------
float bayer4x4(ivec2 p) {
    int x = p.x & 3;
    int y = p.y & 3;
    int idx = y * 4 + x;
    float[16] M = float[16](
         0.0,  8.0,  2.0, 10.0,
        12.0,  4.0, 14.0,  6.0,
         3.0, 11.0,  1.0,  9.0,
        15.0,  7.0, 13.0,  5.0
    );
    return (M[idx] / 16.0) - 0.5;
}

// ---------------------------------------------------------------------------
// Nearest colour
// ---------------------------------------------------------------------------
vec3 nearest_cga(vec3 color) {
    float best_dist = 1e9;
    vec3  best_col  = CGA_PALETTE[0];
    for (int i = 0; i < CGA_SIZE; i++) {
        vec3  delta = color - CGA_PALETTE[i];
        float dist  = dot(delta, delta);
        if (dist < best_dist) {
            best_dist = dist;
            best_col  = CGA_PALETTE[i];
        }
    }
    return best_col;
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------
void main() {
    vec2 uv = v_texcoord;
    if (u_pixelate > 1.0) {
        vec2 texSize   = vec2(textureSize(u_texture, 0));
        vec2 blockSize = vec2(u_pixelate) / texSize;
        uv = (floor(uv / blockSize) + 0.5) * blockSize;
    }

    vec3 color = texture(u_texture, uv).rgb;

    if (u_dither > 0.0) {
        ivec2 px    = ivec2(gl_FragCoord.xy);
        float noise = bayer4x4(px) * u_dither * (1.0 / float(CGA_SIZE));
        color = clamp(color + vec3(noise), 0.0, 1.0);
    }

    fragColor = vec4(nearest_cga(color), 1.0);
}
