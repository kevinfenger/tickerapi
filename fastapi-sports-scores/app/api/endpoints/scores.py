from fastapi import APIRouter, HTTPException, Query, Request
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
from app.services.espn_service import ESPNService
from app.core.cache import Cache

router = APIRouter()
espn_service = ESPNService()
cache = Cache()

def get_sport_priority(sport: str) -> int:
    """Define sport priority for grouping (lower number = higher priority)"""
    sport_priorities = {
        'basketball/mens-college-basketball': 1,  # CBB first
        'basketball/nba': 2,                      # NBA second
        'football/college-football': 3,           # College Football
        'football/nfl': 4,                        # NFL
        'hockey/nhl': 5,                          # NHL
        'baseball/mlb': 6,                        # MLB
        'soccer/eng.1': 7,                        # Soccer leagues
        'soccer/usa.1': 8,
    }
    return sport_priorities.get(sport, 999)  # Default high number for unknown sports

def is_game_in_live_window(game_date: datetime, status: str, current_time: datetime, tight_window: bool = False, collection_mode: bool = False) -> bool:
    """
    Check if a game should be included in the live endpoint.
    
    Args:
        game_date: The game's start time (UTC)
        status: The game's status (e.g., 'final', 'scheduled', 'in progress')
        current_time: Current UTC time
        tight_window: If True, use a much tighter time window for prioritizing results
        collection_mode: If True, use a very broad time window for collection requests
    
    Returns:
        True if the game should be included in live results
    """
    if collection_mode:
        # Use a broader window for collection requests - users want to see games from their collection
        two_days_ago = current_time - timedelta(days=2)
        two_days_from_now = current_time + timedelta(days=2)
        
        status_lower = status.lower()
        
        # Include all live games
        if status_lower in ['in progress', 'halftime', '1st quarter', '2nd quarter', '3rd quarter', '4th quarter', 
                           '1st half', '2nd half', 'overtime', 'live', 'active']:
            return True
        
        # Include finals from the past 2 days
        if status_lower == 'final' and game_date >= two_days_ago:
            return True
        
        # Include scheduled games within the next 2 days
        if status_lower == 'scheduled' and game_date <= two_days_from_now:
            return True
            
        return False
    
    if tight_window:
        # Use a much tighter window when we want to prioritize recent/current games
        four_hours_ago = current_time - timedelta(hours=4)
        six_hours_from_now = current_time + timedelta(hours=6)
        
        status_lower = status.lower()
        
        # Always include live games
        if status_lower in ['in progress', 'halftime', '1st quarter', '2nd quarter', '3rd quarter', '4th quarter', 
                           '1st half', '2nd half', 'overtime', 'live', 'active']:
            return True
        
        # Only recent finals (within 4 hours) and near-future games (within 6 hours)
        if status_lower == 'final' and game_date >= four_hours_ago:
            return True
        
        if status_lower == 'scheduled' and game_date <= six_hours_from_now:
            return True
            
        return False
    
    # Standard window for normal operation
    # Use 12 hours for final games since we only have start time, not end time
    twelve_hours_ago = current_time - timedelta(hours=12)
    
    # For scheduled games, include games within the next 18 hours (to account for US timezones)
    # This ensures we capture games that are "today" in US timezones even if they're tomorrow in UTC
    eighteen_hours_from_now = current_time + timedelta(hours=18)
    
    status_lower = status.lower()
    
    # Include if game is live
    if status_lower in ['in progress', 'halftime', '1st quarter', '2nd quarter', '3rd quarter', '4th quarter', 
                       '1st half', '2nd half', 'overtime', 'live', 'active']:
        return True
    
    # Include if game finished recently (started within last 12 hours)
    if status_lower == 'final' and game_date >= twelve_hours_ago:
        return True
    
    # Include if game is scheduled within the next 18 hours (covers US timezones)
    if status_lower == 'scheduled' and current_time <= game_date < eighteen_hours_from_now:
        return True
    
    return False

def convert_sport_format(sport: str) -> str:
    """Convert user-friendly sport format (with underscores) to ESPN API format (with slashes)"""
    # Handle special cases where we simplified the user format but ESPN still expects the full path
    sport_mappings = {
        "basketball_mens-college": "basketball/mens-college-basketball",
        "basketball_womens-college": "basketball/womens-college-basketball",
        "college_football": "football/college-football"
    }
    
    if sport in sport_mappings:
        return sport_mappings[sport]
    
    # Default conversion: replace underscores with slashes
    return sport.replace('_', '/')

