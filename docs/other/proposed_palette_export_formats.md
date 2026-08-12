# Proposed New Palette Export Formats

This document collects the next wave of palette export formats proposed for `color_tools`, with emphasis on formats that add meaningful interoperability or make palettes directly usable in software, game-development, and shader workflows.

The existing exporter system remains centered around `PaletteExporter`, `ExporterMetadata`, `PaletteExportData`, `PaletteMetadata`, and typed per-export options derived from `ExportOptionsBase`.

---

## 1. Adobe ACO — Photoshop Color Swatch

**Suggested exporter name:** `aco`  
**Extension:** `.aco`  
**Type:** Binary  
**Priority:** High

Adobe ACO is one of the most useful remaining creative-tool palette formats to support. It complements ASE rather than replacing it.

ACO can represent multiple color models, including RGB, CMYK, Lab, grayscale, and others. Version 2 also supports color names. This makes it especially interesting for `color_tools`, because `ColorRecord` already contains richer color-space information than a simple RGB tuple.

### Potential export options

```python
@dataclass(slots=True)
class ACOExportOptions(ExportOptionsBase):
    color_space: Literal["rgb", "lab"] = "rgb"
    include_names: bool = True
```

Example:

```python
exporter = get_exporter("aco")

exporter.export_palette(
    palette,
    "palette.aco",
    options=ACOExportOptions(
        color_space="lab",
        include_names=True,
    ),
)
```

### Why it is useful

- Photoshop interoperability.
- Procreate can import ACO.
- Preserves richer color information than many palette formats.
- Provides a strong use case for the typed export-options architecture.

---

## 2. Adobe ACT — Adobe Color Table

**Suggested exporter name:** `act`  
**Extension:** `.act`  
**Type:** Binary  
**Priority:** High

ACT is a compact indexed-color palette format traditionally used by Adobe software.

It is primarily useful for palettes of up to 256 RGB colors and is a natural counterpart to the existing machine-oriented PNG LUT exporter.

```text
palette_lut.png    -> image-based palette lookup table
palette.act        -> traditional indexed Adobe color table
```

### Potential export options

```python
@dataclass(slots=True)
class ACTExportOptions(ExportOptionsBase):
    pad_to_256: bool = False
```

### Why it is useful

- Indexed-color workflows.
- Photoshop compatibility.
- Compact binary representation.
- Easy bridge between traditional graphics software and generated palettes.

---

## 3. Procreate Swatches

**Suggested exporter name:** `procreate_swatches`  
**Extension:** `.swatches`  
**Type:** Binary/container  
**Priority:** Medium

Procreate's native `.swatches` format is useful because Procreate is a major destination for illustrators and designers.

The format should be treated as a binary/container format rather than as a plain text palette.

Because Procreate already imports ASE and ACO, native `.swatches` support is not required for basic Procreate interoperability. It is therefore lower priority than ACO, but native support would still be valuable.

### Implementation caution

This should be implemented only after inspecting real Procreate-exported `.swatches` files and documenting the actual archive/container structure.

---

# Developer-Oriented Palette Formats

These formats turn a generated palette directly into code or GPU-ready data.

---

## 4. Generic Python

**Suggested exporter name:** `python`  
**Extension:** `.py`  
**Type:** Text  
**Priority:** Very High

A generic Python exporter should support several useful representations.

### Dictionary of RGB tuples

```python
PALETTE = {
    "medium_blue": (53, 105, 184),
    "muted_violet": (128, 88, 166),
    "dusty_magenta": (165, 72, 132),
}
```

### List of RGB tuples

```python
PALETTE = [
    (53, 105, 184),
    (128, 88, 166),
    (165, 72, 132),
]
```

### Named constants

```python
MEDIUM_BLUE = (53, 105, 184)
MUTED_VIOLET = (128, 88, 166)
DUSTY_MAGENTA = (165, 72, 132)
```

### Normalized floating-point values

```python
PALETTE = {
    "medium_blue": (0.207843, 0.411765, 0.721569),
    "muted_violet": (0.501961, 0.345098, 0.650980),
}
```

### Potential export options

```python
@dataclass(slots=True)
class PythonExportOptions(ExportOptionsBase):
    representation: Literal["dict", "list", "tuple", "constants"] = "dict"
    normalized: bool = False
    include_alpha: bool = False
    precision: int = 6
```

Example:

```python
exporter = get_exporter("python")

exporter.export_palette(
    palette,
    "palette.py",
    options=PythonExportOptions(
        representation="dict",
        normalized=False,
    ),
)
```

---

## 5. pygame Python

**Suggested exporter name:** `pygame`  
**Extension:** `.py`  
**Type:** Text  
**Priority:** High

