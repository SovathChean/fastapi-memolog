# FastAPI Template

A minimal FastAPI project template.

## Requirements

- Python 3.11+

## Installation

```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# Install dependencies (using pyproject.toml)
pip install -e ".[dev]"

# Or using requirements.txt
pip install -r requirements-dev.txt
```

## Environment Configuration

Copy the example environment file and modify as needed:

```bash
# For development
cp .env.dev .env

# Or for production
cp .env.production .env
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `APP_NAME` | Application name | FastAPI Template |
| `APP_ENV` | Environment (development/production) | development |
| `DEBUG` | Debug mode | true |
| `HOST` | Server host | 127.0.0.1 |
| `PORT` | Server port | 8000 |

### Environment Files

- `.env.example` - Template with all available variables
- `.env.dev` - Development settings (DEBUG=true)
- `.env.production` - Production settings (DEBUG=false)
- `.env` - Active environment file (gitignored)

## Usage

### Development Server

```bash
fastapi dev main.py
```

Server runs at http://127.0.0.1:8000

### Production Server

```bash
fastapi run main.py
```

## API Documentation

- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Health check |
| GET | `/api/v1/hello` | Hello endpoint |
| GET | `/api/v1/info` | App info from settings |

## Development

```bash
# Run tests
pytest

# Lint code
ruff check .

# Format code
ruff format .
```

## Project Structure

```
fastapi-template/
├── .venv/               # Virtual environment
├── main.py              # FastAPI application
├── config.py            # Settings configuration
├── pyproject.toml       # Project config & dependencies
├── requirements.txt     # Production dependencies
├── requirements-dev.txt # Development dependencies
├── .env                 # Active environment (gitignored)
├── .env.example         # Environment template
├── .env.dev             # Development settings
├── .env.production      # Production settings
├── .gitignore           # Git ignore patterns
└── README.md            # This file
```