def build_pagination_response(
    request: Request,
    data: List[Dict[str, Any]],
    page: int,
    page_size: int,
    total_items: int,
    base_params: Dict[str, Any],
    force_refresh: bool = False
) -> Dict[str, Any]:
    """
    Build a standardized pagination response with proper URL construction.
    
    Args:
        request: FastAPI request object
        data: The paginated data for this page
        page: Current page number
        page_size: Number of items per page
        total_items: Total number of items across all pages
        base_params: Base query parameters to include in pagination URLs
        force_refresh: Whether to include force_refresh in URLs
    
    Returns:
        Dictionary with pagination metadata and URLs
    """
    # Calculate pagination metadata
    total_pages = (total_items + page_size - 1) // page_size
    has_next = page < total_pages
    has_previous = page > 1
    
    # Get scheme and host with reverse proxy support
    scheme = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("x-forwarded-host", request.headers.get("host", request.url.netloc))
    base_url = f"{scheme}://{host}{request.url.path}"
    
    # Build query parameters for URLs
    def build_url_params(target_page: int) -> str:
        params = [f"page={target_page}", f"page_size={page_size}"]
        
        # Add base parameters
        for key, value in base_params.items():
            if value is not None:
                params.append(f"{key}={value}")
        
        # Add force_refresh if needed
        if force_refresh:
            params.append("force_refresh=true")
            
        return "&".join(params)
    
    # Build pagination URLs
    next_page_url = f"{base_url}?{build_url_params(page + 1)}" if has_next else None
    prev_page_url = f"{base_url}?{build_url_params(page - 1)}" if has_previous else None
    
    return {
        "data": data,
        "pagination": {
            "current_page": page,
            "page_size": page_size,
            "total_scores": total_items,
            "total_pages": total_pages,
            "has_next": has_next,
            "has_previous": has_previous,
            "next_page_url": next_page_url,
            "previous_page_url": prev_page_url
        }
    }