pygame accepts ordinary RGB tuples almost everywhere, but an explicit pygame exporter can generate code tailored to pygame projects.

### Tuple representation

```python
PALETTE = {
    "medium_blue": (53, 105, 184),
    "muted_violet": (128, 88, 166),
}
```

### `pygame.Color` representation

```python
import pygame

PALETTE = {
    "medium_blue": pygame.Color(53, 105, 184),
    "muted_violet": pygame.Color(128, 88, 166),
}
```

### Potential export options

```python
@dataclass(slots=True)
class PygameExportOptions(ExportOptionsBase):
    representation: Literal["tuple", "color"] = "tuple"
    include_alpha: bool = False
```

---

## 6. NumPy

**Suggested exporter name:** `numpy`  
**Extension:** `.py`  
**Type:** Text  
**Priority:** Very High

A NumPy exporter is especially useful for image processing, LUT generation, GPU uploads, numerical operations, and batch color transformations.

### Unsigned 8-bit representation

```python
import numpy as np

PALETTE = np.array([
    [53, 105, 184],
    [128, 88, 166],
    [165, 72, 132],
], dtype=np.uint8)
```

### Normalized float representation

```python
import numpy as np

PALETTE = np.array([
    [0.207843, 0.411765, 0.721569],
    [0.501961, 0.345098, 0.650980],
    [0.647059, 0.282353, 0.517647],
], dtype=np.float32)
```

### Potential export options

```python
@dataclass(slots=True)
class NumPyExportOptions(ExportOptionsBase):
    normalized: bool = False
    include_alpha: bool = False
    dtype: Literal["uint8", "float32", "float64"] = "uint8"
    precision: int = 6
```

---

## 7. PyGLM

**Suggested exporter name:** `pyglm`  
**Extension:** `.py`  
**Type:** Text  
**Priority:** High

### `glm.vec3` palette

```python
import glm

PALETTE = [
    glm.vec3(0.207843, 0.411765, 0.721569),
    glm.vec3(0.501961, 0.345098, 0.650980),
    glm.vec3(0.647059, 0.282353, 0.517647),
]
```

### `glm.vec4` palette

```python
import glm

PALETTE = [
    glm.vec4(0.207843, 0.411765, 0.721569, 1.0),
    glm.vec4(0.501961, 0.345098, 0.650980, 1.0),
]
```

### Potential export options

```python
@dataclass(slots=True)
class PyGLMExportOptions(ExportOptionsBase):
    vector_size: Literal[3, 4] = 3
    precision: int = 6
```

---

# Shader-Oriented Formats

## 8. GLSL

**Suggested exporter name:** `glsl`  
**Extension:** `.glsl`  
**Type:** Text  
**Priority:** Very High

### Palette array

```glsl
const vec3 PALETTE[4] = vec3[](
    vec3(0.207843, 0.411765, 0.721569),
    vec3(0.501961, 0.345098, 0.650980),
    vec3(0.647059, 0.282353, 0.517647),
    vec3(0.698039, 0.266667, 0.360784)
);
```

### Named constants

```glsl
const vec3 MEDIUM_BLUE =
    vec3(0.207843, 0.411765, 0.721569);

const vec3 MUTED_VIOLET =
    vec3(0.501961, 0.345098, 0.650980);
```

### Array with names as comments

```glsl
const vec3 PALETTE[3] = vec3[](
    vec3(0.207843, 0.411765, 0.721569), // Medium Blue
    vec3(0.501961, 0.345098, 0.650980), // Muted Violet
    vec3(0.647059, 0.282353, 0.517647)  // Dusty Magenta
);
```

### Potential export options

```python
@dataclass(slots=True)
class GLSLExportOptions(ExportOptionsBase):
    representation: Literal["array", "constants"] = "array"
    vector_size: Literal[3, 4] = 3
    include_names: bool = True
    precision: int = 6
```

---

## 9. HLSL

**Suggested exporter name:** `hlsl`  
**Extension:** `.hlsl`  
**Type:** Text  
**Priority:** Medium

```hlsl
static const float3 Palette[] = {
    float3(0.207843, 0.411765, 0.721569),
    float3(0.501961, 0.345098, 0.650980),
    float3(0.647059, 0.282353, 0.517647),
};
```

### Potential export options

```python
@dataclass(slots=True)
class HLSLExportOptions(ExportOptionsBase):
    representation: Literal["array", "constants"] = "array"
    vector_size: Literal[3, 4] = 3
    include_names: bool = True
    precision: int = 6
```

---

## 10. WGSL

**Suggested exporter name:** `wgsl`  
**Extension:** `.wgsl`  
**Type:** Text  
**Priority:** Medium

