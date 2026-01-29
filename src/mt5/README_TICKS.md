# Модуль работы с тиковыми данными

## Описание

Модуль для загрузки, хранения и получения тиковых данных из MetaTrader 5.

## Основные компоненты

### 1. TickDatabaseManager (`src/database/tick_db_manager.py`)

Менеджер базы данных для хранения тиковых данных.

**База данных:** `ticks.db` (отдельный файл)

**Таблицы:**
- `ticks` - хранит тиковые данные (server, symbol, time, bid, ask, volume, flags)
- `tick_ranges` - отслеживает доступные диапазоны данных по месяцам

**Основные методы:**
- `init_database()` - инициализация БД
- `save_ticks(server, symbol, ticks)` - сохранение тиков
- `get_ticks(server, symbol, from_time, to_time)` - получение тиков из БД
- `get_missing_months(server, symbol, from_date, to_date)` - определение недостающих месяцев
- `get_available_ranges(server, symbol)` - получение доступных диапазонов

### 2. MT5TickProvider (`src/mt5/tick_data.py`)

Провайдер для получения тиков из MT5 и работы с БД.

**Основные методы:**
- `get_ticks_from_mt5(symbol, from_date, to_date, account)` - получение тиков из MT5
- `download_and_save_ticks(symbol, from_date, to_date, account, auto_fill_months)` - загрузка и сохранение тиков
- `get_ticks_from_db(symbol, from_date, to_date, server, account)` - получение тиков из БД (с автодогрузкой)
- `get_high_low_prices(symbol, from_date, to_date, account)` - получение HIGH/LOW цен

## Использование

### Базовый пример

```python
from src.mt5.tick_data import mt5_tick_provider
from datetime import datetime

# Загрузка тиков за сентябрь 2024
from_date = datetime(2024, 9, 1)
to_date = datetime(2024, 9, 30, 23, 59, 59)

result = mt5_tick_provider.download_and_save_ticks(
    symbol="EURUSD",
    from_date=from_date,
    to_date=to_date,
    auto_fill_months=True  # Автоматически догружает недостающие месяцы
)

print(f"Загружено тиков: {result['ticks_downloaded']}")
```

### Получение тиков из БД

```python
# Автоматически догрузит недостающие данные, если нужно
ticks = mt5_tick_provider.get_ticks_from_db(
    symbol="EURUSD",
    from_date=datetime(2024, 9, 13, 0, 0, 0),
    to_date=datetime(2024, 9, 13, 23, 59, 59)
)

for tick in ticks:
    print(f"Time: {datetime.fromtimestamp(tick['time'])}, "
          f"Bid: {tick['bid']}, Ask: {tick['ask']}")
```

### Получение HIGH/LOW цен

```python
high_low = mt5_tick_provider.get_high_low_prices(
    symbol="EURUSD",
    from_date=datetime(2024, 9, 13, 0, 0, 0),
    to_date=datetime(2024, 9, 13, 23, 59, 59)
)

print(f"HIGH: {high_low['high']}, LOW: {high_low['low']}")
```

## Особенности

1. **Автоматическая догрузка по месяцам**: Если запрашиваются данные за 13 сентября 2024, а в БД есть только данные за 2025 год, система автоматически загрузит весь сентябрь 2024.

2. **Разделение по серверам и символам**: Данные хранятся с привязкой к серверу MT5 и символу, что позволяет работать с несколькими серверами одновременно.

3. **Оптимизация хранения**: Используются индексы для быстрого поиска, данные хранятся в компактном формате.

4. **Отслеживание диапазонов**: Система отслеживает, какие месяцы уже загружены, чтобы избежать повторной загрузки.

## Тестирование

Запуск теста:
```bash
python tests/test_tick_data.py
```

Тест проверяет:
- Инициализацию БД
- Загрузку тиков из MT5
- Сохранение в БД
- Получение данных из БД
- Определение недостающих месяцев
- Получение HIGH/LOW цен

