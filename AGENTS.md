# AGENTS.md - LLM Context for MT5 Trading Dashboard

This file provides detailed context for AI assistants working on this project.

## Project Overview

**MT5 Trading Dashboard** is a personal trading statistics viewer for MetaTrader 5. It syncs trading data from MT5 terminal and displays it in a modern web interface.

**Use Case**: Personal home project for viewing trading history and statistics. NOT a commercial product, so:
- Security focus is light (no complex auth, just optional IP whitelist)
- Single user assumed
- May run on VPS for remote access

## Technology Stack

### Backend (Python)
- **FastAPI** - REST API framework
- **SQLAlchemy 2.0** - ORM with SQLite
- **MetaTrader5** - Official MT5 Python library (Windows only)
- **Pydantic** - Data validation
- **Cryptography** - Fernet encryption for credentials

### Frontend (Next.js)
- **Next.js 14** with App Router
- **React 18** with hooks
- **TypeScript**
- **Tailwind CSS** - Styling
- **html2canvas** - Screenshot functionality

## Architecture Principles

### Service Layer Pattern
API endpoints are "thin" - they validate input and call services:
```
API (main.py) → Services → Database/MT5
```

Services:
- `AccountService` - Account CRUD, credentials management
- `SyncService` - MT5 data synchronization (async with ThreadPoolExecutor)
- `GroupService` - Magic groups and labels
- `ChartService` - Chart file (.chr) editing for EA parameters

### CQRS (Light)
- **Commands**: Services handle writes
- **Queries**: `readmodels/dashboard_queries.py` handles complex reads

### MT5 Threading
MT5 API is blocking and not async-compatible. Solution:
```python
_mt5_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="mt5_")

async def sync_history(...):
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(_mt5_executor, blocking_mt5_call)
```

### Time Handling
- **MT5 API**: Returns times in UTC
- **Display**: Local time (UTC + LOCAL_TIMESHIFT from config)
- **Database**: Stores UTC
- Use `src/utils/timezone.py` for conversions

## Key Concepts

### Magic Numbers
MT5 uses "magic numbers" to identify trading strategies/EAs. Dashboard allows:
- Labeling magics with human-readable names
- Grouping magics for aggregated statistics
- Filtering by individual magics or groups

### Data Flow

1. **Sync** - User clicks "Sync History"
2. MT5 terminal must be running and logged in
3. `SyncService` fetches deals from MT5 API
4. Deals saved to SQLite via SQLAlchemy
5. Frontend fetches aggregated data via REST API

### State Management (Frontend)

**localStorage** (`mt5_dashboard_state`):
- Selected account, period, filters
- Magic labels (duplicated in DB)
- Layout margins
- View preferences per account

**Server (SQLite)**:
- Accounts, deals, positions
- Magic labels, groups, assignments
- Credentials (encrypted)

⚠️ Labels are stored in BOTH places. localStorage takes priority on load.

## File Structure Details

### Backend Entry Points
- `src/api/main.py` - FastAPI app, all endpoints
- `uvicorn src.api.main:app` - How to run

### Key Files
| File | Purpose |
|------|---------|
| `src/services/sync_service.py` | Async MT5 sync operations |
| `src/services/chart_service.py` | Chart file (.chr) editing operations |
| `src/mt5/mt5_client.py` | MT5Connection singleton, data fetching |
| `src/db_sa/models.py` | SQLAlchemy models (Account, Deal, Magic, ChartSection, etc.) |
| `src/readmodels/dashboard_queries.py` | Complex aggregation queries |
| `dashboard-next/src/app/page.tsx` | Main dashboard page (large file) |
| `dashboard-next/src/app/create-charts/page.tsx` | Chart parameter editor page |
| `dashboard-next/src/lib/api.ts` | API client functions |

### Frontend Components
| Component | Purpose |
|-----------|---------|
| `TopBar.tsx` | Account selector, period filters, sync button |
| `OpenPositionsBar.tsx` | Floating P/L display |
| `MainResults.tsx` | Magic/group statistics cards |
| `SettingsDialog.tsx` | Account settings, password |
| `GroupsDialog.tsx` | Magic group management |
| `LabelsDialog.tsx` | Magic label editing |

## Common Tasks

### Add New API Endpoint
1. Add Pydantic model in `main.py` (if needed)
2. Add service method in appropriate service
3. Add endpoint in `main.py`
4. Add API function in `dashboard-next/src/lib/api.ts`

### Add New Period Filter
1. Add to `periodPresets` in `TopBar.tsx`
2. Add to `periodLabels` in `TopBar.tsx`
3. Add case in `buildPeriod()` in `page.tsx`

### Fix Magic Selection Bug
The logic in `loadAccountData()` handles what happens when switching periods:
- If selected magics become inactive, reset to all active magics
- See `shouldResetMagics` logic

## Known Issues / TODOs

1. **Deals Page** (`/deals`) - Basic implementation, needs work
2. **Balance Chart** (`/balance-chart`) - Basic implementation, needs work
3. **Tick Data** - Drawdown calculation requires tick data collection (disabled by default)
4. **Tests** - Minimal coverage, mostly manual testing

## Environment Variables

```env
# Required
MT5_CRED_KEY=<fernet-key>        # For encrypting MT5 passwords

# Optional
LOCAL_TIMESHIFT=3                 # Hours offset from UTC
ALLOWED_ORIGINS=http://localhost:3000
IP_WHITELIST=                     # Empty = allow all
DRAWDOWN_ENABLED=false            # Requires tick data
LOG_LEVEL=INFO
```

## Development Notes

- **Logging**: Always use `logger = get_logger()`, outputs start with timestamp
- **Commits**: Use `commit-message.txt` (in .gitignore) for commit messages
- **User prefers**: Russian language responses, practical solutions over theoretical

## Database Schema (Main Tables)

```
accounts (account_id PK, label, history_start_date)
account_info (account_id PK FK, account_number, leverage, server)
account_credentials (account_id PK FK, login, server, password_encrypted)
deals (account_id, ticket_id PK, magic, profit, time, symbol, volume, ...)
magics (account_id, id PK, label)
magic_groups (id PK, account_id, name, label2, font_color, fill_color)
magic_group_assignments (account_id, group_id, magic_id)
open_positions (account_id, ticket_id PK, magic, profit, ...)
chart_configs (id PK, charts_path)
chart_sections (id PK, folder_name, validation_line1, validation_line2, param_key, param_value, order_index)
```
