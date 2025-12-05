#!/usr/bin/env python3

import requests
import os
import sys
import argparse
import math
from urllib.parse import urlparse, parse_qs
from PIL import Image

# Constants and function for image processing (from get_images.py)
GAMMA = 2.6

PASSTHROUGH = ((0, 0, 0),
               (255, 0, 0),
               (255, 255, 0),
               (0, 255, 0),
               (0, 255, 255),
               (0, 0, 255),
               (255, 0, 255),
               (255, 255, 255))

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

def fetch_teams_from_espn_url(espn_url):
    """Fetch team data from ESPN scoreboard API URL"""
    print(f"Fetching teams from: {espn_url}")
    
    try:
        response = requests.get(espn_url)
        if response.status_code != 200:
            print(f"Failed to fetch data from ESPN API: {response.status_code}")
            return []
            
        data = response.json()
        events = data.get('events', [])
        teams = set()  # Use set to avoid duplicates
        
        # Extract teams from all events/games
        for event in events:
            competitions = event.get('competitions', [])
            for competition in competitions:
                competitors = competition.get('competitors', [])
                for competitor in competitors:
                    team_data = competitor.get('team', {})
                    if team_data:
                        # Try both 'logo' (single) and 'logos' (array) formats
                        logo_url = team_data.get('logo', '')
                        if not logo_url and team_data.get('logos'):
                            logo_url = team_data.get('logos', [{}])[0].get('href', '')
                        
                        teams.add((
                            team_data.get('abbreviation', 'UNK'),
                            team_data.get('displayName', 'Unknown Team'),
                            logo_url
                        ))
        
        # Convert set back to list of dicts
        team_list = []
        for abbr, name, logo_url in teams:
            if logo_url:  # Only include teams with logos
                team_list.append({
                    'abbreviation': abbr,
                    'name': name,
                    'logo_url': logo_url
                })
        
        print(f"Found {len(team_list)} teams with logos")
        return team_list
        
    except Exception as e:
        print(f"Error fetching teams: {e}")
        return []

def download_and_process_team_logo(team_data, output_dir):
    """Download a team logo and process it using the proven process() function"""
    abbr = team_data['abbreviation']
    name = team_data['name']
    logo_url = team_data['logo_url']
    
    print(f"Processing {name} ({abbr})...")
    
    try:
        # Create temp PNG path
        temp_png = os.path.join(output_dir, f"{abbr}.png")
        
        # Download the logo
        response = requests.get(logo_url, stream=True)
        if response.status_code != 200:
            print(f"  ❌ Failed to download logo for {abbr}")
            return False
            
        # Save temporary PNG
        with open(temp_png, 'wb') as file:
            for chunk in response.iter_content(chunk_size=1024):
                file.write(chunk)
        
        # Resize to 32x32 for LED display
        with Image.open(temp_png) as img:
            img_resized = img.resize((32, 32), Image.Resampling.LANCZOS)
            img_resized.save(temp_png)
        
        # Process through the proven process() function
        # This will create a .bmp file automatically
        process(temp_png)
        
        # Clean up temp PNG file
        if os.path.exists(temp_png):
            os.remove(temp_png)
        
        # Check if BMP was created successfully
        final_bmp = os.path.join(output_dir, f"{abbr}.bmp")
        if os.path.exists(final_bmp):
            print(f"  ✅ Successfully processed {abbr} → {final_bmp}")
            return True
        else:
            print(f"  ❌ Failed to create BMP for {abbr}")
            return False
            
    except Exception as e:
        print(f"  ❌ Error processing {abbr}: {e}")
        return False

