// PICO-8 Palette Shader
// =============================================================================
// Quantises every pixel to the PICO-8 fantasy console's 16-colour palette.
// PICO-8 is a popular modern retro platform with a carefully curated palette
// that gives images a distinctive, vibrant look.
//
// Uniforms
//   u_texture   – source image / video frame (sampler2D)
//   u_pixelate  – pixel-block size (1 = off, 3-4 works well for PICO-8 feel)
//   u_dither    – Bayer dither strength (0.0 = off, 1.0 = full)
//
// Palette source: color_tools data/palettes/pico8.json
// =============================================================================

#version 330 core

in  vec2  v_texcoord;
out vec4  fragColor;

uniform sampler2D u_texture;
uniform float     u_pixelate;  // default 3.0
uniform float     u_dither;    // default 0.0

// ---------------------------------------------------------------------------
// PICO-8 16-colour palette
// ---------------------------------------------------------------------------
const int PICO8_SIZE = 16;
const vec3 PICO8_PALETTE[16] = vec3[16](
    vec3(0.0000, 0.0000, 0.0000),  // black       #000000
    vec3(0.1137, 0.1686, 0.3255),  // dark-blue   #1D2B53
    vec3(0.4941, 0.1451, 0.3255),  // dark-purple #7E2553
    vec3(0.0000, 0.5294, 0.3176),  // dark-green  #008751
    vec3(0.6706, 0.3216, 0.2118),  // brown       #AB5236
    vec3(0.3725, 0.3412, 0.3098),  // dark-grey   #5F574F
    vec3(0.7608, 0.7647, 0.7804),  // light-grey  #C2C3C7
    vec3(1.0000, 0.9451, 0.9098),  // white       #FFF1E8
    vec3(1.0000, 0.0000, 0.3020),  // red         #FF004D
    vec3(1.0000, 0.6392, 0.0000),  // orange      #FFA300
    vec3(1.0000, 0.9255, 0.1529),  // yellow      #FFEC27
    vec3(0.0000, 0.8941, 0.2118),  // green       #00E436
    vec3(0.1608, 0.6784, 1.0000),  // blue        #29ADFF
    vec3(0.5137, 0.4627, 0.6118),  // lavender    #83769C
    vec3(1.0000, 0.4667, 0.6588),  // pink        #FF77A8
    vec3(1.0000, 0.8000, 0.6667)   // light-peach #FFCCAA
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
vec3 nearest_pico8(vec3 color) {
    float best_dist = 1e9;
    vec3  best_col  = PICO8_PALETTE[0];
    for (int i = 0; i < PICO8_SIZE; i++) {
        vec3  delta = color - PICO8_PALETTE[i];
        float dist  = dot(delta, delta);
        if (dist < best_dist) {
            best_dist = dist;
            best_col  = PICO8_PALETTE[i];
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
        float noise = bayer4x4(px) * u_dither * (1.0 / float(PICO8_SIZE));
        color = clamp(color + vec3(noise), 0.0, 1.0);
    }

    fragColor = vec4(nearest_pico8(color), 1.0);
}