def get_collection_groups() -> Dict[str, Dict[str, List[int]]]:
    """Get the conference to ESPN group mapping with granular sport-specific collections"""
    return {
        # GRANULAR SPORT-SPECIFIC COLLECTIONS (New preferred format)
        
        # Atlantic 10 Conference (A-10)
        "a_10_mens_basketball": {
            "basketball_mens-college": [3]  # Group 3 is A-10 for men's basketball
        },
        "a_10_womens_basketball": {
            "basketball_womens-college": [3]  # Group 3 is A-10 for women's basketball
        },
        
        # Big East Conference
        "big_east_mens_basketball": {
            "basketball_mens-college": [4]  # Group 4 is Big East for men's basketball
        },
        "big_east_womens_basketball": {
            "basketball_womens-college": [4]  # Group 4 is Big East for women's basketball
        },
        
        # Big 12 Conference  
        "big_12_football": {
            "college_football": [4]  # Group 4 is Big 12 for football
        },
        
        # Big Ten Conference
        "big_ten_football": {
            "college_football": [5]  # Group 5 is Big Ten for football
        },
        
        # ACC Conference
        "acc_mens_basketball": {
            "basketball_mens-college": [2]  # Group 2 is ACC for men's basketball
        },
        "acc_womens_basketball": {
            "basketball_womens-college": [2]  # Group 2 is ACC for women's basketball
        },
        "acc_football": {
            "college_football": [1]  # Group 1 is ACC for football
        },
        
        # America East Conference
        "america_east_mens_basketball": {
            "basketball_mens-college": [1]  # Group 1 is America East for men's basketball
        },
        "america_east_womens_basketball": {
            "basketball_womens-college": [1]  # Group 1 is America East for women's basketball
        },
        
        # Big Sky Conference
        "big_sky_mens_basketball": {
            "basketball_mens-college": [5]  # Group 5 is Big Sky for men's basketball (Group 49 is identical alternative)
        },
        "big_sky_womens_basketball": {
            "basketball_womens-college": [5]  # Group 5 is Big Sky for women's basketball (Group 47 is identical alternative)
        },
        "big_sky_football": {
            "college_football": [20]  # Group 20 is Big Sky for football
        },
        
        # Big 12 Conference  
        "big_12_mens_basketball": {
            "basketball_mens-college": [8]  # Group 8 is Big 12 for men's basketball
        },
        "big_12_womens_basketball": {
            "basketball_womens-college": [8]  # Group 8 is Big 12 for women's basketball
        },
        "big_12_football": {
            "college_football": [4]  # Group 4 is Big 12 for football
        },
        
        # SEC Conference
        "sec_mens_basketball": {
            "basketball_mens-college": [23]  # Group 23 is SEC for men's basketball
        },
        "sec_womens_basketball": {
            "basketball_womens-college": [23]  # Group 23 is SEC for women's basketball (same group)
        },
        "sec_football": {
            "college_football": [8]  # Group 8 is SEC for football
        },
        
        # ACC Conference
        "acc_mens_basketball": {
            "basketball_mens-college": [2]  # Group 2 is ACC for men's basketball
        },
        "acc_womens_basketball": {
            "basketball_womens-college": [2]  # Group 2 is ACC for women's basketball (same group)
        },
        "acc_football": {
            "college_football": [1]  # Group 1 is ACC for football
        },
        
        # Big Ten Conference
        "big_ten_mens_basketball": {
            "basketball_mens-college": [7]  # Group 7 is Big Ten for men's basketball
        },
        "big_ten_womens_basketball": {
            "basketball_womens-college": [7]  # Group 7 is Big Ten for women's basketball (same group)
        },
        "big_ten_football": {
            "college_football": [5]  # Group 5 is Big Ten for football
        },
        
        # Big West Conference
        "big_west_mens_basketball": {
            "basketball_mens-college": [9]  # Group 9 is Big West for men's basketball
        },
        "big_west_womens_basketball": {
            "basketball_womens-college": [9]  # Group 9 is Big West for women's basketball
        },
        
        # Coastal Athletic Association
        "coastal_mens_basketball": {
            "basketball_mens-college": [10]  # Group 10 is Coastal for men's basketball
        },
        "coastal_womens_basketball": {
            "basketball_womens-college": [10]  # Group 10 is Coastal for women's basketball
        },
        
        # Conference USA (C-USA)
        "conference_usa_mens_basketball": {
            "basketball_mens-college": [11]  # Group 11 is Conference USA for men's basketball
        },
        "conference_usa_womens_basketball": {
            "basketball_womens-college": [11]  # Group 11 is Conference USA for women's basketball
        },
        "conference_usa_football": {
            "college_football": [12]  # Group 12 is Conference USA for football
        },
        
        # Ivy League
        "ivy_league_mens_basketball": {
            "basketball_mens-college": [12]  # Group 12 is Ivy League for men's basketball
        },
        "ivy_league_womens_basketball": {
            "basketball_womens-college": [12]  # Group 12 is Ivy League for women's basketball
        },
        
        # Metro Atlantic Athletic Conference (MAAC)
        "maac_mens_basketball": {
            "basketball_mens-college": [13]  # Group 13 is MAAC for men's basketball
        },
        "maac_womens_basketball": {
            "basketball_womens-college": [13]  # Group 13 is MAAC for women's basketball
        },
        
        # Mid-American Conference (MAC)
        "mac_mens_basketball": {
            "basketball_mens-college": [14]  # Group 14 is MAC for men's basketball
        },
        "mac_womens_basketball": {
            "basketball_womens-college": [14]  # Group 14 is MAC for women's basketball
        },
        "mac_football": {
            "college_football": [15]  # Group 15 is MAC for football
        },
        
        # Mid-Eastern Athletic Conference (MEAC)
        "meac_mens_basketball": {
            "basketball_mens-college": [16]  # Group 16 is MEAC for men's basketball
        },
        "meac_womens_basketball": {
            "basketball_womens-college": [16]  # Group 16 is MEAC for women's basketball
        },
        
        # Mountain West Conference
        "mountain_west_football": {
            "college_football": [17]  # Group 17 is Mountain West for football
        },
        
        # Missouri Valley Conference (MVC)
        "missouri_valley_mens_basketball": {
            "basketball_mens-college": [18]  # Group 18 is Missouri Valley for men's basketball
        },
        "missouri_valley_womens_basketball": {
            "basketball_womens-college": [18]  # Group 18 is Missouri Valley for women's basketball
        },
        
        # Northeast Conference (NEC)
        "northeast_mens_basketball": {
            "basketball_mens-college": [19]  # Group 19 is Northeast for men's basketball
        },
        "northeast_womens_basketball": {
            "basketball_womens-college": [19]  # Group 19 is Northeast for women's basketball
        },
        
        # Ohio Valley Conference (OVC)
        "ohio_valley_mens_basketball": {
            "basketball_mens-college": [20]  # Group 20 is Ohio Valley for men's basketball
        },
        "ohio_valley_womens_basketball": {
            "basketball_womens-college": [20]  # Group 20 is Ohio Valley for women's basketball
        },
        
        # Pac-12 Conference (or Pac-whatever it is now)
        "pac_12_mens_basketball": {
            "basketball_mens-college": [21]  # Group 21 is Pac-12 for men's basketball
        },
        "pac_12_womens_basketball": {
            "basketball_womens-college": [21]  # Group 21 is Pac-12 for women's basketball
        },
        
        # Patriot League
        "patriot_league_mens_basketball": {
            "basketball_mens-college": [22]  # Group 22 is Patriot League for men's basketball
        },
        "patriot_league_womens_basketball": {
            "basketball_womens-college": [22]  # Group 22 is Patriot League for women's basketball
        },
        
        # Southern Conference (SoCon)
        "southern_mens_basketball": {
            "basketball_mens-college": [24]  # Group 24 is Southern for men's basketball
        },
        "southern_womens_basketball": {
            "basketball_womens-college": [24]  # Group 24 is Southern for women's basketball
        },
        
        # Southland Conference
        "southland_mens_basketball": {
            "basketball_mens-college": [25]  # Group 25 is Southland for men's basketball
        },
        "southland_womens_basketball": {
            "basketball_womens-college": [25]  # Group 25 is Southland for women's basketball
        },
        
        # Southwestern Athletic Conference (SWAC)
        "swac_mens_basketball": {
            "basketball_mens-college": [26]  # Group 26 is SWAC for men's basketball
        },
        "swac_womens_basketball": {
            "basketball_womens-college": [26]  # Group 26 is SWAC for women's basketball
        },
        
        # Sun Belt Conference
        "sun_belt_mens_basketball": {
            "basketball_mens-college": [27]  # Group 27 is Sun Belt for men's basketball
        },
        "sun_belt_womens_basketball": {
            "basketball_womens-college": [27]  # Group 27 is Sun Belt for women's basketball
        },
        
        # Patriot League Football
        "patriot_league_football": {
            "college_football": [27]  # Group 27 is Patriot League for football
        },
        
        # WCC (West Coast Conference) Basketball
        "wcc_mens_basketball": {
            "basketball_mens-college": [29]  # Group 29 is WCC for men's basketball
        },
        "wcc_womens_basketball": {
            "basketball_womens-college": [29]  # Group 29 is WCC for women's basketball
        },
        
        # Southern Conference Football
        "southern_football": {
            "college_football": [29]  # Group 29 is Southern for football
        },
        
        # WAC (Western Athletic Conference) Basketball
        "wac_mens_basketball": {
            "basketball_mens-college": [30]  # Group 30 is WAC for men's basketball
        },
        "wac_womens_basketball": {
            "basketball_womens-college": [30]  # Group 30 is WAC for women's basketball
        },
        
        # UAC (United Athletic Conference) Football
        "uac_football": {
            "college_football": [30]  # Group 30 is UAC for football
        },
        
        # SWAC (Southwestern Athletic Conference) Football
        "swac_football": {
            "college_football": [31]  # Group 31 is SWAC for football
        },
        
        # Division III Football
        "d3_football": {
            "college_football": [35]  # Group 35 is Division III football (Group 58 is subset with 8 games)
        },
        
        # Division II Football
        "d2_football": {
            "college_football": [57]  # Group 57 is Division II football
        },
        
        # Horizon League Basketball
        "horizon_league_mens_basketball": {
            "basketball_mens-college": [45]  # Group 45 is Horizon League for men's basketball
        },
        "horizon_league_womens_basketball": {
            "basketball_womens-college": [45]  # Group 45 is Horizon League for women's basketball
        },
        
        # ASUN Conference Basketball
        "asun_mens_basketball": {
            "basketball_mens-college": [46]  # Group 46 is ASUN for men's basketball
        },
        "asun_womens_basketball": {
            "basketball_womens-college": [46]  # Group 46 is ASUN for women's basketball
        },
        
        # FBS Collections
        "fbs_football": {
            "college_football": [80]  # Group 80 is FBS football
        },
        
        # FCS Collections
        "fcs_football": {
            "college_football": [81]  # Group 81 is FCS football
        },
        "mvfc_football": {  # Missouri Valley Football Conference
            "college_football": [21]  # Group 21 is MVFC for football
        },
        
        # Top 25 Collections
        "cfb_top_25": {
            "college_football": ["top25"]  # Special identifier for top 25 filtering
        },
        "mcbb_top_25": {
            "basketball_mens-college": ["top25"]  # Special identifier for men's college basketball top 25 filtering
        },
        "wcbb_top_25": {
            "basketball_womens-college": ["top25"]  # Special identifier for women's college basketball top 25 filtering
        },
        
        # Broad Collections
        "college_football": {
            "college_football": [90]  # Group 90 is FBS + FCS football (Group 99 includes D2/D3 for true "all football")
        },
        "all_college_football": {
            "college_football": [99]  # Group 99 is ALL college football (FBS + FCS + D2 + D3)
        },
        "mens_college_basketball": {
            "basketball_mens-college": [50]  # Group 50 is all Division I men's college basketball
        },
        "womens_college_basketball": {
            "basketball_womens-college": [50]  # Group 50 is all Division I women's college basketball
        },
        
        # LEGACY COLLECTIONS (For backward compatibility - will map to multiple sports)
        "big sky": {
            "basketball_mens-college": [5],  # Group 5 is Big Sky for basketball
            "college_football": [20]  # Group 20 is Big Sky for football
        },
        "big_sky": {  # Allow underscore version
            "basketball_mens-college": [5],
            "college_football": [20]
        },
        "big 12": {
            "basketball_mens-college": [21],  # Group 21 is Big 12 for basketball
            "college_football": [4]  # Group 4 is Big 12 for football
        },
        "big_12": {  # Allow underscore version (legacy)
            "basketball_mens-college": [21],
            "college_football": [4]
        },
        "mvfc": {
            "college_football": [21]  # Group 21 is MVFC for football
        },
        "missouri_valley": {  # Allow full name version
            "college_football": [21]
        },
        "fcs": {
            "college_football": [81]  # Group 81 is FCS football
        },
        "fcs football": {  # Allow full name version
            "college_football": [81]
        }
    }

