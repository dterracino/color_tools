#version 330 core

in vec2 v_texcoord;
out vec4 fragColor;

uniform sampler2D u_texture;
uniform vec2      u_resolution;   // Screen / viewport resolution in pixels
uniform float     u_dither;       // Dither strength: 0.0 to 1.0

// -----------------------------------------------------------------------------
// Canonical 54-Color NES Master Palette in CIELAB (D65 illuminant, 2° observer)
// -----------------------------------------------------------------------------
const int NES_SIZE = 54;
const vec3 NES_LAB[54] = vec3[54](
    vec3( 0.00,   0.00,   0.00), vec3(43.19,   0.00,  -0.01), vec3(70.93,  -0.01,  -0.01),
    vec3(18.27,  27.42, -59.43), vec3(41.13,  19.51, -73.69), vec3(70.08, -13.06, -42.84),
    vec3(88.85, -11.91, -15.54), vec3(14.86,  39.54, -77.56), vec3(35.25,  45.39, -96.24),
    vec3(62.62,  16.89, -60.03), vec3(84.95,  -0.04, -22.39), vec3(14.77,  56.09, -68.41),
    vec3(34.25,  69.64, -98.66), vec3(60.91,  54.67, -59.60), vec3(83.74,  21.94, -20.65),
    vec3(17.84,  55.53, -40.91), vec3(35.15,  71.95, -57.82), vec3(59.96,  79.37, -51.30),
    vec3(83.18,  38.74, -18.72), vec3(18.17,  54.40,  -3.55), vec3(34.90,  69.04,  -9.06),
    vec3(60.52,  75.39,  -9.35), vec3(83.82,  36.56,  -4.10), vec3(17.38,  44.75,  26.06),
    vec3(35.91,  53.51,  40.40), vec3(63.95,  54.34,  44.42), vec3(85.74,  25.04,  20.40),
    vec3(18.52,  27.46,  32.14), vec3(37.60,  30.93,  48.06), vec3(68.57,  21.84,  64.55),
    vec3(87.89,   4.95,  34.02), vec3(21.46,  -4.18,  31.50), vec3(44.49,  -7.14,  48.00),
    vec3(74.79, -15.03,  70.61), vec3(90.69, -10.51,  38.30), vec3(26.24, -36.78,  34.58),
    vec3(50.41, -47.01,  49.62), vec3(79.32, -49.67,  65.51), vec3(91.75, -23.70,  38.79),
    vec3(29.62, -45.98,  32.74), vec3(54.49, -58.07,  44.52), vec3(81.82, -54.91,  50.96),
    vec3(92.42, -26.96,  24.97), vec3(28.84, -44.88,  21.36), vec3(53.64, -53.25,  26.35),
    vec3(80.59, -51.27,  21.05), vec3(91.87, -24.71,   9.28), vec3(23.99, -29.98,  -9.28),
    vec3(46.86, -33.91, -12.98), vec3(75.52, -31.42, -18.73), vec3(89.65, -15.65,  -7.24),
    vec3(33.58,   0.00,  -0.01), vec3(74.58,  -0.01,  -0.01), vec3(99.61,  -0.01,  -0.01)
);

