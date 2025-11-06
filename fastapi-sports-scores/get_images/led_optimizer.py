#!/usr/bin/env python3

import requests
import os
import sys
import argparse
from PIL import Image
import math

# LED display optimization settings from get_images.py
GAMMA = 2.4
PASSTHROUGH = [(0, 0, 0)]  # Don't dither black

def process(filename, output_8_bit=True, passthrough=PASSTHROUGH, gentle_mode=False, preserve_mode=False):
    """Given a color image filename, load image and apply gamma correction
       and error-diffusion dithering while quantizing to 565 color
       resolution. If output_8_bit is True, image is reduced to 8-bit
       paletted mode after quantization/dithering. If passthrough (a list
       of 3-tuple RGB values) is provided, dithering won't be applied to
       colors in the provided list, they'll be quantized only (allows areas
       of the image to remain clean and dither-free). If gentle_mode is True,
       uses less aggressive processing to preserve detail. If preserve_mode is True,
       only does 565 quantization with minimal gamma adjustment.
    """
    img = Image.open(filename).convert('RGB')
    
    if preserve_mode:
        # Preserve mode: minimal processing, just 565 quantization with slight brightness boost
        print("Using preserve mode - minimal processing")
        for row in range(img.size[1]):
            for column in range(img.size[0]):
                pixel = img.getpixel((column, row))
                r, g, b = pixel
                
                # Slight brightness boost for LEDs (much gentler than gamma)
                r = min(255, int(r * 1.1))
                g = min(255, int(g * 1.1)) 
                b = min(255, int(b * 1.1))
                
                # Direct 565 quantization without dithering
                got = (r >> 3, g >> 2, b >> 3)
                rgb565 = ((got[0] << 3) | (got[0] >> 2),
                          (got[1] << 2) | (got[1] >> 4),
                          (got[2] << 3) | (got[2] >> 2))
                img.putpixel((column, row), rgb565)
    else:
        # Original processing with optional gentle mode
        err_next_pixel = (0, 0, 0)
        err_next_row = [(0, 0, 0) for _ in range(img.size[0])]
        
        # Adjust gamma for gentle mode
        gamma = 1.8 if gentle_mode else GAMMA
        
        for row in range(img.size[1]):
            for column in range(img.size[0]):
                pixel = img.getpixel((column, row))
                want = (math.pow(pixel[0] / 255.0, gamma) * 31.0,
                        math.pow(pixel[1] / 255.0, gamma) * 63.0,
                        math.pow(pixel[2] / 255.0, gamma) * 31.0)
                if pixel in passthrough:
                    got = (pixel[0] >> 3,
                           pixel[1] >> 2,
                           pixel[2] >> 3)
                else:
                    # Use less aggressive error diffusion in gentle mode
                    error_factor = 0.3 if gentle_mode else 0.5
                    row_factor = 0.15 if gentle_mode else 0.25
                    
                    got = (min(max(int(err_next_pixel[0] * error_factor +
                                       err_next_row[column][0] * row_factor +
                                       want[0] + 0.5), 0), 31),
                           min(max(int(err_next_pixel[1] * error_factor +
                                       err_next_row[column][1] * row_factor +
                                       want[1] + 0.5), 0), 63),
                           min(max(int(err_next_pixel[2] * error_factor +
                                       err_next_row[column][2] * row_factor +
                                       want[2] + 0.5), 0), 31))
                err_next_pixel = (want[0] - got[0],
                                  want[1] - got[1],
                                  want[2] - got[2])
                err_next_row[column] = err_next_pixel
                rgb565 = ((got[0] << 3) | (got[0] >> 2),
                          (got[1] << 2) | (got[1] >> 4),
                          (got[2] << 3) | (got[2] >> 2))
                img.putpixel((column, row), rgb565)

    if output_8_bit:
        try:
            img = img.convert('P', palette=Image.ADAPTIVE)
        except Exception as e:
            print(f"Warning: ColorConverter error, keeping RGB mode: {e}")
            # Keep as RGB instead of converting to palette mode

    img.save(filename.split('.')[0] + '.bmp')

def analyze_brightness(image_path):
    """Analyze the brightness of an image"""
    try:
        with Image.open(image_path) as img:
            # Convert to grayscale and get average brightness
            grayscale = img.convert('L')
            pixels = list(grayscale.getdata())
            avg_brightness = sum(pixels) / len(pixels)
            return avg_brightness
    except Exception as e:
        print(f"Error analyzing brightness: {e}")
        return None

