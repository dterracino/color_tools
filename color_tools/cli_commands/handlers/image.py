"""
Image processing command handler.

Handles all image subcommands: cvd (simulation/correction), quantize, watermark, etc.
"""

import sys
from pathlib import Path

# Image analysis is optional (requires Pillow)
try:
    from ...image import (
        extract_unique_colors,
        redistribute_luminance,
        format_color_change_report,
        simulate_cvd_image,
        correct_cvd_image,
        quantize_image_to_palette,
        add_text_watermark,
        add_image_watermark,
        add_svg_watermark,
        convert_image,
    )
    IMAGE_AVAILABLE = True
except ImportError:
    IMAGE_AVAILABLE = False

from ...palette import load_palette


def handle_image_command(args):
    """Handle all image processing commands."""
    if not IMAGE_AVAILABLE:
        print("Error: Image processing requires Pillow", file=sys.stderr)
        print("Install with: pip install color-match-tools[image]", file=sys.stderr)
        sys.exit(1)
    
    # Handle --list-palettes first (doesn not require file)
    if args.list_palettes:
        try:
            palettes_dir = Path(__file__).parent.parent.parent / "data" / "palettes"
            available = sorted([p.stem for p in palettes_dir.glob("*.json")])
            print("Available retro palettes:")
            for palette_name in available:
                try:
                    pal = load_palette(palette_name)
                    print(f"  {palette_name:<15} - {len(pal.records)} colors")
                except Exception:
                    print(f"  {palette_name:<15} - (error loading)")
        except Exception as e:
            print(f"Error listing palettes: {e}", file=sys.stderr)
            sys.exit(1)
        sys.exit(0)
    
    # Check if file is provided and exists for operations that need it
    if not args.file:
        print("Error: --file is required for this operation", file=sys.stderr)
        sys.exit(1)
    
    image_path = Path(args.file)
    if not image_path.exists():
        print(f"Error: Image file not found: {image_path}", file=sys.stderr)
        sys.exit(1)
    
    # Determine output path
    output_path = args.output
    
    # Count active operations
    operations = [
        args.redistribute_luminance,
        args.cvd_simulate is not None,
        args.cvd_correct is not None,
        args.quantize_palette is not None,
        args.watermark,
        args.convert is not None,
    ]
    active_count = sum(operations)
    
    if active_count == 0:
        print("Error: No operation specified. Choose one of:", file=sys.stderr)
        print("  --redistribute-luminance    (HueForge color analysis)", file=sys.stderr)
        print("  --cvd-simulate TYPE         (colorblindness simulation)", file=sys.stderr)
        print("  --cvd-correct TYPE          (colorblindness correction)", file=sys.stderr)
        print("  --quantize-palette NAME     (convert to retro palette)", file=sys.stderr)
        print("  --watermark                 (add text/image/SVG watermark with --watermark-text/--watermark-image/--watermark-svg)", file=sys.stderr)
        print("  --convert FORMAT            (convert image format: png, jpg, webp, heic, avif, etc.)", file=sys.stderr)
        print("  --list-palettes             (show available palettes)", file=sys.stderr)
        sys.exit(1)
    elif active_count > 1:
        print("Error: Only one operation allowed at a time", file=sys.stderr)
        sys.exit(1)
    
    # Execute the requested operation
    try:
        if args.redistribute_luminance:
            # HueForge luminance redistribution (existing functionality)
            print(f"Extracting {args.colors} unique colors from {image_path.name}...")
            colors = extract_unique_colors(str(image_path), n_colors=args.colors)
            print(f"Extracted {len(colors)} colors")
            
            # Redistribute luminance
            changes = redistribute_luminance(colors)
            
            # Display report
            report = format_color_change_report(changes)
            print(report)
        
        elif args.cvd_simulate:
            # CVD simulation
            print(f"Simulating {args.cvd_simulate} for {image_path.name}...")
            sim_image = simulate_cvd_image(str(image_path), args.cvd_simulate, output_path)
            
            if output_path:
                print(f"CVD simulation saved to: {output_path}")
            else:
                # Generate default output name
                default_output = image_path.with_name(f"{image_path.stem}_{args.cvd_simulate}_sim{image_path.suffix}")
                sim_image.save(default_output)
                print(f"CVD simulation saved to: {default_output}")
        
        elif args.cvd_correct:
            # CVD correction
            print(f"Applying {args.cvd_correct} correction to {image_path.name}...")
            corrected_image = correct_cvd_image(str(image_path), args.cvd_correct, output_path)
            
            if output_path:
                print(f"CVD correction saved to: {output_path}")
            else:
                # Generate default output name
                default_output = image_path.with_name(f"{image_path.stem}_{args.cvd_correct}_corrected{image_path.suffix}")
                corrected_image.save(default_output)
                print(f"CVD correction saved to: {default_output}")
        
        elif args.quantize_palette:
            # Palette quantization
            dither_text = " with dithering" if args.dither else ""
            print(f"Converting {image_path.name} to {args.quantize_palette} palette{dither_text}...")
            print(f"Using {args.metric} distance metric")
            
            # Load palette info for reporting
            try:
                palette_info = load_palette(args.quantize_palette)
                print(f"Target palette: {len(palette_info.records)} colors")
            except Exception as e:
                print(f"Warning: Could not load palette info: {e}", file=sys.stderr)
            
            quantized_image = quantize_image_to_palette(
                str(image_path), 
                args.quantize_palette,
                metric=args.metric,
                dither=args.dither,
                output_path=output_path
            )
            
            if output_path:
                print(f"Quantized image saved to: {output_path}")
            else:
                # Generate default output name
                dither_suffix = "_dithered" if args.dither else ""
                default_output = image_path.with_name(f"{image_path.stem}_{args.quantize_palette}{dither_suffix}{image_path.suffix}")
                quantized_image.save(default_output)
                print(f"Quantized image saved to: {default_output}")
        
        elif args.watermark:
            # Watermarking
            from PIL import Image
            
            # Check that at least one watermark source is specified
            watermark_sources = [args.watermark_text, args.watermark_image, args.watermark_svg]
            if not any(watermark_sources):
                print("Error: Watermark requires one of: --watermark-text, --watermark-image, or --watermark-svg", file=sys.stderr)
                sys.exit(1)
            
            # Check for conflicting watermark sources
            source_count = sum(bool(s) for s in watermark_sources)
            if source_count > 1:
                print("Error: Only one watermark source allowed (--watermark-text, --watermark-image, or --watermark-svg)", file=sys.stderr)
                sys.exit(1)
            
            # Load input image
            print(f"Loading image: {image_path.name}...")
            img = Image.open(str(image_path))
            
            # Apply appropriate watermark type
            if args.watermark_text:
                # Parse color arguments
                try:
                    color_parts = args.watermark_color.split(',')
                    color = tuple(int(c.strip()) for c in color_parts)
                    if len(color) != 3:
                        raise ValueError("Color must have 3 components (R,G,B)")
                except Exception as e:
                    print(f"Error: Invalid --watermark-color format: {e}", file=sys.stderr)
                    print("Use format: R,G,B (e.g., 255,255,255)", file=sys.stderr)
                    sys.exit(1)
                
                stroke_color = None
                if args.watermark_stroke_color:
                    try:
                        stroke_parts = args.watermark_stroke_color.split(',')
                        stroke_color = tuple(int(c.strip()) for c in stroke_parts)
                        if len(stroke_color) != 3:
                            raise ValueError("Stroke color must have 3 components (R,G,B)")
                    except Exception as e:
                        print(f"Error: Invalid --watermark-stroke-color format: {e}", file=sys.stderr)
                        print("Use format: R,G,B (e.g., 0,0,0)", file=sys.stderr)
                        sys.exit(1)
                
                print(f"Adding text watermark: '{args.watermark_text}'")
                watermarked = add_text_watermark(
                    img,
                    text=args.watermark_text,
                    position=args.watermark_position,
                    font_name=args.watermark_font_name,
                    font_file=args.watermark_font_file,
                    font_size=args.watermark_font_size,
                    color=color,
                    opacity=args.watermark_opacity,
                    stroke_color=stroke_color,
                    stroke_width=args.watermark_stroke_width,
                    margin=args.watermark_margin
                )
            
            elif args.watermark_image:
                print(f"Adding image watermark: {Path(args.watermark_image).name}")
                watermarked = add_image_watermark(
                    img,
                    watermark_path=args.watermark_image,
                    position=args.watermark_position,
                    scale=args.watermark_scale,
                    opacity=args.watermark_opacity,
                    margin=args.watermark_margin
                )
            
            elif args.watermark_svg:
                print(f"Adding SVG watermark: {Path(args.watermark_svg).name}")
                try:
                    watermarked = add_svg_watermark(
                        img,
                        svg_path=args.watermark_svg,
                        position=args.watermark_position,
                        scale=args.watermark_scale,
                        opacity=args.watermark_opacity,
                        margin=args.watermark_margin
                    )
                except ImportError as e:
                    print(f"Error: {e}", file=sys.stderr)
                    sys.exit(1)
            
            # Save watermarked image
            if output_path:
                # Convert RGBA to RGB if saving as JPEG
                if output_path.lower().endswith(('.jpg', '.jpeg')) and watermarked.mode == 'RGBA':
                    # Create white background
                    rgb_img = Image.new('RGB', watermarked.size, (255, 255, 255))
                    rgb_img.paste(watermarked, mask=watermarked.split()[3])  # Use alpha channel as mask
                    watermarked = rgb_img
                
                watermarked.save(output_path)
                print(f"Watermarked image saved to: {output_path}")
            else:
                # Generate default output name
                default_output = image_path.with_name(f"{image_path.stem}_watermarked{image_path.suffix}")
                
                # Convert RGBA to RGB if saving as JPEG
                if default_output.suffix.lower() in ['.jpg', '.jpeg'] and watermarked.mode == 'RGBA':
                    rgb_img = Image.new('RGB', watermarked.size, (255, 255, 255))
                    rgb_img.paste(watermarked, mask=watermarked.split()[3])
                    watermarked = rgb_img
                
                watermarked.save(default_output)
                print(f"Watermarked image saved to: {default_output}")
        
        elif args.convert:
            # Image format conversion
            from PIL import Image
            
            # Determine lossless setting for WebP/AVIF
            lossless = None if args.lossy else None  # Will use format defaults
            if args.convert.lower() in ('webp', 'avif') and not args.lossy:
                lossless = True  # Force lossless unless --lossy is specified
            
            print(f"Converting {image_path.name} to {args.convert.upper()}...")
            
            try:
                output_file = convert_image(
                    input_path=image_path,
                    output_path=output_path,
                    output_format=args.convert,
                    quality=args.quality,
                    lossless=lossless
                )
                print(f"Converted image saved to: {output_file}")
            except ImportError as e:
                print(f"Error: {e}", file=sys.stderr)
                print("For HEIC support, install: pip install pillow-heif", file=sys.stderr)
                sys.exit(1)
    
    except Exception as e:
        print(f"Error processing image: {e}", file=sys.stderr)
        sys.exit(1)
