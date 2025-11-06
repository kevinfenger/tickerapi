# TickerAPI

FastAPI Sports Data Backend

## Overview

A comprehensive FastAPI backend that provides live sports scores, team data, and game information optimized for LED display systems. Features real-time data from ESPN APIs with caching and advanced filtering capabilities.

## Features

- **Live Sports Scores**: Real-time game data from multiple leagues (NBA, NFL, NHL, MLB, MLS, NCAA)
- **Team Data Enhancement**: Comprehensive team information with logos and metadata
- **Conference Filtering**: Detailed conference and division organization
- **Caching Layer**: Redis-based caching for optimal performance
- **LED Display Optimization**: Image processing pipeline for LED matrix displays
- **Docker Support**: Containerized deployment with Docker Compose

## API Endpoints

### Core Endpoints
- `GET /live` - Live sports scores with optional conference filtering
- `GET /games` - Game data with detailed status information
- `GET /teams` - Team information and metadata

### Parameters
- `detailed_conferences=true` - Include conference groupings in response
- `league` - Filter by specific league (nba, nfl, nhl, etc.)
- `conference` - Filter by conference name

## Technology Stack

- **FastAPI** - Modern Python web framework
- **Redis** - Caching layer for performance
- **PIL/Pillow** - Image processing for LED optimization
- **Docker** - Containerization and deployment
- **ESPN API** - Live sports data source

## Project Structure

```
fastapi-sports-scores/
├── app/
│   ├── main.py              # FastAPI application
│   ├── api/
│   │   └── endpoints/
│   │       └── scores.py    # Score endpoints
│   ├── core/
│   │   ├── cache.py         # Redis caching
│   │   └── config.py        # Configuration
│   └── services/
│       └── espn_service.py  # ESPN API integration
├── get_images/
│   ├── get_images.py        # Team logo downloader
│   ├── led_optimizer.py     # LED display optimizer
│   └── sport_logos/         # Processed team logos
│       ├── college/         # College team logos
│       ├── leagues/         # League logos
│       ├── nba/            # NBA team logos
│       ├── nfl/            # NFL team logos
│       └── nhl/            # NHL team logos
├── docker-compose.yml       # Docker services
├── Dockerfile              # Container configuration
├── requirements.txt        # Python dependencies
└── README.md
```

## Quick Start

### Using Docker (Recommended)

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd tickerapi/fastapi-sports-scores
   ```

2. Start the services:
   ```bash
   docker-compose up -d
   ```

3. Access the API:
   - API: http://localhost:8000
   - Documentation: http://localhost:8000/docs
   - Redis: localhost:6379

### Local Development

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Start Redis:
   ```bash
   redis-server
   ```

3. Run the application:
   ```bash
   uvicorn app.main:app --reload
   ```

## Image Processing

The system includes a comprehensive image processing pipeline for LED displays:

### Team Logo Collection
- **583+ College Teams**: Basketball and football team logos
- **Professional Leagues**: NBA, NFL, NHL, MLB, MLS team logos  
- **League Logos**: Official league branding

### LED Optimization Process
1. **Download**: High-resolution logos from ESPN CDN
2. **Resize**: Scale to 32x32 pixels for LED matrix
3. **Color Processing**: Gamma correction (2.4 gamma) for LED displays
4. **Dithering**: Error-diffusion dithering for color accuracy
5. **Quantization**: RGB565 color space conversion
6. **Palette**: 8-bit adaptive palette optimization
7. **Format**: BMP output for direct LED display use

### Image Scripts
- `get_images.py` - Bulk team logo downloader
- `led_optimizer.py` - Individual image LED optimization
- `download_league_logos.py` - Official league logo collection

## Configuration

### Environment Variables
- `REDIS_URL` - Redis connection string
- `DEBUG` - Enable debug mode
- `CORS_ORIGINS` - Allowed CORS origins

### Cache Settings
- Default TTL: 300 seconds (5 minutes)
- Redis host: localhost:6379

## API Usage Examples

### Get Live Scores
```bash
curl "http://localhost:8000/live"
```

### Get Live Scores with Conference Details
```bash
curl "http://localhost:8000/live?detailed_conferences=true"
```

### Filter by League
```bash
curl "http://localhost:8000/live?league=nba"
```

### Filter by Conference
```bash
curl "http://localhost:8000/live?conference=ACC"
```

## Data Sources

- **ESPN API**: Primary data source for live scores and team information
- **Team Logos**: ESPN CDN for high-quality team logos
- **League Data**: Official league APIs and CDNs

## Performance

- **Caching**: Redis-based caching reduces API calls and improves response times
- **Async**: FastAPI async support for concurrent request handling
- **Optimization**: Image processing pipeline optimized for LED display requirements

## Related Projects

- [Ticker](../ticker) - LED matrix display frontend that consumes this API

## License

MIT License

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request