def get_basic_sport_filters() -> Dict[str, str]:
    """Get basic sport filtering options for collections parameter"""
    return {
        'nfl': 'football/nfl',
        'nba': 'basketball/nba',
        'mlb': 'baseball/mlb',
        'nhl': 'hockey/nhl',
        'cfb': 'football/college-football',
        'mcbb': 'basketball/mens-college-basketball',
        'mens_college_basketball': 'basketball/mens-college-basketball',
        'womens_college_basketball': 'basketball/womens-college-basketball',
        'wnba': 'basketball/wnba',
        'college_baseball': 'baseball/college-baseball',
        'premier_league': 'soccer/eng.1',
        'champions_league': 'soccer/uefa.champions',
        'mls': 'soccer/usa.1'
    }

def get_sport_examples() -> Dict[str, Any]:
    """Get available sports with user-friendly format"""
    return {
        "basketball": {
            "nba": "basketball_nba",
            "mens_college": "basketball_mens-college",
            "womens_college": "basketball_womens-college-basketball", 
            "wnba": "basketball_wnba"
        },
        "football": {
            "nfl": "football_nfl",
            "college": "college_football"
        },
        "baseball": {
            "mlb": "baseball_mlb",
            "college": "baseball_college-baseball"
        },
        "hockey": {
            "nhl": "hockey_nhl"
        },
        "soccer": {
            "premier_league": "soccer_eng.1",
            "champions_league": "soccer_uefa.champions",
            "mls": "soccer_usa.1",
            "la_liga": "soccer_esp.1",
            "bundesliga": "soccer_ger.1",
            "serie_a": "soccer_ita.1",
            "ligue_1": "soccer_fra.1"
        },
        "tennis": {
            "atp": "tennis_atp",
            "wta": "tennis_wta"
        },
        "golf": {
            "pga": "golf_pga"
        }
    }