const vec3 NES_SRGB[54] = vec3[54](
    vec3(0.0000, 0.0000, 0.0000), vec3(0.4000, 0.4000, 0.4000), vec3(0.6824, 0.6824, 0.6824),
    vec3(0.0000, 0.1647, 0.5333), vec3(0.0824, 0.3725, 0.8549), vec3(0.3922, 0.6902, 0.9961),
    vec3(0.7569, 0.8784, 0.9961), vec3(0.0784, 0.0706, 0.6588), vec3(0.2588, 0.2510, 0.9961),
    vec3(0.5765, 0.5647, 0.9961), vec3(0.8314, 0.8275, 0.9961), vec3(0.2314, 0.0000, 0.6431),
    vec3(0.4627, 0.1529, 1.0000), vec3(0.7804, 0.4667, 0.9961), vec3(0.9137, 0.7843, 0.9961),
    vec3(0.3608, 0.0000, 0.4941), vec3(0.6314, 0.1059, 0.8039), vec3(0.9529, 0.4157, 0.9961),
    vec3(0.9843, 0.7647, 0.9961), vec3(0.4314, 0.0000, 0.2510), vec3(0.7216, 0.1176, 0.4863),
    vec3(0.9961, 0.4314, 0.8039), vec3(0.9961, 0.7725, 0.9216), vec3(0.4235, 0.0275, 0.0000),
    vec3(0.7098, 0.1961, 0.1255), vec3(0.9961, 0.5098, 0.4392), vec3(0.9961, 0.8039, 0.7765),
    vec3(0.3412, 0.1137, 0.0000), vec3(0.6000, 0.3098, 0.0000), vec3(0.9216, 0.6235, 0.1373),
    vec3(0.9686, 0.8510, 0.6510), vec3(0.2039, 0.2078, 0.0000), vec3(0.4235, 0.4314, 0.0000),
    vec3(0.7412, 0.7490, 0.0000), vec3(0.8980, 0.9020, 0.5843), vec3(0.0471, 0.2863, 0.0000),
    vec3(0.2196, 0.5294, 0.0000), vec3(0.5373, 0.8510, 0.0000), vec3(0.8157, 0.9412, 0.5922),
    vec3(0.0000, 0.3216, 0.0000), vec3(0.0510, 0.5804, 0.0000), vec3(0.3647, 0.8980, 0.1882),
    vec3(0.7451, 0.9608, 0.6706), vec3(0.0000, 0.3098, 0.0314), vec3(0.0000, 0.5647, 0.1961),
    vec3(0.2706, 0.8824, 0.5098), vec3(0.7059, 0.9529, 0.8039), vec3(0.0000, 0.2510, 0.3059),
    vec3(0.0000, 0.4863, 0.5569), vec3(0.2824, 0.8078, 0.8745), vec3(0.7098, 0.9255, 0.9529),
    vec3(0.3098, 0.3098, 0.3098), vec3(0.7216, 0.7216, 0.7216), vec3(0.9961, 0.9961, 0.9961)
);

// -----------------------------------------------------------------------------
// 4 Fixed NES Sub-Palettes (13 Colors Total, sharing Color 0 = #000000)
// -----------------------------------------------------------------------------
const int SUB_PALETTES[16] = int[16](
    0,  1,  2, 53, // Greyscale / Metallic
    0, 23, 25, 30, // Warm / Reds / Skin
    0,  3,  5,  6, // Cool / Sky / Water
    0, 35, 37, 34  // Foliage / Earth Greens
);

// -----------------------------------------------------------------------------
// sRGB -> CIELAB Conversion
// -----------------------------------------------------------------------------
vec3 srgbToLinear(vec3 c) {
    return mix(c / 12.92, pow((c + 0.055) / 1.055, vec3(2.4)), step(0.04045, c));
}

float labF(float t) {
    const float delta = 6.0 / 29.0;
    return (t > (delta * delta * delta)) ? pow(t, 1.0 / 3.0) : (t / (3.0 * delta * delta) + 4.0 / 29.0);
}

vec3 rgbToLab(vec3 rgb) {
    vec3 lin = srgbToLinear(clamp(rgb, 0.0, 1.0));
    float x = dot(lin, vec3(0.4124564, 0.3575761, 0.1804375)) / 0.95047;
    float y = dot(lin, vec3(0.2126729, 0.7151522, 0.0721750)) / 1.00000;
    float z = dot(lin, vec3(0.0193339, 0.1191920, 0.9503041)) / 1.08883;

    float fx = labF(x);
    float fy = labF(y);
    float fz = labF(z);
    return vec3(116.0 * fy - 16.0, 500.0 * (fx - fy), 200.0 * (fy - fz));
}

float delta_e76_sq(vec3 a, vec3 b) {
    vec3 d = a - b;
    return dot(d, d);
}

// Bayer 4x4 threshold in range [0.0, 15.0 / 16.0]
float bayer4x4_val(ivec2 p) {
    const float M[16] = float[16](
         0.0,  8.0,  2.0, 10.0,
        12.0,  4.0, 14.0,  6.0,
         3.0, 11.0,  1.0,  9.0,
        15.0,  7.0, 13.0,  5.0
    );
    int idx = (p.y & 3) * 4 + (p.x & 3);
    return M[idx] / 16.0;
}

