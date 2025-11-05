# FastAPI Sports Scores API

A FastAPI application that retrieves live sports scores from ESPN's API with caching, pagination, and multi-sport support.

## 🚀 Features

- **Multi-Sport Support**: NBA, NFL, MLB, NHL, Soccer (Premier League, MLS, etc.), College Basketball & Football
- **Live Scores**: Get games that are currently live or finished within the last 2 hours
- **Smart Caching**: 5-minute cache for regular scores, 2-minute cache for live data
- **Pagination**: Navigate through results with next/previous page URLs
- **Network Access**: Accessible from any device on your WiFi network
- **Force Refresh**: Bypass cache when you need fresh data

## 🏗️ Project Structure

```
fastapi-sports-scores/
├── app/
│   ├── main.py              # FastAPI app setup
│   ├── api/endpoints/
│   │   └── scores.py        # API endpoints
│   ├── core/
│   │   ├── cache.py         # Caching system
│   │   └── config.py        # Configuration
│   └── services/
│       └── espn_service.py  # ESPN API integration
├── requirements.txt         # Python dependencies
├── Dockerfile              # Container setup
├── docker-compose.yml      # Multi-container orchestration
├── Makefile               # Simplified commands
└── README.md              # This file
```

## 🚦 Quick Start

1. **Start the application:**
   ```bash
   make up
   ```

2. **Get your network IP:**
   ```bash
   make ip
   ```

3. **Access the API:**
   - Local: `http://localhost:8000/docs`
   - Network: `http://[YOUR_IP]:8000/docs`

## 📡 API Endpoints

### 🏀 Get Scores by Sport
```http
GET /api/scores
```

**Parameters:**
- `sport` (optional): Sport to get scores for (default: `basketball_nba`)
- `conference` (optional): Filter by conference (e.g., 'SEC', 'Big Ten', 'ACC', 'NBA', 'NFL')
- `page` (optional): Page number (default: 1)
- `page_size` (optional): Results per page (default: 5, max: 100)
- `force_refresh` (optional): Bypass cache (default: false)

**Examples:**
```bash
# NBA scores (default)
curl "http://localhost:8000/api/scores"

# SEC college basketball games only
curl "http://localhost:8000/api/scores?sport=basketball_mens-college&conference=SEC"

# Big Ten college basketball with pagination
curl "http://localhost:8000/api/scores?sport=basketball_mens-college&conference=Big Ten&page_size=3"

# All NBA games
curl "http://localhost:8000/api/scores?sport=basketball_nba&conference=NBA"
```

### 🔴 Get Live Scores (All Sports or Specific Sport)
```http
GET /api/live
```

**Description:** Returns games that are currently live or finished within the last 2 hours from all supported sports or a specific sport.

**Parameters:**
- `sport` (optional): Specific sport to filter by (e.g., `basketball_nba`, `football_nfl`). If not specified, returns all sports.
- `conference` (optional): Filter by conference (e.g., 'SEC', 'Big Ten', 'ACC', 'NBA', 'NFL')
- `page` (optional): Page number (default: 1)
- `page_size` (optional): Results per page (default: 10, max: 100)
- `force_refresh` (optional): Bypass cache (default: false)

**Examples:**
```bash
# Get live games from all sports
curl "http://localhost:8000/api/live?page_size=5"

# Get live SEC games only
curl "http://localhost:8000/api/live?conference=SEC"

# Get live NBA games only
curl "http://localhost:8000/api/live?sport=basketball_nba&conference=NBA"

# Get live Big 12 college football
curl "http://localhost:8000/api/live?sport=football_college&conference=Big 12"
```

### 🏟️ Get Available Conferences
```http
GET /api/conferences
```

**Description:** Returns all available conferences for a specific sport.

**Parameters:**
- `sport` (optional): Sport to get conferences for (default: `basketball_mens-college`)
- `force_refresh` (optional): Bypass cache (default: false)

**Examples:**
```bash
# Get college basketball conferences
curl "http://localhost:8000/api/conferences?sport=basketball_mens-college"

# Get college football conferences
curl "http://localhost:8000/api/conferences?sport=football_college"
```

### 🏟️ Get Available Sports
```http
GET /api/sports
```

**Description:** Returns all supported sports and their ESPN API identifiers.

**Example:**
```bash
curl "http://localhost:8000/api/sports"
```

## 🏆 Supported Sports

| Sport | League | API Parameter |
|-------|--------|---------------|
| **Basketball** | NBA | `basketball_nba` |
| | WNBA | `basketball_wnba` |
| | College | `basketball_mens-college` |
| **Football** | NFL | `football_nfl` |
| | College | `football_college` |
| **Baseball** | MLB | `baseball_mlb` |
| **Hockey** | NHL | `hockey_nhl` |
| **Soccer** | Premier League | `soccer_eng.1` |
| | MLS | `soccer_usa.1` |
| | Champions League | `soccer_uefa.champions` |
| | La Liga | `soccer_esp.1` |
| | Bundesliga | `soccer_ger.1` |
| | Serie A | `soccer_ita.1` |
| **Tennis** | ATP | `tennis_atp` |
| | WTA | `tennis_wta` |
| **Golf** | PGA | `golf_pga` |

## 📋 Response Format

```json
{
  "data": [
    {
      "id": "401810011",
      "name": "Team A at Team B",
      "date": "2025-11-04T00:00Z",
      "status": "In Progress",
      "home_team": {
        "name": "Team B",
        "abbreviation": "TMB",
        "score": "98"
      },
      "away_team": {
        "name": "Team A", 
        "abbreviation": "TMA",
        "score": "102"
      },
      "venue": "Stadium Name",
      "sport": "basketball/nba",
      "sport_display": "Basketball NBA"
    }
  ],
  "pagination": {
    "current_page": 1,
    "page_size": 5,
    "total_scores": 15,
    "total_pages": 3,
    "has_next": true,
    "has_previous": false,
    "next_page_url": "http://localhost:8000/api/scores?page=2&page_size=5",
    "previous_page_url": null
  }
}
```

## 🛠️ Development Commands

```bash
# Start containers in detached mode
make up

# Start with logs (development mode)
make dev

# View logs
make logs

# Check container status
make status

# Get network IP addresses
make ip

# Stop containers
make down

# Clean up everything
make clean

# Rebuild containers
make build
```

## 🌐 Network Access

The API is configured to be accessible from other devices on your WiFi network:

1. **Find your IP address:**
   ```bash
   make ip
   ```

2. **Access from other devices:**
   - Replace `localhost` with your IP address
   - Example: `http://192.168.1.100:8000/docs`

## ⚡ Caching System

- **Regular Scores**: 5-minute cache duration
- **Live Scores**: 2-minute cache duration (more frequent updates)
- **Sport-Specific**: Each sport has its own cache key
- **Force Refresh**: Use `force_refresh=true` to bypass cache

## 📱 Use Cases

- **Live Sports Dashboard**: Display current games across multiple sports
- **Score Notifications**: Check for game updates
- **Sports Apps**: Integrate live scores into mobile/web applications
- **Fantasy Sports**: Track player performances in live games
- **Sports Betting**: Monitor live game status and scores

## 🔧 Configuration

The application runs on:
- **Port**: 8000 (configurable in docker-compose.yml)
- **Cache**: Redis (included in docker-compose)
- **Environment**: Development mode with hot reload

## 📄 License

This project is licensed under the MIT License.