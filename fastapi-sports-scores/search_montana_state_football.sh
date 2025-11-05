#!/bin/bash

echo "🔍 Searching ESPN groups 1-180 for Montana State college football..."
echo "================================================================"

montana_state_groups=()

for group in {1..180}; do
    echo -n "Testing group $group... "
    
    # Make the API call and check for Montana State
    result=$(curl -s "https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard?groups=$group" | grep -i "montana state")
    
    if [ -n "$result" ]; then
        echo "✅ FOUND Montana State!"
        montana_state_groups+=($group)
        
        # Get more details about the games
        echo "   Games found:"
        curl -s "https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard?groups=$group" | grep -i "montana state" -A 3 -B 3 | head -10
        echo ""
    else
        echo "❌ No Montana State"
    fi
    
    # Small delay to be respectful to ESPN's API
    sleep 0.1
done

echo ""
echo "================================================================"
echo "🏈 SUMMARY: Montana State found in groups: ${montana_state_groups[*]}"
echo "Total groups with Montana State: ${#montana_state_groups[@]}"