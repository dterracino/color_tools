"""
Tests for color_tools/image/basic.py — transform functions and dependency paths.

Covers:
- transform_image()
- simulate_cvd_image()
- correct_cvd_image()
- quantize_image_to_palette()
- _check_dependencies / _check_basic_dependencies / _check_noise_dependencies ImportError paths
- is_indexed_mode() PILLOW_AVAILABLE=False path
- analyze_noise_level sigma branches (iterable, scalar, noisy assessment)
"""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# Availability flags
# ---------------------------------------------------------------------------

def _pil_available():
    try:
        from PIL import Image  # noqa: F401
        return True
    except ImportError:
        return False


def _numpy_available():
    try:
        import numpy  # noqa: F401
        return True
    except ImportError:
        return False


def _skimage_available():
    try:
        from skimage import restoration  # noqa: F401
        return True
    except ImportError:
        return False


PIL_AVAILABLE = _pil_available()
NUMPY_AVAILABLE = _numpy_available()
SKIMAGE_AVAILABLE = _skimage_available()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_temp_rgb_image(size=(8, 8), color=(100, 150, 200)) -> str:
    """Create a temporary solid-colour RGB PNG and return its path."""
    from PIL import Image
    fd, path = tempfile.mkstemp(suffix='.png')
    os.close(fd)
    img = Image.new('RGB', size, color)
    img.save(path)
    return path