@router.get("/scores")
async def get_scores(
    request: Request,
    sport: str = Query("basketball_nba", description="Sport to get scores for (e.g., basketball_nba, football_nfl, baseball_mlb, hockey_nhl, soccer_eng.1)"),
    page: int = Query(1, ge=1, description="Page number (starts from 1)"),
    page_size: int = Query(5, ge=1, le=500, description="Number of scores per page"),
    force_refresh: bool = Query(False, description="Force refresh from ESPN API")
) -> Dict[str, Any]:
    # Convert user-friendly format to ESPN API format
    espn_sport = convert_sport_format(sport)
    
    # Calculate offset based on page and page_size
    offset = (page - 1) * page_size
    
    # Create sport-specific cache key
    cache_key = f"sports_scores_{sport.replace('.', '_')}"
    
    # Check cache unless force refresh is requested
    cached_scores = None if force_refresh else cache.get(cache_key)
    
    scores_data = None
    total_scores = 0
    
    if cached_scores:
        scores_data = cached_scores
        total_scores = len(cached_scores)
    else:
        try:
            # Fetch fresh scores from ESPN using converted format
            scores = await espn_service.fetch_scores(sport=espn_sport)
            
            cache.set(cache_key, scores)
            scores_data = scores
            total_scores = len(scores)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    # Calculate pagination
    offset = (page - 1) * page_size
    end_index = offset + page_size
    paginated_scores = scores_data[offset:end_index]
    
    if not paginated_scores and page > 1:
        raise HTTPException(status_code=404, detail="Page not found")
    
    # Build pagination response
    base_params = {"sport": sport}
    return build_pagination_response(
        request=request,
        data=paginated_scores,
        page=page,
        page_size=page_size,
        total_items=total_scores,
        base_params=base_params,
        force_refresh=force_refresh
    )

@router.get("/sports")
async def get_available_sports() -> Dict[str, Any]:
    """Get list of available sports"""
    sports = get_sport_examples()
    
    return {
        "sports": sports,
        "examples": [
            "/api/scores?sport=football_nfl",
            "/api/scores?sport=soccer_eng.1", 
            "/api/scores?sport=baseball_mlb",
            "/api/scores?sport=hockey_nhl"
        ],
        "note": "Use underscores instead of slashes for better URL compatibility"
    }