def determine_output_directory(espn_url):
    """Determine output directory name from ESPN URL"""
    try:
        # Parse URL to extract sport, league, and group info
        parsed = urlparse(espn_url)
        path_parts = parsed.path.split('/')
        
        # Extract sport and league from path like /apis/site/v2/sports/football/college-football/scoreboard
        if len(path_parts) >= 7:
            sport = path_parts[5]  # football, basketball, etc.
            league = path_parts[6]  # college-football, nfl, etc.
        else:
            sport = "unknown"
            league = "unknown"
        
        # Extract group ID if present
        query_params = parse_qs(parsed.query)
        group_id = query_params.get('groups', [''])[0]
        
        # Create directory name
        if group_id:
            dir_name = f"{sport}_{league}_group_{group_id}"
        else:
            dir_name = f"{sport}_{league}_all"
            
        return f"sport_logos/{dir_name}"
        
    except Exception as e:
        print(f"Warning: Could not parse URL for directory name: {e}")
        return "sport_logos/espn_teams"

def download_single_logo(logo_url, team_abbr, team_name, output_dir):
    """Download and process a single logo from a direct URL"""
    team_data = {
        'abbreviation': team_abbr,
        'name': team_name,
        'logo_url': logo_url
    }
    return download_and_process_team_logo(team_data, output_dir)

def main():
    parser = argparse.ArgumentParser(description="Fetch team logos from ESPN API URL or process individual logo URLs")
    parser.add_argument("input_url", help="ESPN API URL to fetch teams from, OR direct logo image URL")
    parser.add_argument("--output-dir", help="Custom output directory (optional)")
    parser.add_argument("--team-abbr", help="Team abbreviation (required when using direct logo URL)")
    parser.add_argument("--team-name", help="Team name (optional, defaults to abbreviation)")
    
    args = parser.parse_args()
    
    input_url = args.input_url
    
    # Check if this is a direct image URL or ESPN API URL
    is_direct_image = input_url.endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg'))
    
    if is_direct_image:
        # Handle single logo download
        if not args.team_abbr:
            print("Error: --team-abbr is required when using direct logo URLs")
            return 1
        
        team_abbr = args.team_abbr
        team_name = args.team_name or team_abbr
        
        # Determine output directory
        output_dir = args.output_dir or "/tmp/logo_temp"
        
        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            print(f"Created directory: {output_dir}")
        
        print("🎯 Processing Single Logo")
        print("=" * 40)
        print(f"Logo URL: {input_url}")
        print(f"Team: {team_name} ({team_abbr})")
        print(f"Output: {output_dir}")
        print("=" * 40)
        
        success = download_single_logo(input_url, team_abbr, team_name, output_dir)
        
        if success:
            print(f"✅ Successfully processed logo for {team_abbr}")
            print(f"📁 File saved: {output_dir}/{team_abbr}.bmp")
            return 0
        else:
            print(f"❌ Failed to process logo for {team_abbr}")
            return 1
    
    else:
        # Handle ESPN API URL (original functionality)
        espn_url = input_url
        
        # Determine output directory
        if args.output_dir:
            output_dir = args.output_dir
        else:
            output_dir = determine_output_directory(espn_url)
        
        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            print(f"Created directory: {output_dir}")
        
        print("🏈 Fetching Teams from ESPN API")
        print("=" * 60)
        print(f"URL: {espn_url}")
        print(f"Output: {output_dir}")
        print(f"Processing: Using proven process() function from get_images.py")
        print("=" * 60)
        
        # Fetch teams from ESPN API
        teams = fetch_teams_from_espn_url(espn_url)
    
    if not teams:
        print("No teams found or error occurred")
        return 1
    
    print(f"\nProcessing {len(teams)} teams through LED optimizer...")
    print("-" * 60)
    
    success_count = 0
    for team in teams:
        if download_and_process_team_logo(team, output_dir):
            success_count += 1
    
    print("-" * 60)
    print(f"✅ Successfully processed {success_count}/{len(teams)} team logos")
    print(f"📁 Output directory: {output_dir}")
    
    # List the created files
    if success_count > 0:
        print(f"\nCreated BMP files:")
        for filename in sorted(os.listdir(output_dir)):
            if filename.endswith('.bmp'):
                print(f"  • {filename}")
    
    return 0 if success_count > 0 else 1

if __name__ == "__main__":
    sys.exit(main())