def _make_temp_multicolor_image(size=(8, 8), seed=42) -> str:
    """Create a temporary PNG with many distinct (random) pixel colors."""
    import random
    from PIL import Image
    random.seed(seed)
    fd, path = tempfile.mkstemp(suffix='.png')
    os.close(fd)
    img = Image.new('RGB', size)
    pixels = [
        (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
        for _ in range(size[0] * size[1])
    ]
    img.putdata(pixels)
    img.save(path)
    return path


# ---------------------------------------------------------------------------
# TestTransformImage
# ---------------------------------------------------------------------------

@unittest.skipUnless(PIL_AVAILABLE and NUMPY_AVAILABLE, 'Requires Pillow and numpy')
class TestTransformImage(unittest.TestCase):
    """Tests for transform_image()."""

    def setUp(self):
        self._files: list[str] = []

    def tearDown(self):
        for f in self._files:
            if os.path.exists(f):
                os.remove(f)

    def _tmp_path(self, suffix='.png') -> str:
        fd, path = tempfile.mkstemp(suffix=suffix)
        os.close(fd)
        self._files.append(path)
        return path

    def _img(self, **kw) -> str:
        p = _make_temp_rgb_image(**kw)
        self._files.append(p)
        return p

    def _identity(self, rgb):
        return rgb

    # --- basic behaviour ---

    def test_identity_returns_pil_image(self):
        """An identity transform returns a PIL Image of the same size."""
        from color_tools.image.basic import transform_image
        result = transform_image(self._img(size=(4, 4)), self._identity)
        import PIL.Image
        self.assertIsInstance(result, PIL.Image.Image)
        self.assertEqual(result.size, (4, 4))

    def test_transform_modifies_pixels(self):
        """A transform that inverts colours actually changes pixel values."""
        from color_tools.image.basic import transform_image

        def invert(rgb):
            return (255 - rgb[0], 255 - rgb[1], 255 - rgb[2])

        img_path = self._img(size=(4, 4), color=(100, 100, 100))
        result = transform_image(img_path, invert)
        pixel = result.getpixel((0, 0))
        assert isinstance(pixel, tuple)
        r, g, b = pixel[:3]
        self.assertEqual((r, g, b), (155, 155, 155))

    def test_saves_to_output_path(self):
        """transform_image saves result when output_path is provided."""
        from color_tools.image.basic import transform_image
        out = self._tmp_path()
        transform_image(self._img(size=(4, 4)), self._identity, output_path=out)
        self.assertGreater(os.path.getsize(out), 0)

    def test_nonexistent_file_raises_file_not_found(self):
        """Passing a non-existent path raises FileNotFoundError."""
        from color_tools.image.basic import transform_image
        with self.assertRaises(FileNotFoundError):
            transform_image('/nonexistent/__nope__.png', self._identity)

    # --- image-mode handling ---

    def test_rgba_preserves_alpha(self):
        """RGBA image's alpha channel is preserved by default."""
        from PIL import Image
        from color_tools.image.basic import transform_image

        fd, path = tempfile.mkstemp(suffix='.png')
        os.close(fd)
        self._files.append(path)
        Image.new('RGBA', (4, 4), (100, 150, 200, 128)).save(path)

        result = transform_image(path, self._identity, preserve_alpha=True)
        pixel = result.getpixel((0, 0))
        assert isinstance(pixel, tuple)
        self.assertEqual(len(pixel), 4, 'Expected RGBA output')
        self.assertEqual(pixel[3], 128, 'Alpha should be preserved')

    def test_palette_mode_image_is_processed(self):
        """A palette-mode (P) image is accepted and processed."""
        from PIL import Image
        from color_tools.image.basic import transform_image
        import PIL.Image

        fd, path = tempfile.mkstemp(suffix='.png')
        os.close(fd)
        self._files.append(path)
        Image.new('RGB', (4, 4), (100, 150, 200)).convert('P').save(path)

        result = transform_image(path, self._identity)
        self.assertIsInstance(result, PIL.Image.Image)

    def test_grayscale_image_is_processed(self):
        """A grayscale (L) image is accepted and processed."""
        from PIL import Image
        from color_tools.image.basic import transform_image
        import PIL.Image

        fd, path = tempfile.mkstemp(suffix='.png')
        os.close(fd)
        self._files.append(path)
        Image.new('L', (4, 4), 128).save(path)

        result = transform_image(path, self._identity)
        self.assertIsInstance(result, PIL.Image.Image)


# ---------------------------------------------------------------------------
# TestSimulateCvdImage
# ---------------------------------------------------------------------------

@unittest.skipUnless(PIL_AVAILABLE and NUMPY_AVAILABLE, 'Requires Pillow and numpy')
class TestSimulateCvdImage(unittest.TestCase):
    """Tests for simulate_cvd_image()."""

    def setUp(self):
        self._files: list[str] = []

    def tearDown(self):
        for f in self._files:
            if os.path.exists(f):
                os.remove(f)

    def _img(self) -> str:
        p = _make_temp_rgb_image(size=(4, 4))
        self._files.append(p)
        return p

    def test_protanopia_returns_pil_image(self):
        """simulate_cvd_image returns a PIL Image for protanopia."""
        from color_tools.image.basic import simulate_cvd_image
        import PIL.Image
        result = simulate_cvd_image(self._img(), 'protanopia')
        self.assertIsInstance(result, PIL.Image.Image)
        self.assertEqual(result.size, (4, 4))

    def test_deuteranopia_returns_pil_image(self):
        """simulate_cvd_image works for deuteranopia."""
        from color_tools.image.basic import simulate_cvd_image
        import PIL.Image
        p = _make_temp_rgb_image(size=(4, 4), color=(200, 50, 50))
        self._files.append(p)
        result = simulate_cvd_image(p, 'deuteranopia')
        self.assertIsInstance(result, PIL.Image.Image)

    def test_saves_to_output_path(self):
        """simulate_cvd_image saves image when output_path is given."""
        from color_tools.image.basic import simulate_cvd_image
        fd, out = tempfile.mkstemp(suffix='.png')
        os.close(fd)
        self._files.append(out)
        simulate_cvd_image(self._img(), 'protanopia', output_path=out)
        self.assertGreater(os.path.getsize(out), 0)


# ---------------------------------------------------------------------------
# TestCorrectCvdImage
# ---------------------------------------------------------------------------

@unittest.skipUnless(PIL_AVAILABLE and NUMPY_AVAILABLE, 'Requires Pillow and numpy')
class TestCorrectCvdImage(unittest.TestCase):
    """Tests for correct_cvd_image()."""

    def setUp(self):
        self._files: list[str] = []

    def tearDown(self):
        for f in self._files:
            if os.path.exists(f):
                os.remove(f)

    def _img(self) -> str:
        p = _make_temp_rgb_image(size=(4, 4))
        self._files.append(p)
        return p

    def test_protanopia_correction_returns_pil_image(self):
        """correct_cvd_image returns a PIL Image."""
        from color_tools.image.basic import correct_cvd_image
        import PIL.Image
        result = correct_cvd_image(self._img(), 'protanopia')
        self.assertIsInstance(result, PIL.Image.Image)

    def test_saves_to_output_path(self):
        """correct_cvd_image saves result when output_path is provided."""
        from color_tools.image.basic import correct_cvd_image
        fd, out = tempfile.mkstemp(suffix='.png')
        os.close(fd)
        self._files.append(out)
        correct_cvd_image(self._img(), 'protanopia', output_path=out)
        self.assertGreater(os.path.getsize(out), 0)


# ---------------------------------------------------------------------------
# TestQuantizeImageToPalette
# ---------------------------------------------------------------------------

@unittest.skipUnless(PIL_AVAILABLE and NUMPY_AVAILABLE, 'Requires Pillow and numpy')
class TestQuantizeImageToPalette(unittest.TestCase):
    """Tests for quantize_image_to_palette()."""

    def setUp(self):
        self._files: list[str] = []

    def tearDown(self):
        for f in self._files:
            if os.path.exists(f):
                os.remove(f)

    def _low_color_img(self) -> str:
        """Image with only 2 distinct colors — exercises the direct-mapping path."""
        from PIL import Image
        fd, path = tempfile.mkstemp(suffix='.png')
        os.close(fd)
        self._files.append(path)
        img = Image.new('RGB', (4, 4))
        img.putdata([(0, 0, 0)] * 8 + [(255, 255, 255)] * 8)
        img.save(path)
        return path

    def _high_color_img(self) -> str:
        """Image with many distinct colors — exercises the k-means path."""
        p = _make_temp_multicolor_image(size=(8, 8))
        self._files.append(p)
        return p

    # --- direct-mapping path (source colors <= palette size) ---

    def test_low_color_direct_mapping_returns_pil_image(self):
        """< palette_size unique colors → direct mapping, returns PIL Image."""
        from color_tools.image.basic import quantize_image_to_palette
        import PIL.Image
        result = quantize_image_to_palette(self._low_color_img(), 'cga4')
        self.assertIsInstance(result, PIL.Image.Image)
        self.assertEqual(result.size, (4, 4))

    # --- k-means path (source colors > palette size) ---

    def test_high_color_kmeans_returns_pil_image(self):
        """Many unique colors → k-means reduction, returns PIL Image."""
        from color_tools.image.basic import quantize_image_to_palette
        import PIL.Image
        result = quantize_image_to_palette(self._high_color_img(), 'cga4')
        self.assertIsInstance(result, PIL.Image.Image)

    # --- dithering ---

    def test_dither_low_color_returns_pil_image(self):
        """dither=True with a low-color image runs Floyd-Steinberg on direct mapping."""
        from color_tools.image.basic import quantize_image_to_palette
        import PIL.Image
        result = quantize_image_to_palette(self._low_color_img(), 'cga4', dither=True)
        self.assertIsInstance(result, PIL.Image.Image)

    def test_dither_high_color_returns_pil_image(self):
        """dither=True with a high-color image runs Floyd-Steinberg on k-means."""
        from color_tools.image.basic import quantize_image_to_palette
        import PIL.Image
        result = quantize_image_to_palette(self._high_color_img(), 'cga4', dither=True)
        self.assertIsInstance(result, PIL.Image.Image)

    # --- output_path ---

    def test_saves_to_output_path(self):
        """quantize_image_to_palette saves result when output_path is provided."""
        from color_tools.image.basic import quantize_image_to_palette
        fd, out = tempfile.mkstemp(suffix='.png')
        os.close(fd)
        self._files.append(out)
        quantize_image_to_palette(self._high_color_img(), 'cga4', output_path=out)
        self.assertGreater(os.path.getsize(out), 0)

    def test_dither_saves_to_output_path(self):
        """dither=True also saves when output_path is provided."""
        from color_tools.image.basic import quantize_image_to_palette
        fd, out = tempfile.mkstemp(suffix='.png')
        os.close(fd)
        self._files.append(out)
        quantize_image_to_palette(self._high_color_img(), 'cga4', dither=True, output_path=out)
        self.assertGreater(os.path.getsize(out), 0)

    # --- error cases ---

    def test_invalid_palette_raises_value_error(self):
        """An unknown palette name raises ValueError."""
        from color_tools.image.basic import quantize_image_to_palette
        p = _make_temp_rgb_image(size=(4, 4))
        self._files.append(p)
        with self.assertRaises(ValueError):
            quantize_image_to_palette(p, 'nonexistent_palette_xyz_abc')

    def test_nonexistent_image_raises_file_not_found(self):
        """A missing image raises FileNotFoundError."""
        from color_tools.image.basic import quantize_image_to_palette
        with self.assertRaises(FileNotFoundError):
            quantize_image_to_palette('/nonexistent/__nope__.png', 'cga4')


# ---------------------------------------------------------------------------
# TestDependencyErrorPaths
# ---------------------------------------------------------------------------

class TestDependencyErrorPaths(unittest.TestCase):
    """Tests that ImportError is raised when dependencies are unavailable."""

    def test_check_dependencies_no_pillow(self):
        """_check_dependencies raises ImportError when Pillow flag is False."""
        import color_tools.image.basic as mod
        with patch.object(mod, 'PILLOW_AVAILABLE', False):
            with self.assertRaises(ImportError) as ctx:
                mod._check_dependencies()
        self.assertIn('Pillow', str(ctx.exception))

    def test_check_dependencies_no_numpy(self):
        """_check_dependencies raises ImportError when numpy flag is False."""
        import color_tools.image.basic as mod
        with patch.object(mod, 'NUMPY_AVAILABLE', False):
            with self.assertRaises(ImportError) as ctx:
                mod._check_dependencies()
        self.assertIn('numpy', str(ctx.exception))

    def test_check_basic_dependencies_no_pillow(self):
        """_check_basic_dependencies raises ImportError when Pillow is unavailable."""
        import color_tools.image.basic as mod
        with patch.object(mod, 'PILLOW_AVAILABLE', False):
            with self.assertRaises(ImportError):
                mod._check_basic_dependencies()

    def test_check_basic_dependencies_no_numpy(self):
        """_check_basic_dependencies raises ImportError when numpy is unavailable."""
        import color_tools.image.basic as mod
        with patch.object(mod, 'NUMPY_AVAILABLE', False):
            with self.assertRaises(ImportError):
                mod._check_basic_dependencies()

    def test_check_noise_dependencies_no_skimage(self):
        """_check_noise_dependencies raises ImportError when scikit-image flag is False."""
        import color_tools.image.basic as mod
        with patch.object(mod, 'SCIKIT_IMAGE_AVAILABLE', False):
            with self.assertRaises(ImportError) as ctx:
                mod._check_noise_dependencies()
        self.assertIn('scikit-image', str(ctx.exception))

    def test_is_indexed_mode_no_pillow(self):
        """is_indexed_mode raises ImportError when PILLOW_AVAILABLE is False."""
        import color_tools.image.basic as mod
        with patch.object(mod, 'PILLOW_AVAILABLE', False):
            with self.assertRaises(ImportError):
                mod.is_indexed_mode('any_path.png')


# ---------------------------------------------------------------------------
# TestAnalyzeNoiseSigmaBranches
# ---------------------------------------------------------------------------

@unittest.skipUnless(
    PIL_AVAILABLE and NUMPY_AVAILABLE and SKIMAGE_AVAILABLE,
    'Requires Pillow, numpy, and scikit-image',
)
class TestAnalyzeNoiseSigmaBranches(unittest.TestCase):
    """Tests for the sigma-handling branches inside analyze_noise_level."""

    def setUp(self):
        self._files: list[str] = []

    def tearDown(self):
        for f in self._files:
            if os.path.exists(f):
                os.remove(f)

    def _img(self, size=(16, 16)) -> str:
        p = _make_temp_rgb_image(size=size)
        self._files.append(p)
        return p

    def test_sigma_iterable_triggers_mean_and_noisy(self):
        """When estimate_sigma returns a list, sigma is averaged; 'noisy' if > threshold."""
        import color_tools.image.basic as mod
        with patch.object(mod.restoration, 'estimate_sigma', return_value=[5.0, 5.0, 5.0]):
            result = mod.analyze_noise_level(self._img())
        self.assertEqual(result['assessment'], 'noisy')
        self.assertAlmostEqual(float(result['noise_sigma']), 5.0, places=3)

    def test_sigma_scalar_used_directly_and_noisy(self):
        """When estimate_sigma returns a scalar, it is converted directly; 'noisy' if > threshold."""
        import color_tools.image.basic as mod
        with patch.object(mod.restoration, 'estimate_sigma', return_value=5.0):
            result = mod.analyze_noise_level(self._img())
        self.assertEqual(result['assessment'], 'noisy')
        self.assertAlmostEqual(float(result['noise_sigma']), 5.0, places=3)

    def test_low_sigma_gives_clean_assessment(self):
        """Sigma below threshold yields 'clean' assessment."""
        import color_tools.image.basic as mod
        with patch.object(mod.restoration, 'estimate_sigma', return_value=0.5):
            result = mod.analyze_noise_level(self._img())
        self.assertEqual(result['assessment'], 'clean')


if __name__ == '__main__':
    unittest.main()
