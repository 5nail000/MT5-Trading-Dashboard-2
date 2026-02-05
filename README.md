# MT5 Trading Dashboard

Personal trading dashboard for MetaTrader 5 with FastAPI backend and Next.js frontend.

## Features

- **Real-time Trading Data**: Connect to MetaTrader 5 terminal
- **Open Positions Monitoring**: Track current floating P/L by magic numbers
- **Historical Analysis**: Analyze past trading performance
- **Magic Number Management**: Organize and describe trading strategies
- **Magic Groups**: Group magics for aggregated statistics
- **Balance/Equity Charts**: Timeline visualization of account performance
- **Deals History**: Detailed view of closed positions
- **Account Comparison**: Compare deals between two accounts by entry time
- **Chart Editor**: Bulk editing of EA parameters in .chr files

## Architecture

```
MT5_Trading_Dashboard/
├── src/                      # Python backend
│   ├── api/                  # FastAPI application
│   │   └── main.py          # REST API endpoints
│   ├── config/              # Configuration
│   │   └── settings.py      # Settings from .env
│   ├── services/            # Business logic layer
│   │   ├── account_service.py   # Account management
│   │   ├── sync_service.py      # MT5 sync operations
│   │   ├── group_service.py     # Magic groups management
│   │   └── chart_service.py     # Chart file (.chr) editing
│   ├── db_sa/               # SQLAlchemy ORM
│   │   ├── models.py        # Database models
│   │   ├── session.py       # Session management
│   │   └── init_db.py       # Database initialization
│   ├── mt5/                 # MetaTrader 5 integration
│   │   ├── mt5_client.py    # MT5 connection & calculations
│   │   └── tick_data.py     # Tick data management
│   ├── sync/                # Data synchronization
│   │   ├── mt5_sync.py      # Sync deals & positions
│   │   └── orchestrator.py  # Sync orchestration
│   ├── analytics/           # Analytics calculations
│   │   └── drawdown.py      # Drawdown calculations
│   ├── readmodels/          # Query handlers (CQRS read side)
│   │   └── dashboard_queries.py
│   ├── security/            # Security utilities
│   │   ├── crypto.py        # Credential encryption (Fernet)
│   │   └── ip_filter.py     # IP whitelist middleware
│   └── utils/               # Utilities
│       ├── helpers.py       # Helper functions
│       ├── logger.py        # Logging configuration
│       └── timezone.py      # Timezone utilities
├── dashboard-next/          # Next.js frontend
│   ├── src/
│   │   ├── app/            # App Router pages
│   │   ├── components/     # React components
│   │   ├── lib/            # API client
│   │   └── types/          # TypeScript types
│   └── package.json
├── tests/                   # Test files
├── scripts/                 # Utility scripts
├── requirements.txt         # Python dependencies
└── .env.example            # Environment template
```

## Installation

### Prerequisites

- Python 3.10+
- Node.js 18+
- MetaTrader 5 terminal installed

### Backend Setup

```bash
# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env
# Edit .env with your settings
```

### Frontend Setup

```bash
cd dashboard-next

# Install dependencies
npm install
```

## Usage

### Start Backend

```bash
# From project root
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

### Start Frontend

```bash
cd dashboard-next
npm run dev
```

Open http://localhost:3000 in your browser.

## Configuration

Edit `.env` file:

```env
# Database
SQLALCHEMY_DATABASE_URL=sqlite:///./mt5_dashboard.db

# Trading
LOCAL_TIMESHIFT=3

# Security
MT5_CRED_KEY=<your-fernet-key>
ALLOWED_ORIGINS=http://localhost:3000
IP_WHITELIST=
```

Generate Fernet key:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /health | Health check |
| GET | /accounts | List accounts |
| GET | /terminal/active | Get active terminal account |
| GET | /magics | List magic numbers |
| GET | /groups | List magic groups |
| GET | /open-positions | Get open positions |
| GET | /aggregates | Get period aggregates |
| GET | /deals | Get deals history |
| GET | /compare-deals | Compare deals between accounts |
| POST | /sync/open | Sync open positions |
| POST | /sync/history | Sync deals history |
| GET | /charts/config | Chart editor configuration |
| PUT | /charts/config | Update charts folder path |
| GET | /charts/folders | List profile folders |
| GET | /charts/sections | List editing sections |
| POST | /charts/validate | Validate section |
| POST | /charts/write/{id} | Write changes to file |

## Key Classes

- `MT5Connection`: Manages MT5 terminal connection (singleton)
- `MT5DataProvider`: Fetches trading data from MT5
- `MT5Calculator`: Trading calculations (balance, equity, margin)
- `SessionLocal`: SQLAlchemy database session

## Development

```bash
# Run tests
pytest

# Format code
black src/

# Type checking
mypy src/
```

## License

MIT License
