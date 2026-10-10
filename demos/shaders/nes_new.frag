#version 330 core

in vec2 v_texcoord;
out vec4 fragColor;

uniform sampler2D u_texture;
uniform vec2      u_resolution;  // Viewport/window resolution in pixels
uniform float     u_dither;      // 0.0 to 1.0 (default ~0.75 - 1.0)
uniform int       u_crop_overscan;// 1 = crop top/bottom 8px (256x224), 0 = 256x240

// -----------------------------------------------------------------------------
// Canonical NES Master Palette (54 Colors, sRGB)
// -----------------------------------------------------------------------------
const int NES_SIZE = 54;
const vec3 NES_PALETTE[54] = vec3[54](
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
// Bayer 4x4 Dither Matrix (Normalized to [-0.5, 0.5])
// -----------------------------------------------------------------------------
float bayer4x4(ivec2 p) {
    const float M[16] = float[16](
         0.0,  8.0,  2.0, 10.0,
        12.0,  4.0, 14.0,  6.0,
         3.0, 11.0,  1.0,  9.0,
        15.0,  7.0, 13.0,  5.0
    );
    int idx = (p.y & 3) * 4 + (p.x & 3);
    return (M[idx] / 16.0) - 0.5;
}

// Perceptual luminance weights
float getLuminance(vec3 c) {
    return dot(c, vec3(0.299, 0.587, 0.114));
}

// Nearest color from master NES palette using weighted Euclidean distance
vec3 findNearestNes(vec3 color) {
    float best_dist = 1e9;
    vec3  best_col  = NES_PALETTE[0];
    
    for (int i = 0; i < NES_SIZE; ++i) {
        vec3 delta = color - NES_PALETTE[i];
        // Slight perceptual weighting on RGB delta components
        float dist = dot(delta * vec3(0.3, 0.59, 0.11), delta);
        if (dist < best_dist) {
            best_dist = dist;
            best_col = NES_PALETTE[i];
        }
    }
    return best_col;
}

// Nearest color chosen strictly from the active 4-color sub-palette
vec3 findNearestSubPalette(vec3 color, vec3 pal[4]) {
    float best_dist = 1e9;
    vec3 best_col = pal[0];
    for (int i = 0; i < 4; ++i) {
        vec3 delta = color - pal[i];
        float dist = dot(delta, delta);
        if (dist < best_dist) {
            best_dist = dist;
            best_col = pal[i];
        }
    }
    return best_col;
}

void main() {
    // 1. Calculate 4:3 Aspect-Correct Display Box inside the Viewport
    vec2 targetAspect = vec2(4.0, 3.0);
    float screenAspect = u_resolution.x / u_resolution.y;
    float desiredAspect = targetAspect.x / targetAspect.y;

    vec2 boxScale = vec2(1.0);
    if (screenAspect > desiredAspect) {
        boxScale.x = desiredAspect / screenAspect; // Pillarbox
    } else {
        boxScale.y = screenAspect / desiredAspect; // Letterbox
    }

    vec2 uv = (v_texcoord - 0.5) / boxScale + 0.5;

    // Mask out borders
    if (uv.x < 0.0 || uv.x > 1.0 || uv.y < 0.0 || uv.y > 1.0) {
        fragColor = vec4(0.0, 0.0, 0.0, 1.0);
        return;
    }

    // 2. Native NES Pixel Grid Mapping (256x240 or 256x224 with overscan crop)
    vec2 nesDim = (u_crop_overscan == 1) ? vec2(256.0, 224.0) : vec2(256.0, 240.0);
    vec2 nesPixelCoord = floor(uv * nesDim);
    
    // Convert back to quantized UV for sampling source texture
    vec2 sampleUV = (nesPixelCoord + 0.5) / nesDim;

    // 3. Emulate 16x16 Attribute Blocks
    // An attribute block on NES is 16x16 pixels sharing one 4-color palette
    vec2 attrBlockCoord = floor(nesPixelCoord / 16.0);
    vec2 attrCenterUV = ((attrBlockCoord * 16.0) + 8.0) / nesDim;

    // Probe the 16x16 region (center, corners) to derive the local dominant color range
    vec2 texel = 1.0 / nesDim;
    vec3 sC = texture(u_texture, attrCenterUV).rgb;
    vec3 sTL = texture(u_texture, attrCenterUV - 6.0 * texel).rgb;
    vec3 sBR = texture(u_texture, attrCenterUV + 6.0 * texel).rgb;

    // Pick 3 representative local colors ordered by tone
    vec3 localDark  = findNearestNes(min(sC, min(sTL, sBR)));
    vec3 localLight = findNearestNes(max(sC, max(sTL, sBR)));
    vec3 localMid   = findNearestNes(sC);

    // Color 0 is universally the backdrop color (typically near-black or deep dark blue/brown)
    vec3 globalBackdrop = NES_PALETTE[0]; // #000000

    // Assemble the strict 4-color sub-palette for this 16x16 block
    vec3 subPalette[4];
    subPalette[0] = globalBackdrop;
    subPalette[1] = localDark;
    subPalette[2] = localMid;
    subPalette[3] = localLight;

    // 4. Sample the pixel, apply Bayer dithering at the native NES resolution
    vec3 srcColor = texture(u_texture, sampleUV).rgb;

    if (u_dither > 0.0) {
        // Bayer matrix indexed by NES native pixel coordinates
        float ditherOffset = bayer4x4(ivec2(nesPixelCoord)) * (u_dither * 0.22);
        srcColor = clamp(srcColor + vec3(ditherOffset), 0.0, 1.0);
    }

    // 5. Quantize to the active 16x16 sub-palette
    vec3 finalColor = findNearestSubPalette(srcColor, subPalette);

    fragColor = vec4(finalColor, 1.0);
}