```wgsl
const PALETTE = array<vec3<f32>, 3>(
    vec3<f32>(0.207843, 0.411765, 0.721569),
    vec3<f32>(0.501961, 0.345098, 0.650980),
    vec3<f32>(0.647059, 0.282353, 0.517647),
);
```

---

# GPU / Binary Formats

## 11. Raw GPU Palette Buffer

**Suggested exporter name:** `gpu_buffer`  
**Extension:** `.bin`  
**Type:** Binary  
**Priority:** High for engine/tooling use

Possible layouts:

```text
RGB8
RGBA8
RGB32F
RGBA32F
```

### Potential export options

```python
@dataclass(slots=True)
class GPUBufferExportOptions(ExportOptionsBase):
    format: Literal[
        "rgb8",
        "rgba8",
        "rgb32f",
        "rgba32f",
    ] = "rgb32f"
```

This could be uploaded directly into a UBO, SSBO, texture buffer, or other GPU resource with little or no parsing.

---

# Additional Developer / Design-System Formats

## 12. SCSS

**Suggested exporter name:** `scss`  
**Extension:** `.scss`  
**Type:** Text  
**Priority:** Medium

```scss
$medium-blue: #3569B8;
$muted-violet: #8058A6;
$dusty-magenta: #A54884;
```

Or:

```scss
$palette: (
    "medium-blue": #3569B8,
    "muted-violet": #8058A6,
    "dusty-magenta": #A54884,
);
```

---

## 13. Less

**Suggested exporter name:** `less`  
**Extension:** `.less`  
**Type:** Text  
**Priority:** Low to Medium

```less
@medium-blue: #3569B8;
@muted-violet: #8058A6;
@dusty-magenta: #A54884;
```

---

## 14. Tailwind / JavaScript / TypeScript Palette

**Suggested exporter name:** `tailwind`  
**Extension:** `.js` or `.ts`  
**Type:** Text  
**Priority:** Medium

```javascript
export const palette = {
    mediumBlue: "#3569B8",
    mutedViolet: "#8058A6",
    dustyMagenta: "#A54884",
};
```

Tailwind-oriented variant:

```javascript
export const colors = {
    "medium-blue": "#3569B8",
    "muted-violet": "#8058A6",
    "dusty-magenta": "#A54884",
};
```

---

## 15. C / C++ Header

**Suggested exporter name:** `c_header`  
**Extension:** `.h`  
**Type:** Text  
**Priority:** Medium

### Floating-point palette

```c
static const float palette[][3] = {
    {0.207843f, 0.411765f, 0.721569f},
    {0.501961f, 0.345098f, 0.650980f},
    {0.647059f, 0.282353f, 0.517647f},
};
```

### Integer palette

```c
static const unsigned char palette[][3] = {
    {53, 105, 184},
    {128, 88, 166},
    {165, 72, 132},
};
```

---

# Recommended Implementation Order

1. **Python**
2. **NumPy**
3. **pygame**
4. **PyGLM**
5. **GLSL**
6. **ACO**
7. **ACT**
8. **Raw GPU Buffer**
9. **HLSL**
10. **WGSL**
11. **SCSS**
12. **Tailwind / JavaScript / TypeScript**
13. **C/C++**
14. **Procreate `.swatches`**
15. **Less**

The first five provide immediate value for Python, game, and shader development and exercise the typed export-options system particularly well.

---

# Importer Compatibility Goal

These formats should eventually participate in the same general interchange pipeline as traditional palette formats:

```text
Any supported format
        ↓
      Import
        ↓
PaletteExportData
        ↓
      Export
        ↓
Any supported target format
```

Examples:

```text
ASE       -> Python
GPL       -> GLSL
KPL       -> NumPy
Paint.NET -> pygame
Lospec    -> PyGLM
ACO       -> Swatch PNG
Python    -> ASE
GLSL      -> GPL
```

For real palette formats such as ASE, GPL, KPL, ACO, and ACT, importers should parse the actual external format.

For code-oriented formats such as Python and GLSL, future importers should support the canonical structures emitted by `color_tools` rather than attempting to parse arbitrary source code.

For Python specifically, a future importer should use `ast` and accept only safe literal structures. It should never execute imported palette source with `exec()`.

---

# Architectural Principle

```text
PaletteMetadata
      ↓
PaletteExportData
      ↓
PaletteExporter.export_palette(...)

ExportOptionsBase
      ↓
Format-specific options
      ↓
PaletteExporter.export_palette(..., options=...)
```

Palette data describes **what the palette is**.

Export options describe **how a particular exporter should serialize or present it**.

This allows the registry to continue constructing stateless exporters while still supporting highly configurable output formats.
