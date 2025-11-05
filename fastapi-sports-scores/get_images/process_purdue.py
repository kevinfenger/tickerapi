#!/usr/bin/env python3

import requests
import os
from PIL import Image
import math

# Copy the process function from get_images.py
GAMMA = 2.4
PASSTHROUGH = [(0, 0, 0)]  # Don't dither black

def process(filename, output_8_bit=True, passthrough=PASSTHROUGH):
    """Given a color image filename, load image and apply gamma correction
       and error-diffusion dithering while quantizing to 565 color
       resolution. If output_8_bit is True, image is reduced to 8-bit
       paletted mode after quantization/dithering. If passthrough (a list
       of 3-tuple RGB values) is provided, dithering won't be applied to
       colors in the provided list, they'll be quantized only (allows areas
       of the image to remain clean and dither-free).
    """
    img = Image.open(filename).convert('RGB')
    err_next_pixel = (0, 0, 0)
    err_next_row = [(0, 0, 0) for _ in range(img.size[0])]
    for row in range(img.size[1]):
        for column in range(img.size[0]):
            pixel = img.getpixel((column, row))
            want = (math.pow(pixel[0] / 255.0, GAMMA) * 31.0,
                    math.pow(pixel[1] / 255.0, GAMMA) * 63.0,
                    math.pow(pixel[2] / 255.0, GAMMA) * 31.0)
            if pixel in passthrough:
                got = (pixel[0] >> 3,
                       pixel[1] >> 2,
                       pixel[2] >> 3)
            else:
                got = (min(max(int(err_next_pixel[0] * 0.5 +
                                   err_next_row[column][0] * 0.25 +
                                   want[0] + 0.5), 0), 31),
                       min(max(int(err_next_pixel[1] * 0.5 +
                                   err_next_row[column][1] * 0.25 +
                                   want[1] + 0.5), 0), 63),
                       min(max(int(err_next_pixel[2] * 0.5 +
                                   err_next_row[column][2] * 0.25 +
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
        img = img.convert('P', palette=Image.ADAPTIVE)

    img.save(filename.split('.')[0] + '.bmp')

def download_and_process_purdue():
    """Download Purdue logo and process it like get_images.py does"""
    
    logo_url = "https://a.espncdn.com/i/teamlogos/ncaa/500/2509.png"
    college_dir = "/app/get_images/sport_logos/college"
    
    print(f"Downloading Purdue logo from {logo_url}")
    
    try:
        # Download the logo
        img_path_png = os.path.join(college_dir, "PUR.png")
        response = requests.get(logo_url, stream=True)
        if response.status_code != 200:
            print(f"Failed to download logo: HTTP {response.status_code}")
            return False
            
        with open(img_path_png, 'wb') as file:
            for chunk in response.iter_content(chunk_size=1024):
                file.write(chunk)

        print("Downloaded PNG, resizing to 32x32...")
        
        # Open, resize, and save the image with PIL (same as get_images.py)
        with Image.open(img_path_png) as the_img:
            img_resized = the_img.resize((32, 32))
            img_resized.save(img_path_png)
            
            print("Processing with gamma correction and dithering...")
            process(img_path_png)

        # Delete the original .png file (same as get_images.py)
        os.remove(img_path_png)
        
        print(f"✓ Successfully processed PUR.bmp with LED display optimization")
        return True
        
    except Exception as e:
        print(f"Error processing logo: {e}")
        return False

def main():
    print("Downloading and processing Purdue logo (team ID 2509) with LED display optimization...")
    success = download_and_process_purdue()
    
    if success:
        print("✓ Purdue logo processed successfully with same method as get_images.py!")
    else:
        print("❌ Failed to process Purdue logo")

if __name__ == "__main__":
    main()