"""
Database operations for tick data storage (uncompressed)
Stores ticks directly, one DB file per server
"""

import sqlite3
import os
import threading
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from contextlib import contextmanager
from ..config.settings import Config
from ..utils.logger import get_logger

logger = get_logger()


class TickDatabaseManager:
    """Manages uncompressed tick data database operations"""
    
    def __init__(self, data_dir: str = "ticks_data"):
        self.data_dir = data_dir
        # Ensure data directory exists
        os.makedirs(self.data_dir, exist_ok=True)
        # Lock for thread-safe database operations
        self._locks = {}  # {server: threading.Lock()}
        self._locks_lock = threading.Lock()  # Lock for accessing _locks dict
    
    def get_db_path(self, server: str) -> str:
        """Get database file path for a server"""
        # Sanitize server name for filename
        safe_server_name = server.replace('/', '_').replace('\\', '_').replace(':', '_')
        return os.path.join(self.data_dir, f"{safe_server_name}.db")
    
    def _get_lock(self, server: str) -> threading.Lock:
        """Get or create a lock for a specific server"""
        with self._locks_lock:
            if server not in self._locks:
                self._locks[server] = threading.Lock()
            return self._locks[server]
    
    @contextmanager
    def get_connection(self, server: str, timeout: float = 30.0):
        """Context manager for database connections with timeout"""
        db_path = self.get_db_path(server)
        conn = sqlite3.connect(db_path, timeout=timeout)
        try:
            yield conn
        finally:
            conn.close()
    
    def init_database(self, server: str):
        """Initialize tick database tables for a server"""
        with self.get_connection(server) as conn:
            cursor = conn.cursor()
            
            # Table for storing tick data
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ticks
                (
                    symbol TEXT NOT NULL,
                    time INTEGER NOT NULL,
                    bid REAL NOT NULL,
                    ask REAL NOT NULL,
                    volume INTEGER NOT NULL,
                    flags INTEGER,
                    PRIMARY KEY(symbol, time)
                )
            """)
            
            # Index for faster queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_ticks_symbol_time
                ON ticks(symbol, time)
            """)
            
            # Table for tracking available data ranges per symbol
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tick_ranges
                (
                    symbol TEXT NOT NULL,
                    year INTEGER NOT NULL,
                    month INTEGER NOT NULL,
                    first_tick_time INTEGER,
                    last_tick_time INTEGER,
                    tick_count INTEGER DEFAULT 0,
                    PRIMARY KEY(symbol, year, month)
                )
            """)
            
            # Index for range queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_ranges_symbol
                ON tick_ranges(symbol, year, month)
            """)
            
            conn.commit()
    
    def save_ticks(self, server: str, symbol: str, ticks: List[Any]):
        """
        Save ticks to database
        ticks: list of MT5 tick objects (with time, bid, ask, volume, flags attributes)
        """
        if not ticks:
            logger.debug(f"save_ticks: Пустой список тиков для {symbol} на {server}")
            return
        
        logger.info(f"save_ticks: Начинаю сохранение {len(ticks)} тиков для {symbol} на {server}")
        
        # Initialize database if needed
        self.init_database(server)
        
        # Use lock to prevent concurrent writes
        lock = self._get_lock(server)
        with lock:
            with self.get_connection(server) as conn:
                cursor = conn.cursor()
                
                # Prepare data for bulk insert
                tick_data = []
                months_data = {}  # Track data per month for ranges
                
                for tick in ticks:
                    # Extract tick data
                    try:
                        if hasattr(tick, 'dtype') and tick.dtype.names:
                            tick_time = int(tick['time'])
                            tick_bid = float(tick['bid'])
                            tick_ask = float(tick['ask'])
                            tick_volume = int(tick['volume'])
                            tick_flags = int(tick['flags'] if 'flags' in tick.dtype.names else 0)
                        elif isinstance(tick, dict):
                            tick_time = int(tick['time'])
                            tick_bid = float(tick['bid'])
                            tick_ask = float(tick['ask'])
                            tick_volume = int(tick.get('volume', 0))
                            tick_flags = int(tick.get('flags', 0))
                        elif hasattr(tick, 'time'):
                            tick_time = int(tick.time)
                            tick_bid = float(tick.bid)
                            tick_ask = float(tick.ask)
                            tick_volume = int(tick.volume)
                            tick_flags = int(getattr(tick, 'flags', 0))
                        else:
                            tick_time = int(tick[0])
                            tick_bid = float(tick[1])
                            tick_ask = float(tick[2])
                            tick_volume = int(tick[3])
                            tick_flags = int(tick[4] if len(tick) > 4 else 0)
                    except (AttributeError, KeyError, IndexError, TypeError) as e:
                        print(f"⚠️ Ошибка доступа к полям тика: {e}, тип: {type(tick)}")
                        continue
                    
                    tick_dt = datetime.fromtimestamp(tick_time)
                    year = tick_dt.year
                    month = tick_dt.month
                    
                    # Store tick data
                    tick_data.append((
                        symbol,
                        tick_time,
                        tick_bid,
                        tick_ask,
                        tick_volume,
                        tick_flags
                    ))
                    
                    # Track month ranges
                    month_key = (year, month)
                    if month_key not in months_data:
                        months_data[month_key] = {
                            'first_time': tick_time,
                            'last_time': tick_time,
                            'count': 0
                        }
                    else:
                        months_data[month_key]['first_time'] = min(
                            months_data[month_key]['first_time'], tick_time
                        )
                        months_data[month_key]['last_time'] = max(
                            months_data[month_key]['last_time'], tick_time
                        )
                    months_data[month_key]['count'] += 1
                
                # Логируем максимальные времена для каждого месяца для диагностики
                for (year, month), data in months_data.items():
                    from datetime import timezone as tz
                    first_time_local = datetime.fromtimestamp(data['first_time'], tz=tz.utc).replace(tzinfo=None) + timedelta(hours=Config.LOCAL_TIMESHIFT)
                    last_time_local = datetime.fromtimestamp(data['last_time'], tz=tz.utc).replace(tzinfo=None) + timedelta(hours=Config.LOCAL_TIMESHIFT)
                    logger.info(f"save_ticks: Месяц {year}-{month:02d}: {data['count']} тиков, "
                               f"период {first_time_local} (UTC: {data['first_time']}) - "
                               f"{last_time_local} (UTC: {data['last_time']})")
                
                logger.info(f"save_ticks: Подготовлено {len(tick_data)} тиков для сохранения, месяцы: {list(months_data.keys())}")
                
                # Bulk insert ticks (ignore duplicates)
                cursor.executemany("""
                    INSERT OR IGNORE INTO ticks 
                    (symbol, time, bid, ask, volume, flags)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, tick_data)
                
                # Note: executemany doesn't return rowcount reliably, so we log what we tried to insert
                logger.info(f"save_ticks: Выполнена вставка {len(tick_data)} тиков в БД")
                
                # Update month ranges
                for (year, month), data in months_data.items():
                    cursor.execute("""
                        SELECT first_tick_time, last_tick_time, tick_count FROM tick_ranges
                        WHERE symbol=? AND year=? AND month=?
                    """, (symbol, year, month))
                    existing = cursor.fetchone()
                    
                    if existing:
                        existing_first = existing[0]
                        existing_last = existing[1]
                        existing_count = existing[2]
                        
                        final_first = min(existing_first, data['first_time']) if existing_first else data['first_time']
                        final_last = max(existing_last, data['last_time']) if existing_last else data['last_time']
                        final_count = existing_count + data['count']
                        
                        # Конвертируем для логирования в локальное время
                        from datetime import timezone as tz
                        existing_last_local = datetime.fromtimestamp(existing_last, tz=tz.utc).replace(tzinfo=None) + timedelta(hours=Config.LOCAL_TIMESHIFT)
                        final_last_local = datetime.fromtimestamp(final_last, tz=tz.utc).replace(tzinfo=None) + timedelta(hours=Config.LOCAL_TIMESHIFT)
                        logger.info(f"save_ticks: Обновление диапазона для {symbol} {year}-{month:02d}: "
                                   f"было {existing_count} тиков до {existing_last_local} (UTC timestamp: {existing_last}), "
                                   f"стало {final_count} тиков до {final_last_local} (UTC timestamp: {final_last})")
                    else:
                        final_first = data['first_time']
                        final_last = data['last_time']
                        final_count = data['count']
                        
                        # Конвертируем для логирования в локальное время
                        from datetime import timezone as tz
                        final_first_local = datetime.fromtimestamp(final_first, tz=tz.utc).replace(tzinfo=None) + timedelta(hours=Config.LOCAL_TIMESHIFT)
                        final_last_local = datetime.fromtimestamp(final_last, tz=tz.utc).replace(tzinfo=None) + timedelta(hours=Config.LOCAL_TIMESHIFT)
                        logger.info(f"save_ticks: Создание нового диапазона для {symbol} {year}-{month:02d}: "
                                  f"{final_count} тиков, период {final_first_local} (UTC timestamp: {final_first}) - "
                                  f"{final_last_local} (UTC timestamp: {final_last})")
                    
                    cursor.execute("""
                        INSERT OR REPLACE INTO tick_ranges
                        (symbol, year, month, first_tick_time, last_tick_time, tick_count)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (symbol, year, month, final_first, final_last, final_count))
                
                conn.commit()
                logger.info(f"save_ticks: Успешно сохранено {len(tick_data)} тиков для {symbol} на {server}, обновлено диапазонов: {len(months_data)}")
    
    def get_ticks(self, server: str, symbol: str, 
                  from_time: datetime, to_time: datetime) -> List[Dict[str, Any]]:
        """
        Get ticks from database
        
        Args:
            from_time: Start time in LOCAL time (naive datetime, represents UTC+LOCAL_TIMESHIFT)
            to_time: End time in LOCAL time (naive datetime, represents UTC+LOCAL_TIMESHIFT)
        
        Note: datetime objects represent local time (UTC+LOCAL_TIMESHIFT).
        Ticks in DB are stored with UTC timestamps.
        To convert local time to UTC timestamp:
        - Create UTC datetime by subtracting LOCAL_TIMESHIFT from local time
        - Use timezone.utc to ensure correct conversion
        """
        self.init_database(server)
        
        from datetime import timezone
        
        # from_time represents local time (UTC+LOCAL_TIMESHIFT), naive datetime
        # To get UTC datetime: subtract LOCAL_TIMESHIFT from local time
        # Then mark it as UTC timezone for correct timestamp conversion
        from_time_utc_naive = from_time - timedelta(hours=Config.LOCAL_TIMESHIFT)
        to_time_utc_naive = to_time - timedelta(hours=Config.LOCAL_TIMESHIFT)
        
        # Now mark as UTC timezone for correct timestamp conversion
        from_time_utc = from_time_utc_naive.replace(tzinfo=timezone.utc)
        to_time_utc = to_time_utc_naive.replace(tzinfo=timezone.utc)
        
        from_timestamp = int(from_time_utc.timestamp())
        to_timestamp = int(to_time_utc.timestamp())
        
        with self.get_connection(server) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT time, bid, ask, volume, flags FROM ticks
                WHERE symbol = ? AND time BETWEEN ? AND ?
                ORDER BY time
            """, (symbol, from_timestamp, to_timestamp))
            
            results = cursor.fetchall()
            return [
                {
                    "time": row[0],
                    "bid": row[1],
                    "ask": row[2],
                    "volume": row[3],
                    "flags": row[4]
                }
                for row in results
            ]
    
    def get_available_ranges(self, server: str, symbol: str) -> List[Dict[str, Any]]:
        """Get available data ranges for symbol"""
        self.init_database(server)
        
        with self.get_connection(server) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT year, month, first_tick_time, last_tick_time, tick_count
                FROM tick_ranges
                WHERE symbol = ?
                ORDER BY year, month
            """, (symbol,))
            
            results = cursor.fetchall()
            return [
                {
                    "year": row[0],
                    "month": row[1],
                    "first_tick_time": row[2],
                    "last_tick_time": row[3],
                    "tick_count": row[4]
                }
                for row in results
            ]
    
    def get_missing_months(self, server: str, symbol: str, 
                          from_date: datetime, to_date: datetime) -> List[Tuple[int, int]]:
        """
        Get list of missing months (year, month) for the given date range
        Also checks if current month needs update (has data but not up to requested date)
        """
        self.init_database(server)
        
        logger.debug(f"get_missing_months: Проверка для {symbol} на {server}, период {from_date} - {to_date}")
        
        # Get all months in the range
        required_months = set()
        current = datetime(from_date.year, from_date.month, 1)
        end = datetime(to_date.year, to_date.month, 1)
        
        while current <= end:
            required_months.add((current.year, current.month))
            if current.month == 12:
                current = datetime(current.year + 1, 1, 1)
            else:
                current = datetime(current.year, current.month + 1, 1)
        
        logger.debug(f"get_missing_months: Требуемые месяцы: {sorted(required_months)}")
        
        # Get available months from DB with their last tick times
        available_ranges = self.get_available_ranges(server, symbol)
        available_months = {}
        for r in available_ranges:
            key = (r["year"], r["month"])
            if key not in available_months:
                available_months[key] = r
        
        logger.debug(f"get_missing_months: Доступные месяцы в БД: {list(available_months.keys())}")
        
        # Check each required month
        missing = []
        now = datetime.now()
        
        for year, month in required_months:
            month_key = (year, month)
            
            if month_key not in available_months:
                # Month completely missing
                logger.debug(f"get_missing_months: Месяц {year}-{month:02d} полностью отсутствует")
                missing.append((year, month))
            else:
                # Month exists, but check if we need more data
                range_info = available_months[month_key]
                last_tick_time = range_info.get('last_tick_time')
                
                if last_tick_time:
                    # UTC timestamp нужно конвертировать правильно: fromtimestamp с timezone.utc
                    from datetime import timezone as tz
                    last_tick_dt_utc = datetime.fromtimestamp(last_tick_time, tz=tz.utc)
                    # Convert to local time for comparison (UTC+LOCAL_TIMESHIFT)
                    last_tick_dt_local = last_tick_dt_utc.replace(tzinfo=None) + timedelta(hours=Config.LOCAL_TIMESHIFT)
                    
                    logger.debug(f"get_missing_months: Месяц {year}-{month:02d} существует, "
                                f"последний тик UTC timestamp: {last_tick_time}, "
                                f"UTC datetime: {last_tick_dt_utc.replace(tzinfo=None)}, "
                                f"локальное время: {last_tick_dt_local}, "
                                f"запрашивается до: {to_date}")
                    
                    # If we need data beyond what we have
                    # For current or future months, always check if we need update
                    if (year == now.year and month == now.month):
                        # Current month - check if we have data up to end of previous day
                        # We don't load current day ticks, so we only need data up to yesterday
                        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
                        yesterday_end = today_start - timedelta(seconds=1)
                        
                        # Конвертируем yesterday_end в UTC timestamp для прямого сравнения с last_tick_time (UTC timestamp)
                        # yesterday_end - локальное время (UTC+LOCAL_TIMESHIFT)
                        # Чтобы получить UTC timestamp: вычитаем LOCAL_TIMESHIFT и конвертируем
                        yesterday_end_utc_naive = yesterday_end - timedelta(hours=Config.LOCAL_TIMESHIFT)
                        yesterday_end_utc = yesterday_end_utc_naive.replace(tzinfo=tz.utc)
                        yesterday_end_utc_timestamp = int(yesterday_end_utc.timestamp())
                        
                        # Сравниваем UTC timestamps напрямую, чтобы избежать ошибок конвертации
                        time_diff_seconds = last_tick_time - yesterday_end_utc_timestamp
                        # Допуск: если разница менее 5 минут, считаем что данных достаточно
                        # (MT5 может не вернуть тики точно до указанного времени)
                        tolerance_seconds = 5 * 60  # 5 минут
                        
                        logger.debug(f"get_missing_months: Сравнение для текущего месяца {year}-{month:02d} (UTC timestamps): "
                                    f"последний тик UTC timestamp: {last_tick_time} ({last_tick_dt_local} локальное), "
                                    f"конец предыдущего дня UTC timestamp: {yesterday_end_utc_timestamp} ({yesterday_end} локальное), "
                                    f"разница: {time_diff_seconds} секунд ({time_diff_seconds/3600:.2f} часов), "
                                    f"допуск: {tolerance_seconds} секунд")
                        
                        # Если последний тик >= конца предыдущего дня в UTC (с учетом допуска), данных достаточно
                        if last_tick_time >= (yesterday_end_utc_timestamp - tolerance_seconds):
                            # We have data up to end of previous day (within tolerance), no need to update
                            if time_diff_seconds >= 0:
                                logger.debug(f"get_missing_months: Текущий месяц {year}-{month:02d} имеет данные до конца предыдущего дня "
                                            f"(последний тик UTC: {last_tick_time}, локальное: {last_tick_dt_local}, "
                                            f"требуется до UTC: {yesterday_end_utc_timestamp}, локальное: {yesterday_end})")
                            else:
                                logger.debug(f"get_missing_months: Текущий месяц {year}-{month:02d} имеет данные достаточно близко к концу предыдущего дня "
                                            f"(разница: {abs(time_diff_seconds)} секунд, в пределах допуска {tolerance_seconds} секунд)")
                            # Don't add to missing - we don't load current day ticks
                        else:
                            # We need data up to end of previous day
                            logger.info(f"get_missing_months: Текущий месяц {year}-{month:02d} нуждается в обновлении: "
                                      f"последний тик UTC timestamp: {last_tick_time} ({last_tick_dt_local} локальное), "
                                      f"требуется до UTC timestamp: {yesterday_end_utc_timestamp} ({yesterday_end} локальное), "
                                      f"не хватает: {abs(time_diff_seconds)} секунд ({abs(time_diff_seconds)/3600:.2f} часов), "
                                      f"превышает допуск {tolerance_seconds} секунд")
                            missing.append((year, month))
                    elif (year > now.year) or (year == now.year and month > now.month):
                        # Future month - should not happen, but include it
                        logger.warning(f"get_missing_months: Будущий месяц {year}-{month:02d} помечен как недостающий")
                        missing.append((year, month))
                    # For past months, check if we have sufficient data
                    # For historical months, we need to check if the last tick is reasonably close to the end of the month
                    # OR if the requested to_date is beyond what we have
                    else:
                        # Convert to_date to UTC timestamp for comparison
                        to_date_utc_naive = to_date - timedelta(hours=Config.LOCAL_TIMESHIFT)
                        to_date_utc = to_date_utc_naive.replace(tzinfo=tz.utc)
                        to_date_utc_timestamp = int(to_date_utc.timestamp())
                        
                        # Calculate end of month in local time
                        if month == 12:
                            month_end_local = datetime(year + 1, 1, 1, 0, 0, 0) - timedelta(seconds=1)
                        else:
                            month_end_local = datetime(year, month + 1, 1, 0, 0, 0) - timedelta(seconds=1)
                        
                        # Convert month end to UTC timestamp for comparison
                        month_end_utc_naive = month_end_local - timedelta(hours=Config.LOCAL_TIMESHIFT)
                        month_end_utc = month_end_utc_naive.replace(tzinfo=tz.utc)
                        month_end_utc_timestamp = int(month_end_utc.timestamp())
                        
                        # Compare UTC timestamps directly
                        time_diff_from_month_end = last_tick_time - month_end_utc_timestamp
                        time_diff_from_to_date = last_tick_time - to_date_utc_timestamp
                        
                        # Для исторических месяцев используем более мягкий допуск:
                        # - Если последний тик в пределах 3 дней от конца месяца, считаем что данных достаточно
                        #   (учитываем выходные и праздники, когда торговли нет)
                        # - Или если запрашиваемый to_date не выходит за пределы имеющихся данных более чем на 1 день
                        tolerance_for_month_end = 3 * 24 * 3600  # 3 дня допуск для конца месяца (выходные/праздники)
                        tolerance_for_to_date = 1 * 24 * 3600  # 1 день допуск для запрашиваемой даты
                        
                        logger.debug(f"get_missing_months: Проверка исторического месяца {year}-{month:02d}: "
                                   f"последний тик UTC timestamp: {last_tick_time} ({last_tick_dt_local} локальное), "
                                   f"конец месяца UTC timestamp: {month_end_utc_timestamp} ({month_end_local} локальное), "
                                   f"запрашивается до UTC timestamp: {to_date_utc_timestamp} ({to_date} локальное), "
                                   f"разница от конца месяца: {time_diff_from_month_end} секунд ({time_diff_from_month_end/3600:.2f} часов), "
                                   f"разница от запрашиваемой даты: {time_diff_from_to_date} секунд ({time_diff_from_to_date/3600:.2f} часов)")
                        
                        # Проверяем, нужны ли данные:
                        # 1. Если последний тик значительно раньше конца месяца (более 3 дней) И
                        # 2. Запрашиваемая дата выходит за пределы имеющихся данных (более 1 дня)
                        needs_update = False
                        if time_diff_from_month_end < -tolerance_for_month_end:
                            # Последний тик более чем на 3 дня раньше конца месяца
                            if time_diff_from_to_date < -tolerance_for_to_date:
                                # И запрашиваемая дата выходит за пределы имеющихся данных более чем на 1 день
                                needs_update = True
                                logger.info(f"get_missing_months: Исторический месяц {year}-{month:02d} нуждается в обновлении: "
                                          f"последний тик {last_tick_dt_local} (UTC: {last_tick_time}), "
                                          f"конец месяца {month_end_local} (UTC: {month_end_utc_timestamp}), "
                                          f"запрашивается до {to_date} (UTC: {to_date_utc_timestamp}), "
                                          f"не хватает от конца месяца: {abs(time_diff_from_month_end)} секунд ({abs(time_diff_from_month_end)/3600:.2f} часов), "
                                          f"не хватает от запрашиваемой даты: {abs(time_diff_from_to_date)} секунд ({abs(time_diff_from_to_date)/3600:.2f} часов)")
                            else:
                                logger.debug(f"get_missing_months: Исторический месяц {year}-{month:02d} актуален "
                                           f"(последний тик {last_tick_dt_local} достаточно близок к запрашиваемой дате {to_date}, "
                                           f"разница: {abs(time_diff_from_to_date)} секунд, в пределах допуска {tolerance_for_to_date} секунд)")
                        else:
                            logger.debug(f"get_missing_months: Исторический месяц {year}-{month:02d} актуален "
                                       f"(последний тик {last_tick_dt_local} достаточно близок к концу месяца {month_end_local}, "
                                       f"разница: {abs(time_diff_from_month_end)} секунд, в пределах допуска {tolerance_for_month_end} секунд)")
                        
                        if needs_update:
                            missing.append((year, month))
                else:
                    # Month exists but has no data
                    logger.warning(f"get_missing_months: Месяц {year}-{month:02d} существует в БД, но не имеет данных")
                    missing.append((year, month))
        
        logger.info(f"get_missing_months: Для {symbol} на {server} недостающие месяцы: {missing}")
        return sorted(list(set(missing)))
    
    def get_first_available_month(self, server: str, symbol: str) -> Optional[Tuple[int, int]]:
        """Get first available month (year, month) for symbol"""
        ranges = self.get_available_ranges(server, symbol)
        if not ranges:
            return None
        
        earliest = min(ranges, key=lambda x: (x["year"], x["month"]))
        return (earliest["year"], earliest["month"])
    
    def recalculate_ranges(self, server: str, symbol: str = None):
        """
        Пересчитать диапазоны на основе реальных данных в ticks
        
        Args:
            server: Сервер для пересчета
            symbol: Если указан, пересчитать только для этого символа
        """
        self.init_database(server)
        
        with self.get_connection(server) as conn:
            cursor = conn.cursor()
            
            # Удалить существующие диапазоны
            if symbol:
                cursor.execute("DELETE FROM tick_ranges WHERE symbol=?", (symbol,))
            else:
                cursor.execute("DELETE FROM tick_ranges")
            
            # Пересчитать диапазоны на основе тиков
            if symbol:
                query = """
                    SELECT 
                        symbol,
                        CAST(strftime('%Y', datetime(time, 'unixepoch')) AS INTEGER) as year,
                        CAST(strftime('%m', datetime(time, 'unixepoch')) AS INTEGER) as month,
                        MIN(time) as first_tick_time,
                        MAX(time) as last_tick_time,
                        COUNT(*) as tick_count
                    FROM ticks
                    WHERE symbol = ?
                    GROUP BY symbol, year, month
                """
                cursor.execute(query, (symbol,))
            else:
                query = """
                    SELECT 
                        symbol,
                        CAST(strftime('%Y', datetime(time, 'unixepoch')) AS INTEGER) as year,
                        CAST(strftime('%m', datetime(time, 'unixepoch')) AS INTEGER) as month,
                        MIN(time) as first_tick_time,
                        MAX(time) as last_tick_time,
                        COUNT(*) as tick_count
                    FROM ticks
                    GROUP BY symbol, year, month
                """
                cursor.execute(query)
            
            ranges = cursor.fetchall()
            
            # Вставить пересчитанные диапазоны
            for sym, yr, mn, first_time, last_time, count in ranges:
                cursor.execute("""
                    INSERT INTO tick_ranges
                    (symbol, year, month, first_tick_time, last_tick_time, tick_count)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (sym, yr, mn, int(first_time), int(last_time), count))
            
            conn.commit()
            print(f"✅ Пересчитано диапазонов: {len(ranges)}")
    
    def get_statistics(self, server: str) -> Dict[str, Any]:
        """Get database statistics for a server"""
        self.init_database(server)
        
        with self.get_connection(server) as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM ticks")
            total_ticks = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(DISTINCT symbol) FROM ticks")
            unique_symbols = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM tick_ranges")
            total_ranges = cursor.fetchone()[0]
            
            db_path = self.get_db_path(server)
            size_bytes = os.path.getsize(db_path) if os.path.exists(db_path) else 0
            
            return {
                "server": server,
                "total_ticks": total_ticks,
                "unique_symbols": unique_symbols,
                "total_month_ranges": total_ranges,
                "database_path": db_path,
                "database_size_mb": size_bytes / (1024 * 1024) if size_bytes > 0 else 0
            }


# Global uncompressed tick database manager instance
tick_db_manager = TickDatabaseManager()

