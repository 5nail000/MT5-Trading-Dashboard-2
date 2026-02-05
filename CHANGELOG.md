# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.0] - 2026-02-04

### Added
- **Compare Accounts** - новая страница для сравнения торговой истории между двумя аккаунтами
  - Выбор двух аккаунтов для сравнения
  - Фильтр периода (Today, 3 Days, Week, Month, Year)
  - Выбор magic для сравнения (показывает только общие магики между аккаунтами)
  - Настраиваемая погрешность времени для сопоставления сделок (по умолчанию 1 сек)
  - Таблица с параллельным отображением данных обоих аккаунтов
  - Цветовое выделение несопоставленных сделок (оранжевый - только в acc1, красный - только в acc2)
  - Summary со статистикой: matched, account1_only, account2_only, P/L по каждому аккаунту

### Backend
- Новая функция `get_compared_deals()` в `dashboard_queries.py` для сопоставления сделок по `entry_time`
- Новый API эндпоинт: `GET /compare-deals` с параметрами:
  - `account_id_1`, `account_id_2` - ID аккаунтов
  - `magic` - номер магика
  - `from_date`, `to_date` - период
  - `tolerance_seconds` - погрешность времени (default: 1)

### Frontend
- Новая кнопка "Compare Accounts" в панели Actions (SidePanel)
- Новая страница `/compare` с интерфейсом сравнения
- Новые TypeScript типы: `CompareDeal`, `CompareDealPair`, `CompareSummary`, `CompareResult`

---

## [1.1.0] - 2026-01-30

### Added
- **Create Charts** - новая страница для редактирования параметров советников в .chr файлах MT5
  - Панели по папкам профилей (например Real_Trade_last, Real_Trade_Lord)
  - Секции для изменения параметров советников (Lot, SL, TP и т.д.)
  - Двухуровневая валидация файлов (Validation Line 1 + 2 для точного поиска)
  - Автоматическое определение файла и текущего значения параметра
  - Цветовая индикация: зелёный (найдено), жёлтый (значение уже соответствует), красный (не найдено)
  - Кнопка Write для записи изменений в .chr файлы (UCS-2 LE кодировка)
  - Автосохранение состояния в localStorage
  - Компактный дизайн для отображения множества секций
  - Автозамена запятой на точку в числовых значениях (0,02 → 0.02)

### Backend
- Новые модели БД: `ChartConfig`, `ChartSection`
- Новый сервис: `chart_service.py` для работы с .chr файлами
- Новые API эндпоинты:
  - `GET/PUT /charts/config` - конфигурация пути к папке charts
  - `GET /charts/folders` - список папок профилей
  - `GET/POST/PUT/DELETE /charts/sections` - CRUD секций
  - `POST /charts/validate` - валидация секции
  - `POST /charts/write/{id}` - запись секции в файл
  - `POST /charts/write-folder/{folder}` - запись всех секций папки

### Frontend
- Новая кнопка "Create Charts" в панели Actions (SidePanel)
- Новая страница `/create-charts` с компактным редактором

---

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