// -----------------------------------------------------------------------------
// Main Shader Body
// -----------------------------------------------------------------------------
void main() {
    // 1. Explicit use of v_texcoord ensures 'in_texcoord' attribute is retained by linker
    vec2 baseUv = v_texcoord;

    // 2. Aspect-ratio and integer-scaling handling
    // If u_resolution is not supplied or zero, default to a neutral 1:1 mapping
    vec2 res = (u_resolution.x > 0.0 && u_resolution.y > 0.0) ? u_resolution : vec2(textureSize(u_texture, 0));

    const vec2 NES_RES = vec2(256.0, 240.0);
    float intScale = max(1.0, floor(min(res.x / NES_RES.x, res.y / NES_RES.y)));
    vec2 frameSize = NES_RES * intScale;
    vec2 normFrameSize = frameSize / res;
    vec2 frameOffset = (vec2(1.0) - normFrameSize) * 0.5;

    // Pillarbox / Letterbox boundaries based on quad UV
    if (baseUv.x < frameOffset.x || baseUv.x >= frameOffset.x + normFrameSize.x ||
        baseUv.y < frameOffset.y || baseUv.y >= frameOffset.y + normFrameSize.y) {
        fragColor = vec4(0.0, 0.0, 0.0, 1.0);
        return;
    }

    // Remap quad UV into normalized [0.0, 1.0] inside the active NES screen area
    vec2 nesNormalizedUv = (baseUv - frameOffset) / normFrameSize;

    // Map directly to discrete integer NES pixel grid: [0..255, 0..239]
    ivec2 nesPixel = ivec2(floor(nesNormalizedUv * NES_RES));
    vec2 sampleUV = (vec2(nesPixel) + 0.5) / NES_RES;

    // 3. Select 1 of 4 Fixed Sub-Palettes for this 16x16 Attribute Block
    ivec2 attrBlock = nesPixel / 16; // Exactly 16 blocks wide, 15 blocks tall
    vec2 attrCenterUV = (vec2(attrBlock * 16) + 8.0) / NES_RES;

    vec3 localSampleLab = rgbToLab(texture(u_texture, attrCenterUV).rgb);

    int bestPalIdx = 0;
    float bestPalDist = 1e9;

    for (int p = 0; p < 4; ++p) {
        float minDist = 1e9;
        for (int c = 0; c < 4; ++c) {
            int palColorIdx = SUB_PALETTES[p * 4 + c];
            float d = delta_e76_sq(localSampleLab, NES_LAB[palColorIdx]);
            if (d < minDist) {
                minDist = d;
            }
        }
        if (minDist < bestPalDist) {
            bestPalDist = minDist;
            bestPalIdx = p;
        }
    }

    // 4. Strict 2-Color Dithering within Selected Sub-Palette
    vec3 pixelLab = rgbToLab(texture(u_texture, sampleUV).rgb);

    int firstColorIdx = SUB_PALETTES[bestPalIdx * 4];
    int secondColorIdx = SUB_PALETTES[bestPalIdx * 4 + 1];
    float d1 = 1e9;
    float d2 = 1e9;

    for (int c = 0; c < 4; ++c) {
        int palColorIdx = SUB_PALETTES[bestPalIdx * 4 + c];
        float d = delta_e76_sq(pixelLab, NES_LAB[palColorIdx]);
        if (d < d1) {
            d2 = d1;
            secondColorIdx = firstColorIdx;
            d1 = d;
            firstColorIdx = palColorIdx;
        } else if (d < d2) {
            d2 = d;
            secondColorIdx = palColorIdx;
        }
    }

    // Interlock dither between the closest two palette colors
    int finalPaletteIdx = firstColorIdx;
    if (u_dither > 0.0) {
        float bayer = bayer4x4_val(nesPixel);
        float blendFactor = clamp((d2 - d1) / (d2 + 1e-4), 0.0, 1.0);
        if ((1.0 - blendFactor) * u_dither > bayer) {
            finalPaletteIdx = secondColorIdx;
        }
    }

    fragColor = vec4(NES_SRGB[finalPaletteIdx], 1.0);
}