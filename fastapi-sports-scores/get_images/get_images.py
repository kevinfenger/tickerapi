# SPDX-FileCopyrightText: 2023 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# Written by Liz Clark (Adafruit Industries) with OpenAI ChatGPT v4 Aug 3rd, 2023 build
# https://help.openai.com/en/articles/6825453-chatgpt-release-notes

# https://chat.openai.com/share/2fabba2b-3f17-4ab6-a4d9-58206a3b9916

# process() function originally written by Phil B. for Adafruit Industries
# https://raw.githubusercontent.com/adafruit/Adafruit_Media_Converters/master/protomatter_dither.py

import os
import math
import requests
from PIL import Image

# the name of the sports you want to follow
sport_names = ["football", "baseball", "soccer", "hockey", "basketball", "basketball", "football"]
# the name of the corresponding leages you want to follow
sport_leagues = ["nfl", "mlb", "usa.1", "nhl", "nba", "mens-college-basketball", "college-football"]
# directory to match CircuitPython code folder names
bitmap_directories = ["team0_logos", "team1_logos", "team2_logos", "team3_logos", "team4_logos", "team5_logos", "team6_logos"]

# Constants and function for image processing
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

# Create a base directory to store the logos if it doesn't exist
base_dir = 'sport_logos'
if not os.path.exists(base_dir):
    os.makedirs(base_dir)

def download_and_process_logo(abbreviation, logo_url, sport_dir, league_name):
    """Download and process a single team logo"""
    try:
        print(f"Downloading logo for {abbreviation} from {league_name}...")
        
        img_path_png = os.path.join(sport_dir, f"{abbreviation}.png")
        response = requests.get(logo_url, stream=True)
        if response.status_code != 200:
            print(f"Failed to download logo for {abbreviation}")
            return False
            
        with open(img_path_png, 'wb') as file:
            for chunk in response.iter_content(chunk_size=1024):
                file.write(chunk)

        # Open, resize, and save the image with PIL
        with Image.open(img_path_png) as the_img:
            img_resized = the_img.resize((32, 32))
            img_resized.save(img_path_png)
            process(img_path_png)

        # Delete the original .png file
        os.remove(img_path_png)
        return True
    except Exception as e:
        print(f"Error processing logo for {abbreviation}: {e}")
        return False

def get_college_teams(sport, league, sport_dir):
    """Get college teams by iterating through team IDs 1-800"""
    print(f"Fetching college teams for {league} (checking IDs 1-800)...")
    team_count = 0
    
    for team_id in range(1, 801):
        try:
            url = f"https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/teams/{team_id}"
            response = requests.get(url)
            
            if response.status_code == 200:
                data = response.json()
                team_data = data.get('team', {})
                
                if team_data and 'abbreviation' in team_data and 'logos' in team_data:
                    abbreviation = team_data['abbreviation']
                    logos = team_data.get('logos', [])
                    
                    if logos and len(logos) > 0:
                        logo_url = logos[0]['href']
                        if download_and_process_logo(abbreviation, logo_url, sport_dir, league):
                            team_count += 1
                            
        except Exception as e:
            # Continue to next team ID on any error
            continue
            
        # Print progress every 100 teams
        if team_id % 100 == 0:
            print(f"Checked {team_id}/800 team IDs, found {team_count} teams so far...")
    
    print(f"Completed {league}: found {team_count} teams total")

def get_pro_teams(sport, league, sport_dir):
    """Get professional teams using the teams endpoint"""
    try:
        url = f"https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/teams"
        response = requests.get(url)
        
        if response.status_code != 200:
            print(f"Failed to fetch teams for {league}")
            return
            
        data = response.json()
        teams = data.get('sports', [{}])[0].get('leagues', [{}])[0].get('teams', [])
        
        for team in teams:
            team_data = team['team']
            abbreviation = team_data['abbreviation']
            logo_url = team_data['logos'][0]['href']
            download_and_process_logo(abbreviation, logo_url, sport_dir, league)
            
    except Exception as e:
        print(f"Error fetching professional teams for {league}: {e}")

# Loop through each league to get the teams
for i in range(len(sport_leagues)):
    sport = sport_names[i]
    league = sport_leagues[i]

    # Create a directory for the current sport if it doesn't exist
    sport_dir = os.path.join(base_dir, bitmap_directories[i])
    if not os.path.exists(sport_dir):
        os.makedirs(sport_dir)

    # Handle college sports differently (iterate through team IDs)
    if league in ['mens-college-basketball', 'college-football']:
        get_college_teams(sport, league, sport_dir)
    else:
        # Handle professional sports (use teams endpoint)
        get_pro_teams(sport, league, sport_dir)

print("All logos have been downloaded, processed, and resized!")