@router.get("/conferences")
async def get_conferences(
    sport: str = Query("basketball_mens-college", description="Sport to get conferences for"),
    force_refresh: bool = Query(False, description="Force refresh from ESPN API")
) -> Dict[str, Any]:
    """Get list of conferences for a specific sport"""
    
    # Convert user-friendly format to ESPN API format
    espn_sport = convert_sport_format(sport)
    
    try:
        # Fetch scores to extract conference information
        scores = await espn_service.fetch_scores(sport=espn_sport, limit=100)
        
        # Extract unique conferences
        conferences = set()
        for score in scores:
            home_conf = score.get('home_team', {}).get('conference', '')
            away_conf = score.get('away_team', {}).get('conference', '')
            
            if home_conf and home_conf != 'Unknown':
                conferences.add(home_conf)
            if away_conf and away_conf != 'Unknown':
                conferences.add(away_conf)
        
        # Sort conferences alphabetically
        sorted_conferences = sorted(list(conferences))
        
        return {
            "sport": sport,
            "conferences": sorted_conferences,
            "total_conferences": len(sorted_conferences),
            "examples": [
                f"/api/scores?sport={sport}&conference=SEC",
                f"/api/live?sport={sport}&conference=Big Ten",
                f"/api/scores?sport={sport}&conference=ACC&page_size=5"
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conference/{conference_name}")
async def get_conference_games(
    request: Request,
    conference_name: str,
    sport: str = Query("basketball_mens-college", description="Sport type (basketball_mens-college, college_football)"),
    page: int = Query(1, description="Page number", ge=1),
    page_size: int = Query(10, description="Number of scores per page", ge=1, le=500),
    force_refresh: bool = Query(False, description="Force refresh cache")
):
    """Get games for a specific conference using ESPN groups parameter"""
    
    # Get collection groups mapping
    collection_groups = get_collection_groups()
    
    conference_key = conference_name.lower().replace("-", " ").replace("_", " ")
    
    if conference_key not in collection_groups:
        raise HTTPException(
            status_code=404, 
            detail=f"Conference '{conference_name}' not supported. Available: {list(collection_groups.keys())}"
        )
    
    if sport not in collection_groups[conference_key]:
        raise HTTPException(
            status_code=404,
            detail=f"Sport '{sport}' not available for conference '{conference_name}'"
        )
    
    # Get the group IDs for this conference/sport combination
    group_ids = collection_groups[conference_key][sport]
    
    cache_key = f"conference:{conference_key}:{sport}"
    
    if not force_refresh:
        cached_result = cache.get(cache_key)
        if cached_result:
            # Apply pagination to cached results
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            
            paginated_data = cached_result[start_idx:end_idx]
            
            total_scores = len(cached_result)
            total_pages = (total_scores + page_size - 1) // page_size
            
            # Build pagination response for cached data
            base_params = {"sport": sport}
            pagination_response = build_pagination_response(
                request=request,
                data=paginated_data,
                page=page,
                page_size=page_size,
                total_items=total_scores,
                base_params=base_params,
                force_refresh=force_refresh
            )
            
            # Add conference-specific info to the response
            pagination_response["info"] = {
                "conference": conference_name.title(),
                "sport": sport,
                "group_ids_used": group_ids,
                "cache_duration": "5 minutes"
            }
            
            return pagination_response
    
    # Fetch games from all group IDs for this conference
    all_conference_games = []
    
    # Convert sport format for ESPN API using the same conversion function
    espn_sport_format = convert_sport_format(sport)
    
    for group_id in group_ids:
        try:
            group_games = await espn_service.fetch_conference_games(espn_sport_format, group_id)
            all_conference_games.extend(group_games)
        except Exception as e:
            print(f"Error fetching group {group_id}: {e}")
            continue
    
    # Remove duplicates based on game ID
    seen_ids = set()
    unique_games = []
    for game in all_conference_games:
        if game['id'] not in seen_ids:
            seen_ids.add(game['id'])
            unique_games.append(game)
    
    # Cache the results
    cache.set(cache_key, unique_games, expiration_minutes=5)  # 5 minutes
    
    # Apply pagination
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paginated_data = unique_games[start_idx:end_idx]
    
    total_scores = len(unique_games)
    total_pages = (total_scores + page_size - 1) // page_size
    
    # Build pagination response for fresh data
    base_params = {"sport": sport}
    pagination_response = build_pagination_response(
        request=request,
        data=paginated_data,
        page=page,
        page_size=page_size,
        total_items=total_scores,
        base_params=base_params,
        force_refresh=force_refresh
    )
    
    # Add conference-specific info to the response
    pagination_response["info"] = {
        "conference": conference_name.title(),
        "sport": sport,
        "group_ids_used": group_ids,
        "total_games_found": total_scores,
        "cache_duration": "5 minutes"
    }
    
    return pagination_response

@router.get("/live")
async def get_live_scores(
    request: Request,
    sport: str = Query(None, description="Specific sport to get live scores for (e.g., basketball_nba, football_nfl). If not specified, gets all sports."),
    page: int = Query(1, ge=1, description="Page number (starts from 1)"),
    page_size: int = Query(10, ge=1, le=500, description="Number of scores per page"),
    force_refresh: bool = Query(False, description="Force refresh from ESPN API"),
    collections: str = Query(None, description="Comma-separated list of collections to include games from. Supports granular sport-specific collections (e.g., 'big_sky_mens_basketball,big_sky_football,cfb_top_25') or legacy multi-sport collections (e.g., 'big_sky,cfb_top_25,mcbb_top_25')")
) -> Dict[str, Any]:
    """Get live games, recently finished games (final games that started within the last 12 hours), and upcoming games within the next 18 hours (timezone-aware for US) from specified sport or all sports. Optionally include games from specific collections."""
    
    # Define the sports we want to check
    if sport:
        # Convert user-friendly format to ESPN API format
        espn_sport = convert_sport_format(sport)
        sports_to_check = [espn_sport]
        cache_key = f"live_scores_{sport.replace('.', '_')}"
    else:
        # If no sport specified, check all sports (using ESPN format)
        sports_to_check = [
            "basketball/nba",
            "football/nfl", 
            "baseball/mlb",
            "hockey/nhl",
            "soccer/eng.1",  # Premier League
            "soccer/usa.1",  # MLS
            "basketball/mens-college-basketball",
            "basketball/womens-college-basketball",
            "football/college-football"
        ]
        cache_key = "live_scores_all_sports"
    
    # Add collections to cache key if specified
    if collections:
        cache_key += f"_coll_{collections.replace(',', '_').replace(' ', '')}"
    
    # Check cache unless force refresh is requested
    cached_scores = None if force_refresh else cache.get(cache_key)
    
    all_live_scores = []
    
    if cached_scores:
        all_live_scores = cached_scores
    else:
        current_time = datetime.now(timezone.utc)
        collection_scores = []
        sport_filters_requested = []
        
        # Fetch collection games first if requested
        if collections:
            collection_list = [coll.strip() for coll in collections.split(',')]
            
            # Get the collection groups mapping
            collection_groups = get_collection_groups()
            
            # Get basic sport filtering options
            basic_sport_filters = get_basic_sport_filters()
            
            # Check if any collection is actually a basic sport filter
            sport_filters_requested = []
            actual_collections = []
            
            for collection_name in collection_list:
                collection_key = collection_name.lower().replace(' ', '').replace('-', '_')
                
                if collection_key in basic_sport_filters:
                    # This is a sport filter, not a collection
                    sport_filters_requested.append(basic_sport_filters[collection_key])
                else:
                    # This is an actual collection
                    actual_collections.append(collection_name)
            
            # Fetch games for each actual collection (not sport filters)
            for collection_name in actual_collections:
                collection_key = collection_name.lower().replace(' ', '').replace('-', '_')
                
                if collection_key in collection_groups:
                    # Get groups for all supported sports
                    for sport_key in ["basketball_mens-college", "basketball_womens-college", "college_football"]:
                        if sport_key in collection_groups[collection_key]:
                            groups = collection_groups[collection_key][sport_key]
                            
                            # Convert sport key to ESPN API format
                            espn_sport = convert_sport_format(sport_key)
                            
                            for group_id in groups:
                                try:
                                    # Handle special case for top 25 filtering
                                    if group_id == "top25":
                                        games = await espn_service.fetch_top25_games(espn_sport)
                                    else:
                                        games = await espn_service.fetch_conference_games(espn_sport, group_id)
                                    
                                    for game in games:
                                        # Add sport info to the game data
                                        game['sport'] = espn_sport
                                        game['sport_display'] = espn_sport.replace('/', ' ').title().replace('Nba', 'NBA').replace('Nfl', 'NFL').replace('Mlb', 'MLB').replace('Nhl', 'NHL')
                                        collection_scores.append(game)
                                        
                                except Exception as e:
                                    print(f"Error fetching conference group {group_id} for {sport_key}: {e}")
                                    continue
        
        # Check if we have more than 25 collection results
        if collections and len(collection_scores) > 25:
            # If we have more than 25 collection games, just use those
            all_live_scores = collection_scores
        else:
            # Determine if we should use tight time window
            # Use tight window when pulling from generic results (no collections specified)
            # Use normal window when user specifies collections (they want all games from their collections)
            use_tight_window = collections is None
            
            # Determine which sports to fetch based on sport filters
            # Only fetch general sports if no collections OR if we have sport filters
            should_fetch_general_sports = collections is None or len(sport_filters_requested) > 0
            
            if should_fetch_general_sports:
                sports_to_fetch = sports_to_check
                if sport_filters_requested:
                    # If specific sport filters were requested, only fetch those sports
                    sports_to_fetch = sport_filters_requested
                
                # Fetch scores from sports to supplement
                for espn_sport_format in sports_to_fetch:
                    try:
                        scores = await espn_service.fetch_scores(sport=espn_sport_format, limit=50)
                        
                        # Filter for live games, recently finished games, or upcoming games
                        for score in scores:
                            game_date = datetime.fromisoformat(score['date'].replace('Z', '+00:00'))
                            status = score['status']
                            
                            # Use helper function to check if game should be included
                            # Use collection mode when collections are specified, tight window for generic requests
                            if is_game_in_live_window(game_date, status, current_time, tight_window=use_tight_window, collection_mode=(collections is not None)):
                                
                                # Add sport info to the score data
                                score['sport'] = espn_sport_format
                                score['sport_display'] = espn_sport_format.replace('/', ' ').title().replace('Nba', 'NBA').replace('Nfl', 'NFL').replace('Mlb', 'MLB').replace('Nhl', 'NHL')
                                all_live_scores.append(score)
                                
                    except Exception as e:
                        # Continue with other sports if one fails
                        print(f"Error fetching {espn_sport_format}: {e}")
                        continue
            
            # Combine collection games with general live games and deduplicate
            if collection_scores:
                seen_ids = set()
                combined_scores = []
                
                # Add collection scores first (these take priority)
                for score in collection_scores:
                    if score['id'] not in seen_ids:
                        seen_ids.add(score['id'])
                        combined_scores.append(score)
                
                # Add general live scores that aren't already included
                for score in all_live_scores:
                    if score['id'] not in seen_ids:
                        seen_ids.add(score['id'])
                        combined_scores.append(score)
                
                all_live_scores = combined_scores
        
        # Sort by game date (most recent first)
        all_live_scores.sort(key=lambda x: x['date'], reverse=True)
        
        # Group by league and then sort by time within each league
        # Sort by sport priority first, then by date within each sport
        all_live_scores.sort(key=lambda x: (get_sport_priority(x['sport']), x['date']))
        
        # Enrich in-progress games with detailed status information
        # Group games by sport for efficient enrichment
        games_by_sport = {}
        for game in all_live_scores:
            sport = game['sport']
            if sport not in games_by_sport:
                games_by_sport[sport] = []
            games_by_sport[sport].append(game)
        
        # Enrich each sport's games
        enriched_games = []
        for sport, games in games_by_sport.items():
            try:
                enriched_sport_games = await espn_service._enrich_with_detailed_status(games, sport)
                enriched_games.extend(enriched_sport_games)
            except Exception as e:
                print(f"Error enriching {sport} games: {e}")
                # If enrichment fails, use original games
                enriched_games.extend(games)
        
        # Maintain the same sorting after enrichment
        enriched_games.sort(key=lambda x: (get_sport_priority(x['sport']), x['date']))
        all_live_scores = enriched_games
        
        # Cache the results for 2 minutes (shorter cache for live data)
        cache.set(cache_key, all_live_scores, expiration_minutes=2)
    
    # Apply pagination
    total_scores = len(all_live_scores)
    offset = (page - 1) * page_size
    end_index = offset + page_size
    paginated_scores = all_live_scores[offset:end_index]
    
    if not paginated_scores and page > 1:
        raise HTTPException(status_code=404, detail="Page not found")
    
    # Build pagination response
    base_params = {}
    if collections:
        base_params["collections"] = collections
        
    pagination_response = build_pagination_response(
        request=request,
        data=paginated_scores,
        page=page,
        page_size=page_size,
        total_items=total_scores,
        base_params=base_params,
        force_refresh=force_refresh
    )
    
    # Add live-specific info to the response
    filter_description = "All sports"
    if sport:
        filter_description = f"Specific sport: {sport}"
    elif collections:
        # Check if collections included sport filters
        collection_list = [coll.strip() for coll in collections.split(',')]
        basic_sport_filters = get_basic_sport_filters()
        
        sport_filters = []
        other_collections = []
        
        for coll in collection_list:
            coll_key = coll.lower().replace(' ', '').replace('-', '_')
            if coll_key in basic_sport_filters:
                sport_filters.append(coll)
            else:
                other_collections.append(coll)
        
        if sport_filters and other_collections:
            filter_description = f"Sports: {', '.join(sport_filters)}, Collections: {', '.join(other_collections)}"
        elif sport_filters:
            filter_description = f"Sports: {', '.join(sport_filters)}"
        else:
            filter_description = f"Collections: {', '.join(other_collections)}"
    
    pagination_response["info"] = {
        "description": "Live games or recently finished games (final games that started within the last 4 hours)",
        "sports_checked": sports_to_check,
        "cache_duration": "2 minutes",
        "filter": filter_description
    }
    
    return pagination_response

@router.get("/top_performers")
async def get_top_performers(
    request: Request,
    sport: str = Query(None, description="Specific sport to get top performers for (e.g., basketball_nba, football_nfl). If not specified, gets all sports."),
    stat_category: str = Query(None, description="Filter by specific stat category (e.g., 'Pts', 'Reb', 'Ast', 'passing_td', 'rushing_td')"),
    top_n: int = Query(5, ge=1, le=20, description="Number of top performers to return per category"),
    force_refresh: bool = Query(False, description="Force refresh from ESPN API")
) -> Dict[str, Any]:
    """Get top performers across all sports from games in the past 24 hours"""
    
    # Define the sports we want to check
    if sport:
        espn_sport = convert_sport_format(sport)
        sports_to_check = [espn_sport]
        cache_key = f"top_performers_{sport.replace('.', '_')}"
    else:
        sports_to_check = [
            "basketball/nba",
            "football/nfl", 
            "baseball/mlb",
            "hockey/nhl",
            "basketball/mens-college-basketball",
            "football/college-football"
        ]
        cache_key = "top_performers_all_sports"
    
    # Add stat category and top_n to cache key
    if stat_category:
        cache_key += f"_stat_{stat_category.lower()}"
    cache_key += f"_top{top_n}"
    
    # Check cache unless force refresh is requested
    cached_performers = None if force_refresh else cache.get(cache_key)
    
    if cached_performers:
        return cached_performers
    
    # Collect all performers from games in the past 24 hours
    current_time = datetime.now(timezone.utc)
    twenty_four_hours_ago = current_time - timedelta(hours=24)
    
    all_performers = []
    
    for sport_name in sports_to_check:
        try:
            scores = await espn_service.fetch_scores(sport=sport_name, limit=50)
            
            for score in scores:
                game_date = datetime.fromisoformat(score['date'].replace('Z', '+00:00'))
                
                # Only include games from the past 24 hours
                if game_date >= twenty_four_hours_ago:
                    # Extract top performers from this game
                    for performer in score.get('top_performers', []):
                        performer_data = {
                            'player_name': performer['player_name'],
                            'team': performer['team'],
                            'team_abbr': performer['team_abbr'],
                            'stat_category': performer['stat_category'],
                            'value': performer['value'],
                            'description': performer['description'],
                            'sport': sport_name,
                            'sport_display': sport_name.replace('/', ' ').title().replace('Nba', 'NBA').replace('Nfl', 'NFL').replace('Mlb', 'MLB').replace('Nhl', 'NHL'),
                            'game_name': score['name'],
                            'game_date': score['date'],
                            'game_status': score['status']
                        }
                        all_performers.append(performer_data)
                        
        except Exception as e:
            print(f"Error fetching {sport_name} for top performers: {e}")
            continue
    
    # Organize performers by stat category
    performers_by_category = {}
    
    for performer in all_performers:
        category = performer['stat_category']
        
        # Filter by stat category if specified
        if stat_category and category.lower() != stat_category.lower():
            continue
            
        if category not in performers_by_category:
            performers_by_category[category] = []
        
        performers_by_category[category].append(performer)
    
    # Sort each category by value (descending) and take top N
    top_performers_result = {}
    
    for category, performers in performers_by_category.items():
        # Sort by value (highest first)
        sorted_performers = sorted(performers, key=lambda x: x['value'], reverse=True)
        top_performers_result[category] = sorted_performers[:top_n]
    
    # Calculate some summary stats
    total_games_analyzed = len(set(f"{p['sport']}_{p['game_name']}" for p in all_performers))
    total_performers = len(all_performers)
    unique_players = len(set(p['player_name'] for p in all_performers))
    
    result = {
        "top_performers": top_performers_result,
        "summary": {
            "total_games_analyzed": total_games_analyzed,
            "total_performer_records": total_performers,
            "unique_players": unique_players,
            "stat_categories_found": list(top_performers_result.keys()),
            "time_period": "Past 24 hours",
            "top_n_per_category": top_n
        },
        "filters": {
            "sport_filter": sport if sport else "All sports",
            "stat_category_filter": stat_category if stat_category else "All categories",
            "sports_checked": sports_to_check
        }
    }
    
    # Cache the results for 10 minutes
    cache.set(cache_key, result, expiration_minutes=10)
    
    return result


