# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-01-29

### Added
- **FastAPI Backend** with REST API for MT5 data
- **Next.js Frontend** with modern React UI
- **MT5 Integration** via MetaTrader5 Python library
- **SQLite Database** with SQLAlchemy ORM
- **Service Layer** for business logic separation
  - `AccountService` - account management
  - `SyncService` - MT5 synchronization
  - `GroupService` - magic groups management
- **Security Features**
  - Fernet encryption for MT5 credentials
  - IP whitelist middleware
  - CORS configuration
- **Dashboard Features**
  - Real-time open positions monitoring
  - Historical deals analysis with period filters (Today, 3 Days, Week, Month, Year, Custom)
  - Magic number labels and organization
  - Magic groups for aggregated statistics
  - Multiple account support
- **Frontend Components**
  - TopBar with account selector and period filters
  - OpenPositionsBar with floating P/L
  - MainResults with grouped/individual magic view
  - Settings dialog with password management
  - Labels and Groups management dialogs
- **Async MT5 Operations** using ThreadPoolExecutor to prevent event loop blocking

### Architecture
- Clean separation of concerns: API → Services → Repositories
- CQRS pattern with `readmodels/` for queries
- Timezone utilities for MT5 server time handling
- Centralized logging with timestamps

### Technical Stack
- **Backend**: Python 3.10+, FastAPI, SQLAlchemy 2.0, MetaTrader5
- **Frontend**: Next.js 14, React 18, TypeScript, Tailwind CSS
- **Database**: SQLite (local development)

---

## Previous Development

This is a complete rewrite from the original Streamlit-based dashboard. The new architecture provides:
- Better performance with async operations
- Modern React UI instead of Streamlit
- Proper separation of concerns
- Improved security with credential encryption
- Multi-account support with localStorage persistence
