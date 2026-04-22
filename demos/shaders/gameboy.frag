// Game Boy (DMG) Palette Shader
// =============================================================================
// Quantises every pixel to the classic Game Boy 4-shade green palette.
// The original DMG used a green-tinted LCD.  This shader maps any input image
// to those 4 shades, giving the authentic "pocket handheld" look.
//
// Uniforms
//   u_texture   – source image / video frame (sampler2D)
//   u_pixelate  – pixel-block size (1 = off, 3-6 works well for GB feel)
//   u_dither    – Bayer dither strength (0.0 = off, 1.0 = full)
//
// Palette source: color_tools data/palettes/gameboy.json
// =============================================================================

#version 330 core

in  vec2  v_texcoord;
out vec4  fragColor;

uniform sampler2D u_texture;
uniform float     u_pixelate;  // default 4.0
uniform float     u_dither;    // default 0.0

// ---------------------------------------------------------------------------
// Game Boy DMG 4-colour palette
// ---------------------------------------------------------------------------
const int GB_SIZE = 4;
const vec3 GB_PALETTE[4] = vec3[4](
    vec3(0.0275, 0.0941, 0.1294),  // darkest_green  #071821
    vec3(0.1882, 0.4078, 0.3137),  // dark_green     #306850
    vec3(0.5255, 0.7529, 0.4235),  // light_green    #86C06C
    vec3(0.8784, 0.9725, 0.8118)   // lightest_green #E0F8CF
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
vec3 nearest_gb(vec3 color) {
    float best_dist = 1e9;
    vec3  best_col  = GB_PALETTE[0];
    for (int i = 0; i < GB_SIZE; i++) {
        vec3  delta = color - GB_PALETTE[i];
        float dist  = dot(delta, delta);
        if (dist < best_dist) {
            best_dist = dist;
            best_col  = GB_PALETTE[i];
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

    // Convert to greyscale first so the GB 4 shades make sense
    float grey = dot(color, vec3(0.299, 0.587, 0.114));
    color = vec3(grey);

    if (u_dither > 0.0) {
        ivec2 px    = ivec2(gl_FragCoord.xy);
        float noise = bayer4x4(px) * u_dither * (1.0 / float(GB_SIZE));
        color = clamp(color + vec3(noise), 0.0, 1.0);
    }

    fragColor = vec4(nearest_gb(color), 1.0);
}
