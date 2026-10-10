#version 330 core

in vec2 v_texcoord;
out vec4 fragColor;

uniform sampler2D u_texture;
uniform vec2      u_resolution;
uniform float     u_dither;       // Default ~0.75 - 1.0
uniform int       u_crop_overscan;// 1 = 256x224, 0 = 256x240

#define PI 3.14159265358979323846

// -----------------------------------------------------------------------------
// Canonical 54-Color NES Master Palette in CIELAB (D65 illuminant, 2° observer)
// L* in [0, 100], a* in [-128, 127], b* in [-128, 127]
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

// Corresponding sRGB values for final output emission
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
// Color Conversion: sRGB -> Linear RGB -> CIEXYZ -> CIELAB
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
    
    // sRGB D65 transform matrix
    float x = dot(lin, vec3(0.4124564, 0.3575761, 0.1804375)) / 0.95047;
    float y = dot(lin, vec3(0.2126729, 0.7151522, 0.0721750)) / 1.00000;
    float z = dot(lin, vec3(0.0193339, 0.1191920, 0.9503041)) / 1.08883;

    float fx = labF(x);
    float fy = labF(y);
    float fz = labF(z);

    return vec3(116.0 * fy - 16.0, 500.0 * (fx - fy), 200.0 * (fy - fz));
}

// -----------------------------------------------------------------------------
// CIEDE2000 Delta E Implementation
// -----------------------------------------------------------------------------
float deltaE2000(vec3 lab1, vec3 lab2) {
    float L1 = lab1.x, a1 = lab1.y, b1 = lab1.z;
    float L2 = lab2.x, a2 = lab2.y, b2 = lab2.z;

    float avgL = 0.5 * (L1 + L2);
    float C1 = length(lab1.yz);
    float C2 = length(lab2.yz);
    float avgC = 0.5 * (C1 + C2);

    float avgC7 = pow(avgC, 7.0);
    float G = 0.5 * (1.0 - sqrt(avgC7 / (avgC7 + 6103515625.0))); // 25^7 = 6103515625

    float a1P = (1.0 + G) * a1;
    float a2P = (1.0 + G) * a2;
    float C1P = length(vec2(a1P, b1));
    float C2P = length(vec2(a2P, b2));
    float avgCP = 0.5 * (C1P + C2P);

    float h1P = atan(b1, a1P);
    if (h1P < 0.0) h1P += 2.0 * PI;
    float h2P = atan(b2, a2P);
    if (h2P < 0.0) h2P += 2.0 * PI;

    float avghP = 0.5 * (h1P + h2P);
    if (abs(h1P - h2P) > PI) {
        avghP += (avghP < PI) ? PI : -PI;
    }

    float T = 1.0 - 0.17 * cos(avghP - radians(30.0))
                  + 0.24 * cos(2.0 * avghP)
                  + 0.32 * cos(3.0 * avghP + radians(6.0))
                  - 0.20 * cos(4.0 * avghP - radians(63.0));

    float deltahP = h2P - h1P;
    if (abs(deltahP) > PI) {
        deltahP += (h2P <= h1P) ? 2.0 * PI : -2.0 * PI;
    }

    float deltaLP = L2 - L1;
    float deltaCP = C2P - C1P;
    float deltaHP = 2.0 * sqrt(C1P * C2P) * sin(0.5 * deltahP);

    float avgL_minus_50_sq = (avgL - 50.0) * (avgL - 50.0);
    float SL = 1.0 + (0.015 * avgL_minus_50_sq) / sqrt(20.0 + avgL_minus_50_sq);
    float SC = 1.0 + 0.045 * avgCP;
    float SH = 1.0 + 0.015 * avgCP * T;

    float avgCP7 = pow(avgCP, 7.0);
    float deltaTheta = radians(30.0) * exp(-pow((degrees(avghP) - 275.0) / 25.0, 2.0));
    float RC = 2.0 * sqrt(avgCP7 / (avgCP7 + 6103515625.0));
    float RT = -sin(2.0 * deltaTheta) * RC;

    float vL = deltaLP / SL;
    float vC = deltaCP / SC;
    float vH = deltaHP / SH;

    return sqrt(vL * vL + vC * vC + vH * vH + RT * vC * vH);
}

