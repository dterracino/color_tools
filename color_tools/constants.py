"""
Immutable color science constants from international standards.

These values are defined by CIE (International Commission on Illumination),
sRGB specification, and various color difference formulas. They should
never be modified as they represent fundamental color science.
"""

from __future__ import annotations
import json
import hashlib
from typing import TYPE_CHECKING, cast

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
    WIN_HSL_MAX = 240.0                 # Windows uses 0-240 for HSL (legacy — use WIN_HSL240_* below)
    WIN_HSL240_HUE_MAX = 239            # winHSL240: hue max (240 wraps to 0°, so valid range is 0–239)
    WIN_HSL240_SL_MAX = 240             # winHSL240: saturation / lightness max (Windows Paint, Win32 GDI)
    WIN_HSL255_HUE_MAX = 254            # winHSL255: hue max (same reason; used by Microsoft Office)
    WIN_HSL255_SL_MAX = 255             # winHSL255: saturation / lightness max (Microsoft Office)
    
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
        constants: dict[str, object] = {}
        for name in dir(cls):
            if name.isupper() and not name.startswith('_'):
                value = getattr(cls, name)
                # Convert tuples to lists for JSON serialization
                if isinstance(value, tuple):
                    value = list(cast(tuple[object, ...], value))
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
        from ._integrity_hashes import COLOR_CONSTANTS_EXPECTED_HASH

        return cls._compute_hash() == COLOR_CONSTANTS_EXPECTED_HASH

    @classmethod
    def expected_hash(cls) -> str:
        """Return the expected integrity hash for the color constants."""
        from ._integrity_hashes import COLOR_CONSTANTS_EXPECTED_HASH

        return COLOR_CONSTANTS_EXPECTED_HASH

    @classmethod
    def compute_hash(cls) -> str:
        """Compute the current integrity hash for the color constants."""
        return cls._compute_hash()
    
    # User data files (optional, not verified) - now in user/ subdirectory
    USER_COLORS_JSON_FILENAME = "user/user-colors.json"
    USER_FILAMENTS_JSON_FILENAME = "user/user-filaments.json"
    USER_SYNONYMS_JSON_FILENAME = "user/user-synonyms.json"
    OWNED_FILAMENTS_JSON_FILENAME = "user/owned-filaments.json"
    
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
            content = f.read().replace(b'\r\n', b'\n')
        actual_hash = hashlib.sha256(content).hexdigest()

        return actual_hash == expected_hash

    @classmethod
    def _registered_palette_hashes(cls) -> tuple[tuple[str, str], ...]:
        """Return registered system palette filenames and expected hashes."""
        from ._integrity_hashes import SYSTEM_PALETTE_HASHES

        return tuple(SYSTEM_PALETTE_HASHES.items())

    @classmethod
    def registered_palette_count(cls) -> int:
        """Return the number of system palettes registered for verification."""
        return len(cls._registered_palette_hashes())
    
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

        from ._integrity_hashes import CORE_DATA_HASHES
        
        errors: list[str] = []
        
        # Verify colors.json
        colors_path = data_dir / cls.COLORS_JSON_FILENAME
        if not cls.verify_data_file(colors_path, CORE_DATA_HASHES[cls.COLORS_JSON_FILENAME]):
            errors.append(f"colors.json integrity check FAILED: {colors_path}")
        
        # Verify filaments.json
        filaments_path = data_dir / cls.FILAMENTS_JSON_FILENAME
        if not cls.verify_data_file(
            filaments_path,
            CORE_DATA_HASHES[cls.FILAMENTS_JSON_FILENAME],
        ):
            errors.append(f"filaments.json integrity check FAILED: {filaments_path}")
        
        # Verify maker_synonyms.json
        synonyms_path = data_dir / cls.MAKER_SYNONYMS_JSON_FILENAME
        if not cls.verify_data_file(
            synonyms_path,
            CORE_DATA_HASHES[cls.MAKER_SYNONYMS_JSON_FILENAME],
        ):
            errors.append(f"maker_synonyms.json integrity check FAILED: {synonyms_path}")
        
        # Verify palette files
        palettes_dir = data_dir / "palettes"
        for palette_file, expected_hash in cls._registered_palette_hashes():
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
            3. Regenerate the integrity manifest
        
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
            ALL_SIMULATION,
            ALL_CORRECTION,
        )
        
        # Collect all matrices in a stable order
        matrices_dict = {
            "PROTANOPIA_SIMULATION": PROTANOPIA_SIMULATION,
            "DEUTERANOPIA_SIMULATION": DEUTERANOPIA_SIMULATION,
            "TRITANOPIA_SIMULATION": TRITANOPIA_SIMULATION,
            "PROTANOPIA_CORRECTION": PROTANOPIA_CORRECTION,
            "DEUTERANOPIA_CORRECTION": DEUTERANOPIA_CORRECTION,
            "TRITANOPIA_CORRECTION": TRITANOPIA_CORRECTION,
            "ALL_SIMULATION": ALL_SIMULATION,
            "ALL_CORRECTION": ALL_CORRECTION,
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
        from ._integrity_hashes import MATRICES_EXPECTED_HASH

        return cls._compute_matrices_hash() == MATRICES_EXPECTED_HASH

    @classmethod
    def compute_matrices_hash(cls) -> str:
        """Compute the current integrity hash for the transformation matrices."""
        return cls._compute_matrices_hash()
    
    @classmethod
    def generate_user_data_hash(cls, file_path: "Path | str") -> str:
        """
        Generate SHA-256 hash for a user data file.
        
        Args:
            file_path: Path to user data file
            
        Returns:
            SHA-256 hash of the file contents
            
        Raises:
            FileNotFoundError: If file doesn't exist
        """
        from pathlib import Path
        
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"User data file not found: {path}")
        
        content = path.read_bytes().replace(b'\r\n', b'\n')
        return hashlib.sha256(content).hexdigest()
    
    @classmethod
    def save_user_data_hash(cls, file_path: "Path | str", hash_value: str | None = None) -> "Path":
        """
        Save SHA-256 hash for a user data file to a .sha256 file.
        
        Args:
            file_path: Path to user data file
            hash_value: Optional pre-computed hash. If None, will compute from file.
            
        Returns:
            Path to the created .sha256 file
            
        Raises:
            FileNotFoundError: If file doesn't exist
        """
        from pathlib import Path
        
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"User data file not found: {path}")
        
        if hash_value is None:
            hash_value = cls.generate_user_data_hash(path)
        
        hash_file = path.with_suffix(path.suffix + ".sha256")
        hash_file.write_text(f"{hash_value}  {path.name}\n")
        
        return hash_file
    
    @classmethod
    def verify_user_data_file(cls, file_path: "Path | str") -> tuple[bool, str | None]:
        """
        Verify user data file against its .sha256 file if it exists.
        
        Args:
            file_path: Path to user data file
            
        Returns:
            Tuple of (is_valid, error_message)
            - is_valid: True if file is valid or no hash file exists
            - error_message: None if valid, error description if invalid
        """
        from pathlib import Path
        
        path = Path(file_path)
        if not path.exists():
            return False, f"User data file not found: {path}"
        
        hash_file = path.with_suffix(path.suffix + ".sha256")
        if not hash_file.exists():
            # No hash file means no verification required
            return True, None
        
        try:
            hash_content = hash_file.read_text().strip()
            # Extract hash from "hash  filename" format
            expected_hash = hash_content.split()[0] if hash_content else ""
            
            actual_hash = cls.generate_user_data_hash(path)
            
            if actual_hash == expected_hash:
                return True, None
            else:
                return False, f"Hash mismatch for {path.name}: expected {expected_hash[:8]}..., got {actual_hash[:8]}..."
                
        except Exception as e:
            return False, f"Error verifying {path.name}: {e}"
    
    @classmethod
    def verify_all_user_data(cls, data_dir: "Path | str | None" = None) -> tuple[bool, list[str]]:
        """
        Verify integrity of all user data files in the user/ subdirectory.
        
        Only files with corresponding .sha256 files are verified.
        
        Args:
            data_dir: Optional custom data directory. If None, uses package data directory.
            
        Returns:
            Tuple of (all_valid, list_of_errors)
            - all_valid: True if all files with hash files pass verification
            - list_of_errors: List of error messages for any failed verifications
        """
        from pathlib import Path
        
        if data_dir is None:
            # Use package data directory
            data_dir = Path(__file__).parent / "data"
        else:
            data_dir = Path(data_dir)
        
        user_dir = data_dir / "user"
        if not user_dir.exists():
            # No user directory means no user files to verify
            return True, []
        
        errors: list[str] = []
        
        # Check all user data files
        user_files = [
            cls.USER_COLORS_JSON_FILENAME,
            cls.USER_FILAMENTS_JSON_FILENAME,
            cls.USER_SYNONYMS_JSON_FILENAME
        ]
        
        for filename in user_files:
            file_path = data_dir / filename
            if file_path.exists():
                is_valid, error_msg = cls.verify_user_data_file(file_path)
                if not is_valid and error_msg:
                    errors.append(error_msg)

        # User palette examples are templates, not active palettes.
        from ._palette_utils import get_palette_files

        user_palettes_dir = data_dir / "user" / "palettes"
        for palette_path in get_palette_files(user_palettes_dir, "user-*.json"):
            is_valid, error_msg = cls.verify_user_data_file(palette_path)
            if not is_valid and error_msg:
                errors.append(error_msg)
        
        return (len(errors) == 0, errors)


