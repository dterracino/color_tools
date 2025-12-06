"""
Immutable color science constants from international standards.

These values are defined by CIE (International Commission on Illumination),
sRGB specification, and various color difference formulas. They should
never be modified as they represent fundamental color science.
"""

from __future__ import annotations
import json
import hashlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


class ColorConstants:
    """
    Immutable color science constants from international standards.
    
    These values are defined by CIE (International Commission on Illumination),
    sRGB specification, and various color difference formulas. They should
    never be modified as they represent fundamental color science.
    """
    
    # ===== D65 Standard Illuminant (CIE XYZ Reference White Point) =====
    # D65 represents average daylight with correlated color temperature of 6504K
    D65_WHITE_X = 95.047
    D65_WHITE_Y = 100.000
    D65_WHITE_Z = 108.883
    
    # ===== sRGB to XYZ Transformation Matrix (D65 Illuminant) =====
    # Linear RGB to XYZ conversion coefficients
    SRGB_TO_XYZ_R = (0.4124564, 0.3575761, 0.1804375)
    SRGB_TO_XYZ_G = (0.2126729, 0.7151522, 0.0721750)
    SRGB_TO_XYZ_B = (0.0193339, 0.1191920, 0.9503041)
    
    # ===== XYZ to sRGB Transformation Matrix (Inverse) =====
    XYZ_TO_SRGB_X = (3.2404542, -1.5371385, -0.4985314)
    XYZ_TO_SRGB_Y = (-0.9692660, 1.8760108, 0.0415560)
    XYZ_TO_SRGB_Z = (0.0556434, -0.2040259, 1.0572252)
    
    # ===== sRGB Gamma Correction (Companding) =====
    # sRGB uses a piecewise function for gamma encoding/decoding
    SRGB_GAMMA_THRESHOLD = 0.04045      # Crossover point for piecewise function
    SRGB_GAMMA_LINEAR_SCALE = 12.92     # Scale factor for linear segment
    SRGB_GAMMA_OFFSET = 0.055           # Offset for power function
    SRGB_GAMMA_DIVISOR = 1.055          # Divisor for power function
    SRGB_GAMMA_POWER = 2.4              # Gamma exponent
    
    # ===== Inverse sRGB Gamma (Linearization) =====
    SRGB_INV_GAMMA_THRESHOLD = 0.0031308  # Different threshold for inverse
    # Other constants same as forward direction
    
    # ===== CIE L*a*b* Color Space Constants =====
    LAB_DELTA = 6.0 / 29.0              # Delta constant (≈ 0.206897)
    LAB_KAPPA = 116.0                   # L* scale factor
    LAB_OFFSET = 16.0                   # L* offset
    LAB_A_SCALE = 500.0                 # a* scale factor
    LAB_B_SCALE = 200.0                 # b* scale factor
    
    # ===== Delta E 1994 (CIE94) Constants =====
    DE94_K1 = 0.045                     # Chroma weighting
    DE94_K2 = 0.015                     # Hue weighting
    
    # ===== Delta E 2000 (CIEDE2000) Constants =====
    # These are empirically derived for perceptual uniformity
    DE2000_POW7_BASE = 25.0             # Base for 25^7 calculation
    DE2000_HUE_OFFSET_1 = 30.0
    DE2000_HUE_WEIGHT_1 = 0.17
    DE2000_HUE_MULT_2 = 2.0
    DE2000_HUE_WEIGHT_2 = 0.24
    DE2000_HUE_MULT_3 = 3.0
    DE2000_HUE_OFFSET_3 = 6.0
    DE2000_HUE_WEIGHT_3 = 0.32
    DE2000_HUE_MULT_4 = 4.0
    DE2000_HUE_OFFSET_4 = 63.0
    DE2000_HUE_WEIGHT_4 = 0.20
    DE2000_DRO_MULT = 30.0
    DE2000_DRO_CENTER = 275.0
    DE2000_DRO_DIVISOR = 25.0
    DE2000_L_WEIGHT = 0.015
    DE2000_L_OFFSET = 50.0
    DE2000_L_DIVISOR = 20.0
    DE2000_C_WEIGHT = 0.045
    DE2000_H_WEIGHT = 0.015
    
    # ===== Delta E CMC Constants =====
    # Used in textile industry for color difference
    CMC_L_THRESHOLD = 16.0
    CMC_L_LOW = 0.511
    CMC_L_SCALE = 0.040975
    CMC_L_DIVISOR = 0.01765
    CMC_C_SCALE = 0.0638
    CMC_C_DIVISOR = 0.0131
    CMC_C_OFFSET = 0.638
    CMC_HUE_MIN = 164.0
    CMC_HUE_MAX = 345.0
    CMC_T_IN_RANGE = 0.56
    CMC_T_COS_MULT_IN = 0.2
    CMC_T_HUE_OFFSET_IN = 168.0
    CMC_T_OUT_RANGE = 0.36
    CMC_T_COS_MULT_OUT = 0.4
    CMC_T_HUE_OFFSET_OUT = 35.0
    CMC_F_POWER = 4.0
    CMC_F_DIVISOR = 1900.0
    
    # Default l:c ratios for CMC (2:1 for acceptability, 1:1 for perceptibility)
    CMC_L_DEFAULT = 2.0
    CMC_C_DEFAULT = 1.0
    
    # ===== Angle and Range Constants =====
    HUE_CIRCLE_DEGREES = 360.0          # Full circle for hue
    HUE_HALF_CIRCLE_DEGREES = 180.0     # Half circle
    RGB_MIN = 0                         # Minimum RGB value
    RGB_MAX = 255                       # Maximum RGB value (8-bit)
    NORMALIZED_MIN = 0.0                # Minimum normalized value
    NORMALIZED_MAX = 1.0                # Maximum normalized value
    XYZ_SCALE_FACTOR = 100.0            # XYZ typically scaled 0-100
    WIN_HSL_MAX = 240.0                 # Windows uses 0-240 for HSL
    
    # LAB color space value ranges (8-bit precision)
    AB_MIN = -128.0                     # Minimum a*/b* value
    AB_MAX = 127.0                      # Maximum a*/b* value
    CHROMA_MIN = 0.0                    # Minimum LCH chroma value
    CHROMA_MAX = 181.0                  # Maximum LCH chroma value (theoretical 8-bit sRGB gamut)
    
    # ===== Data File Paths =====
    # Default filenames for color and filament databases
    COLORS_JSON_FILENAME = "colors.json"
    FILAMENTS_JSON_FILENAME = "filaments.json"
    MAKER_SYNONYMS_JSON_FILENAME = "maker_synonyms.json"
    
    # Computed values (derived from above constants)
    LAB_DELTA_CUBED = LAB_DELTA ** 3
    LAB_F_SCALE = 3.0 * (LAB_DELTA ** 2)
    LAB_F_OFFSET = 4.0 / 29.0
    
    @classmethod
    def _compute_hash(cls) -> str:
        """
        Compute SHA-256 hash of all constant values for integrity checking.
        
        This creates a fingerprint of all the color science constants. If any
        constant is accidentally (or maliciously) modified, the hash won't match.
        """
        # Collect all UPPERCASE attributes (our constant naming convention)
        constants = {}
        for name in dir(cls):
            if name.isupper() and not name.startswith('_'):
                value = getattr(cls, name)
                # Convert tuples to lists for JSON serialization
                if isinstance(value, tuple):
                    value = list(value)
                constants[name] = value
        
        # Create stable JSON representation (sorted keys for consistency)
        data = json.dumps(constants, sort_keys=True)
        return hashlib.sha256(data.encode()).hexdigest()
    
    @classmethod
    def verify_integrity(cls) -> bool:
        """
        Verify that constants haven't been modified.
        
        Returns:
            True if all constants match expected values, False if tampered with.
        """
        return cls._compute_hash() == cls._EXPECTED_HASH
    
    # This hash is computed once when the constants are known to be correct
    # Computed hash of all color science constants (SHA-256)
    # NOTE: This hash is computed from the VALUES of all UPPERCASE constants
    # using the _compute_hash() method, NOT from the entire file contents.
    # To regenerate: python -c "from color_tools.constants import ColorConstants; print(ColorConstants._compute_hash())"
    # Updated 2025-12-03: Changed cyan/magenta colors, updated COLORS_JSON_HASH
    _EXPECTED_HASH = "2a42cc204ef7783eaa45199e837220a13decbcea967ab3e234421d16136c4522"
    
    # ========================================================================
    # Data File Integrity Hashes
    # ========================================================================
    # SHA-256 hashes of core data files for integrity verification
    # These hashes are computed from the exact file contents (including whitespace)
    # Updated 2025-12-03: Changed cyan to #00B7EB and magenta to #FF0090 to resolve RGB duplication with aqua/fuchsia
    
    COLORS_JSON_HASH = "dc8ce5769a2186008af540c03159d3f24a72e5effc9ce5b611c8b4374da19ffd"
    FILAMENTS_JSON_HASH = "cecec1bbd83712d5a183ca4c67de555465485170ebb317e60adf65022790f988"
    MAKER_SYNONYMS_JSON_HASH = "27488f9dfa37d661a0d5c0f73d1680aea22ab909f1c94fe1dd576b7902245c81"
    
    # Palette file hashes
    CGA4_PALETTE_HASH = "62624dbeef28b664feca10afe3901b52b2335395134aba88ea21f955f0d17b7d"
    CGA16_PALETTE_HASH = "d189b3004d20a343105d01b03c71d437077e34bb8d25fc074487c35c8490a329"
    COMMODORE64_PALETTE_HASH = "c4502abaed781535de55f3042cca4d7b3653c5eeb4cec3ecb30f591bfbfdfcca"
    EGA16_PALETTE_HASH = "d189b3004d20a343105d01b03c71d437077e34bb8d25fc074487c35c8490a329"
    EGA64_PALETTE_HASH = "2159e51f89cca4a4fb43a2d80bea030f3d7cd0cc5e1eacd25eb95f0ce2027e7f"
    GAMEBOY_PALETTE_HASH = "e2911baed15b4d56a27313b6be506c3a1f57bee3b01ecd2ca5995b512822da9b"
    GAMEBOY_DMG_PALETTE_HASH = "042d7cfd7b94f8719aa01603ddf5b0d9c73ae59b04e27295132ddac13142e968"
    GAMEBOY_GBL_PALETTE_HASH = "f2b6a573b09c1efa3529e79f281dcb0ed4e5c788cb10e51526c60e6e5d928231"
    GAMEBOY_MGB_PALETTE_HASH = "7c556e05e13adcfce0e7aec06ded6c7871acee63771e520319afa67e07080027"
    NES_PALETTE_HASH = "3021573a00b158fb6cf694e6546b236c2ec6862d52e08cc860f32d983e1f0a59"
    SMS_PALETTE_HASH = "95010c348c2f77a209544170da29ee7f5bfccacbcd32ed33c36cb7ef269f72e8"
    VGA_PALETTE_HASH = "9eb6055508d5523ceafbb4abe3d2921f09bc61b20485da1052e4d4fd653a5d00"
    VIRTUALBOY_PALETTE_HASH = "218854f6dc6506649e6ff14f92f56ff996b7c01a36c916b0374880c8524c40a9"
    WEB_PALETTE_HASH = "ba4ad53ece01d2f1338ae13221aa04e5c342519d7750d948458074001a465e7d"
    
    # User data files (optional, not verified)
    USER_COLORS_JSON_FILENAME = "user-colors.json"
    USER_FILAMENTS_JSON_FILENAME = "user-filaments.json"
    USER_SYNONYMS_JSON_FILENAME = "user-synonyms.json"
    
    # ========================================================================
    # Transformation Matrices Integrity Hash
    # ========================================================================
    # SHA-256 hash of transformation matrices from matrices.py module
    # This verifies the 6 CVD matrices haven't been modified
    # To regenerate: python -c "from color_tools.constants import ColorConstants; print(ColorConstants._compute_matrices_hash())"
    MATRICES_EXPECTED_HASH = "d177316ade5146a084bb5b92d693c3f9c62ec593fde9b6face567dbd8a633df5"
    
    @staticmethod
    def verify_data_file(filepath: Path, expected_hash: str) -> bool:
        """
        Verify integrity of a data file using SHA-256 hash.
        
        Args:
            filepath: Path to the data file to verify
            expected_hash: Expected SHA-256 hash of the file contents
            
        Returns:
            True if file hash matches expected hash, False otherwise
        """
        import hashlib
        from pathlib import Path
        
        if not Path(filepath).exists():
            return False
            
        with open(filepath, 'rb') as f:
            actual_hash = hashlib.sha256(f.read()).hexdigest()
        
        return actual_hash == expected_hash
    
    @classmethod
    def verify_all_data_files(cls, data_dir: Path | None = None) -> tuple[bool, list[str]]:
        """
        Verify integrity of all core data files.
        
        Args:
            data_dir: Directory containing data files. If None, uses package data directory.
            
        Returns:
            Tuple of (all_valid, list_of_errors)
            - all_valid: True if all files pass verification
            - list_of_errors: List of error messages for any failed verifications
        """
        from pathlib import Path
        
        if data_dir is None:
            # Use package data directory
            data_dir = Path(__file__).parent / "data"
        else:
            data_dir = Path(data_dir)
        
        errors = []
        
        # Verify colors.json
        colors_path = data_dir / cls.COLORS_JSON_FILENAME
        if not cls.verify_data_file(colors_path, cls.COLORS_JSON_HASH):
            errors.append(f"colors.json integrity check FAILED: {colors_path}")
        
        # Verify filaments.json
        filaments_path = data_dir / cls.FILAMENTS_JSON_FILENAME
        if not cls.verify_data_file(filaments_path, cls.FILAMENTS_JSON_HASH):
            errors.append(f"filaments.json integrity check FAILED: {filaments_path}")
        
        # Verify maker_synonyms.json
        synonyms_path = data_dir / cls.MAKER_SYNONYMS_JSON_FILENAME
        if not cls.verify_data_file(synonyms_path, cls.MAKER_SYNONYMS_JSON_HASH):
            errors.append(f"maker_synonyms.json integrity check FAILED: {synonyms_path}")
        
        # Verify palette files
        palettes_dir = data_dir / "palettes"
        palette_checks = [
            ("cga4.json", cls.CGA4_PALETTE_HASH),
            ("cga16.json", cls.CGA16_PALETTE_HASH),
            ("commodore64.json", cls.COMMODORE64_PALETTE_HASH),
            ("ega16.json", cls.EGA16_PALETTE_HASH),
            ("ega64.json", cls.EGA64_PALETTE_HASH),
            ("gameboy.json", cls.GAMEBOY_PALETTE_HASH),
            ("gameboy_dmg.json", cls.GAMEBOY_DMG_PALETTE_HASH),
            ("gameboy_gbl.json", cls.GAMEBOY_GBL_PALETTE_HASH),
            ("gameboy_mgb.json", cls.GAMEBOY_MGB_PALETTE_HASH),
            ("nes.json", cls.NES_PALETTE_HASH),
            ("sms.json", cls.SMS_PALETTE_HASH),
            ("vga.json", cls.VGA_PALETTE_HASH),
            ("virtualboy.json", cls.VIRTUALBOY_PALETTE_HASH),
            ("web.json", cls.WEB_PALETTE_HASH),
        ]
        
        for palette_file, expected_hash in palette_checks:
            palette_path = palettes_dir / palette_file
            if not cls.verify_data_file(palette_path, expected_hash):
                errors.append(f"{palette_file} integrity check FAILED: {palette_path}")
        
        return (len(errors) == 0, errors)
    
    @classmethod
    def _compute_matrices_hash(cls) -> str:
        """
        Compute SHA-256 hash of transformation matrices for integrity checking.
        
        This imports all matrices from matrices.py and creates a fingerprint.
        If any matrix values are modified, the hash won't match.
        
        ⚠️  When adding new matrices to matrices.py:
            1. Add the import here
            2. Add to matrices_dict below
            3. Regenerate MATRICES_EXPECTED_HASH
            4. Update _EXPECTED_HASH (you added a new constant)
        
        Returns:
            SHA-256 hash of all matrix values
        """
        from .matrices import (
            PROTANOPIA_SIMULATION,
            DEUTERANOPIA_SIMULATION,
            TRITANOPIA_SIMULATION,
            PROTANOPIA_CORRECTION,
            DEUTERANOPIA_CORRECTION,
            TRITANOPIA_CORRECTION,
        )
        
        # Collect all matrices in a stable order
        matrices_dict = {
            "PROTANOPIA_SIMULATION": PROTANOPIA_SIMULATION,
            "DEUTERANOPIA_SIMULATION": DEUTERANOPIA_SIMULATION,
            "TRITANOPIA_SIMULATION": TRITANOPIA_SIMULATION,
            "PROTANOPIA_CORRECTION": PROTANOPIA_CORRECTION,
            "DEUTERANOPIA_CORRECTION": DEUTERANOPIA_CORRECTION,
            "TRITANOPIA_CORRECTION": TRITANOPIA_CORRECTION,
        }
        
        # Convert tuples to lists for JSON serialization
        serializable = {}
        for name, matrix in matrices_dict.items():
            serializable[name] = [[float(val) for val in row] for row in matrix]
        
        # Create stable JSON representation
        data = json.dumps(serializable, sort_keys=True)
        return hashlib.sha256(data.encode()).hexdigest()
    
    @classmethod
    def verify_matrices_integrity(cls) -> bool:
        """
        Verify that transformation matrices haven't been modified.
        
        Returns:
            True if all matrices match expected values, False if tampered with.
        """
        if cls.MATRICES_EXPECTED_HASH == "TO_BE_COMPUTED":
            # Hash hasn't been set yet - skip verification
            return True
        return cls._compute_matrices_hash() == cls.MATRICES_EXPECTED_HASH