// -----------------------------------------------------------------------------
// Bayer 4x4
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

// Global master search using deltaE2000
int findNearestNesLab(vec3 lab) {
    float best_dist = 1e9;
    int   best_idx  = 0;
    for (int i = 0; i < NES_SIZE; ++i) {
        float d = deltaE2000(lab, NES_LAB[i]);
        if (d < best_dist) {
            best_dist = d;
            best_idx  = i;
        }
    }
    return best_idx;
}

// Sub-palette search using deltaE2000 over 4 candidate indices
int findNearestSubPalette(vec3 lab, int pal[4]) {
    float best_dist = 1e9;
    int   best_idx  = pal[0];
    for (int i = 0; i < 4; ++i) {
        float d = deltaE2000(lab, NES_LAB[pal[i]]);
        if (d < best_dist) {
            best_dist = d;
            best_idx  = pal[i];
        }
    }
    return best_idx;
}

void main() {
    // 1. Aspect Ratio Correction (4:3 Display Box)
    vec2 targetAspect = vec2(4.0, 3.0);
    float screenAspect = u_resolution.x / u_resolution.y;
    float desiredAspect = targetAspect.x / targetAspect.y;

    vec2 boxScale = vec2(1.0);
    if (screenAspect > desiredAspect) {
        boxScale.x = desiredAspect / screenAspect;
    } else {
        boxScale.y = screenAspect / desiredAspect;
    }

    vec2 uv = (v_texcoord - 0.5) / boxScale + 0.5;
    if (uv.x < 0.0 || uv.x > 1.0 || uv.y < 0.0 || uv.y > 1.0) {
        fragColor = vec4(0.0, 0.0, 0.0, 1.0);
        return;
    }

    // 2. Native NES Coordinates
    vec2 nesDim = (u_crop_overscan == 1) ? vec2(256.0, 224.0) : vec2(256.0, 240.0);
    vec2 nesPixelCoord = floor(uv * nesDim);
    vec2 sampleUV = (nesPixelCoord + 0.5) / nesDim;

    // 3. Emulate 16x16 Attribute Block palette selection
    vec2 attrBlockCoord = floor(nesPixelCoord / 16.0);
    vec2 attrCenterUV = ((attrBlockCoord * 16.0) + 8.0) / nesDim;
    vec2 texel = 1.0 / nesDim;

    vec3 sC  = rgbToLab(texture(u_texture, attrCenterUV).rgb);
    vec3 sTL = rgbToLab(texture(u_texture, attrCenterUV - 6.0 * texel).rgb);
    vec3 sBR = rgbToLab(texture(u_texture, attrCenterUV + 6.0 * texel).rgb);

    // Build the 4-color sub-palette for this 16x16 attribute block
    int subPal[4];
    subPal[0] = 0; // Universal background (Black #000000)
    subPal[1] = findNearestNesLab(min(sC, min(sTL, sBR)));
    subPal[2] = findNearestNesLab(sC);
    subPal[3] = findNearestNesLab(max(sC, max(sTL, sBR)));

    // 4. Sample current pixel, apply Bayer dithering directly in sRGB before converting to LAB
    vec3 srcRgb = texture(u_texture, sampleUV).rgb;
    if (u_dither > 0.0) {
        float ditherOffset = bayer4x4(ivec2(nesPixelCoord)) * (u_dither * 0.18);
        srcRgb = clamp(srcRgb + vec3(ditherOffset), 0.0, 1.0);
    }
    vec3 srcLab = rgbToLab(srcRgb);

    // 5. Match against the 4-color sub-palette with CIEDE2000
    int finalIdx = findNearestSubPalette(srcLab, subPal);

    fragColor = vec4(NES_SRGB[finalIdx], 1.0);
}