def process_image_for_led(input_path, resize_to_32=True, backup_original=True, bg_color=(255, 255, 255), gentle_mode=False, preserve_mode=False):
    """Process any image file for LED display optimization"""
    
    if not os.path.exists(input_path):
        print(f"❌ Error: File not found: {input_path}")
        return False
    
    mode_text = " (preserve mode)" if preserve_mode else " (gentle mode)" if gentle_mode else ""
    print(f"Processing {input_path} for LED display{mode_text}...")
    
    try:
        # Get file info
        file_dir = os.path.dirname(input_path)
        file_name = os.path.basename(input_path)
        name_without_ext = os.path.splitext(file_name)[0]
        
        # Analyze original brightness
        original_brightness = analyze_brightness(input_path)
        if original_brightness:
            print(f"Original brightness: {original_brightness:.1f}/255")
        
        # Create backup if requested
        if backup_original:
            backup_path = os.path.join(file_dir, f"{name_without_ext}_original.bmp")
            if not os.path.exists(backup_path):
                with Image.open(input_path) as img:
                    img.save(backup_path)
                print(f"✓ Backup saved as {backup_path}")
        
        # Convert to PNG for processing (if not already)
        temp_png = os.path.join(file_dir, f"{name_without_ext}_temp.png")
        
        with Image.open(input_path) as img:
            # Resize if requested
            if resize_to_32 and img.size != (32, 32):
                print(f"Resizing from {img.size} to (32, 32)...")
                img = img.resize((32, 32), Image.Resampling.LANCZOS)
            
            # Convert to RGB if needed
            if img.mode != 'RGB':
                if img.mode in ('RGBA', 'LA'):
                    # Create background with specified color for transparency
                    background = Image.new('RGB', img.size, bg_color)
                    if img.mode == 'RGBA':
                        background.paste(img, mask=img.split()[-1])
                    else:
                        background.paste(img)
                    img = background
                    print(f"Applied background color: RGB{bg_color}")
                else:
                    img = img.convert('RGB')
            
            # Save as temporary PNG
            img.save(temp_png)
        
        if preserve_mode:
            processing_text = "Applying minimal processing (565 quantization + slight brightness boost)..."
        elif gentle_mode:
            processing_text = "Applying gentle gamma correction and light dithering..."
        else:
            processing_text = "Applying gamma correction and error-diffusion dithering..."
        print(processing_text)
        
        # Apply the LED optimization process with mode options
        process(temp_png, gentle_mode=gentle_mode, preserve_mode=preserve_mode)
        
        # The process function saves as temp_png.split('.')[0] + '.bmp'
        # So temp_png = "get_images/MONT_temp.png" becomes "get_images/MONT_temp.bmp"
        temp_bmp = temp_png.split('.')[0] + '.bmp'
        final_bmp = os.path.join(file_dir, f"{name_without_ext}.bmp")
        
        # Move the processed file to the correct final name
        if os.path.exists(temp_bmp):
            os.rename(temp_bmp, final_bmp)
        
        # Remove temporary PNG
        if os.path.exists(temp_png):
            os.remove(temp_png)
        
        # Check final result
        final_bmp = os.path.join(file_dir, f"{name_without_ext}.bmp")
        final_brightness = analyze_brightness(final_bmp)
        
        if final_brightness:
            print(f"Final brightness: {final_brightness:.1f}/255")
            if original_brightness and final_brightness:
                brightness_change = final_brightness - original_brightness
                if brightness_change > 5:
                    print(f"✓ Brightness increased by {brightness_change:.1f}")
                elif brightness_change < -5:
                    print(f"⚠️  Brightness decreased by {abs(brightness_change):.1f}")
                else:
                    print(f"→ Brightness change: {brightness_change:+.1f}")
        
        print(f"✓ Successfully processed {final_bmp} for LED display")
        return True
        
    except Exception as e:
        print(f"❌ Error processing image: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Process images for LED display optimization')
    parser.add_argument('input_path', help='Path to input image file')
    parser.add_argument('--no-resize', action='store_true', help='Skip resizing to 32x32')
    parser.add_argument('--no-backup', action='store_true', help='Skip creating backup of original')
    parser.add_argument('--bg-color', default='white', help='Background color for transparent images (white, black, or R,G,B values)')
    parser.add_argument('--gentle', action='store_true', help='Use gentle mode with less aggressive gamma/dithering for complex images')
    parser.add_argument('--preserve', action='store_true', help='Use preserve mode with minimal processing (565 quantization only)')
    
    args = parser.parse_args()
    
    # Parse background color
    if args.bg_color.lower() == 'white':
        bg_color = (255, 255, 255)
    elif args.bg_color.lower() == 'black':
        bg_color = (0, 0, 0)
    else:
        try:
            # Try to parse as R,G,B values
            rgb_values = [int(x.strip()) for x in args.bg_color.split(',')]
            if len(rgb_values) != 3 or any(x < 0 or x > 255 for x in rgb_values):
                raise ValueError
            bg_color = tuple(rgb_values)
        except ValueError:
            print(f"❌ Error: Invalid background color '{args.bg_color}'. Use 'white', 'black', or 'R,G,B' format.")
            sys.exit(1)
    
    success = process_image_for_led(
        args.input_path, 
        resize_to_32=not args.no_resize,
        backup_original=not args.no_backup,
        bg_color=bg_color,
        gentle_mode=args.gentle,
        preserve_mode=args.preserve
    )
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()