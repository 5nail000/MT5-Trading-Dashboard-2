"""
Database operations for compressed tick data storage using BLOB + zlib
Stores ticks in daily batches, one DB file per server
"""

import sqlite3
import zlib
import struct
import os
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from contextlib import contextmanager
from ..config.settings import Config


class CompressedTickDatabaseManager:
    """Manages compressed tick data database operations with daily batches"""
    
    def __init__(self, data_dir: str = "ticks_data"):
        self.data_dir = os.path.join(data_dir, "compressed")
        # Ensure data directory exists
        os.makedirs(self.data_dir, exist_ok=True)
    
    def get_db_path(self, server: str) -> str:
        """Get database file path for a server"""
        # Sanitize server name for filename
        safe_server_name = server.replace('/', '_').replace('\\', '_').replace(':', '_')
        return os.path.join(self.data_dir, f"{safe_server_name}.db")
    
    @contextmanager
    def get_connection(self, server: str):
        """Context manager for database connections"""
        db_path = self.get_db_path(server)
        conn = sqlite3.connect(db_path)
        try:
            yield conn
        finally:
            conn.close()
    
    def init_database(self, server: str):
        """Initialize tick database tables for a server"""
        with self.get_connection(server) as conn:
            cursor = conn.cursor()
            
            # Table for storing compressed tick batches (daily)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tick_batches
                (
                    symbol TEXT NOT NULL,
                    batch_date INTEGER NOT NULL,  -- date as YYYYMMDD integer
                    batch_start_time INTEGER NOT NULL,  -- first tick timestamp in batch
                    batch_end_time INTEGER NOT NULL,    -- last tick timestamp in batch
                    compressed_data BLOB NOT NULL,     -- zlib compressed tick data
                    tick_count INTEGER NOT NULL,        -- number of ticks in batch
                    PRIMARY KEY(symbol, batch_date)
                )
            """)
            
            # Index for faster queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_batches_symbol_time
                ON tick_batches(symbol, batch_start_time, batch_end_time)
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
    
    def _date_to_int(self, dt: datetime) -> int:
        """Convert datetime to YYYYMMDD integer"""
        return dt.year * 10000 + dt.month * 100 + dt.day
    
    def _int_to_date(self, date_int: int) -> datetime:
        """Convert YYYYMMDD integer to datetime"""
        year = date_int // 10000
        month = (date_int // 100) % 100
        day = date_int % 100
        return datetime(year, month, day)
    
    def _compress_ticks(self, ticks: List[Dict[str, Any]]) -> bytes:
        """
        Compress ticks using struct + zlib
        Format: [count(4)][time(4)][bid(4)][ask(4)][volume(4)][flags(4)]...
        """
        if not ticks:
            return b''
        
        # Pack data: count + ticks
        # Each tick: time(4) + bid(4) + ask(4) + volume(4) + flags(4) = 20 bytes
        # Format: I (time) + f (bid) + f (ask) + f (volume) + I (flags) = IffII
        data = struct.pack('I', len(ticks))  # count (4 bytes)
        
        for tick in ticks:
            data += struct.pack('IffII',
                int(tick['time']),
                float(tick['bid']),
                float(tick['ask']),
                int(tick.get('volume', 0)),  # volume is int, not float
                int(tick.get('flags', 0))
            )
        
        # Compress with zlib (level 6 - balance between speed and compression)
        compressed = zlib.compress(data, level=6)
        return compressed
    
    def _decompress_ticks(self, compressed_data: bytes) -> List[Dict[str, Any]]:
        """Decompress ticks from BLOB"""
        if not compressed_data:
            return []
        
        # Decompress
        data = zlib.decompress(compressed_data)
        
        # Read count
        tick_count = struct.unpack('I', data[:4])[0]
        
        ticks = []
        offset = 4
        # Format: I (time) + f (bid) + f (ask) + I (volume) + I (flags) = 20 bytes
        for _ in range(tick_count):
            tick_data = struct.unpack('IffII', data[offset:offset+20])
            ticks.append({
                'time': tick_data[0],
                'bid': tick_data[1],
                'ask': tick_data[2],
                'volume': int(tick_data[3]),
                'flags': int(tick_data[4])
            })
            offset += 20
        
        return ticks
    
    def save_ticks(self, server: str, symbol: str, ticks: List[Any]):
        """
        Save ticks to database, grouping by days and compressing
        ticks: list of MT5 tick objects (with time, bid, ask, volume, flags attributes)
        """
        if not ticks:
            return
        
        # Initialize database if needed
        self.init_database(server)
        
        with self.get_connection(server) as conn:
            cursor = conn.cursor()
            
            # Group ticks by day
            daily_batches = {}
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
                
                # Convert timestamp to datetime for date grouping
                tick_dt = datetime.fromtimestamp(tick_time)
                date_int = self._date_to_int(tick_dt)
                
                # Group by date
                if date_int not in daily_batches:
                    daily_batches[date_int] = []
                
                daily_batches[date_int].append({
                    'time': tick_time,
                    'bid': tick_bid,
                    'ask': tick_ask,
                    'volume': tick_volume,
                    'flags': tick_flags
                })
                
                # Track month ranges
                year = tick_dt.year
                month = tick_dt.month
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
            
            # Save each daily batch
            for date_int, batch_ticks in daily_batches.items():
                # Sort by time
                batch_ticks.sort(key=lambda x: x['time'])
                
                # Compress
                compressed = self._compress_ticks(batch_ticks)
                
                batch_start = batch_ticks[0]['time']
                batch_end = batch_ticks[-1]['time']
                
                # Insert or replace batch
                cursor.execute("""
                    INSERT OR REPLACE INTO tick_batches
                    (symbol, batch_date, batch_start_time, batch_end_time, compressed_data, tick_count)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (symbol, date_int, batch_start, batch_end, compressed, len(batch_ticks)))
            
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
                else:
                    final_first = data['first_time']
                    final_last = data['last_time']
                    final_count = data['count']
                
                cursor.execute("""
                    INSERT OR REPLACE INTO tick_ranges
                    (symbol, year, month, first_tick_time, last_tick_time, tick_count)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (symbol, year, month, final_first, final_last, final_count))
            
            conn.commit()
    
    def get_ticks(self, server: str, symbol: str, 
                  from_time: datetime, to_time: datetime) -> List[Dict[str, Any]]:
        """Get ticks from compressed batches"""
        self.init_database(server)
        
        from_timestamp = int((from_time - timedelta(hours=Config.LOCAL_TIMESHIFT)).timestamp())
        to_timestamp = int((to_time - timedelta(hours=Config.LOCAL_TIMESHIFT)).timestamp())
        
        with self.get_connection(server) as conn:
            cursor = conn.cursor()
            
            # Find all batches that intersect with requested range
            cursor.execute("""
                SELECT compressed_data FROM tick_batches
                WHERE symbol = ? 
                AND batch_start_time <= ? AND batch_end_time >= ?
                ORDER BY batch_start_time
            """, (symbol, to_timestamp, from_timestamp))
            
            all_ticks = []
            for (compressed_data,) in cursor.fetchall():
                # Decompress batch
                batch_ticks = self._decompress_ticks(compressed_data)
                # Filter by time range
                filtered = [t for t in batch_ticks 
                           if from_timestamp <= t['time'] <= to_timestamp]
                all_ticks.extend(filtered)
            
            return sorted(all_ticks, key=lambda x: x['time'])
    
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
        
        # Get available months from DB with their last tick times
        available_ranges = self.get_available_ranges(server, symbol)
        available_months = {}
        for r in available_ranges:
            key = (r["year"], r["month"])
            if key not in available_months:
                available_months[key] = r
        
        # Check each required month
        missing = []
        now = datetime.now()
        
        for year, month in required_months:
            month_key = (year, month)
            
            if month_key not in available_months:
                # Month completely missing
                missing.append((year, month))
            else:
                # Month exists, but check if we need more data
                range_info = available_months[month_key]
                last_tick_time = range_info.get('last_tick_time')
                
                if last_tick_time:
                    last_tick_dt = datetime.fromtimestamp(last_tick_time)
                    # Convert to local time for comparison
                    last_tick_dt_local = last_tick_dt + timedelta(hours=Config.LOCAL_TIMESHIFT)
                    
                    # If we need data beyond what we have
                    # For current or future months, always check if we need update
                    if (year == now.year and month == now.month):
                        # Current month - check if we need data after the last tick
                        if to_date > last_tick_dt_local:
                            missing.append((year, month))  # Need to update current month
                    elif (year > now.year) or (year == now.year and month > now.month):
                        # Future month - should not happen, but include it
                        missing.append((year, month))
                    # For past months, if to_date is beyond last_tick, we need more data
                    elif to_date > last_tick_dt_local:
                        missing.append((year, month))
                else:
                    # Month exists but has no data
                    missing.append((year, month))
        
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
        Пересчитать диапазоны на основе реальных данных в батчах
        
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
            
            # Пересчитать диапазоны на основе батчей
            if symbol:
                query = """
                    SELECT 
                        symbol,
                        CAST(strftime('%Y', datetime(batch_start_time, 'unixepoch')) AS INTEGER) as year,
                        CAST(strftime('%m', datetime(batch_start_time, 'unixepoch')) AS INTEGER) as month,
                        MIN(batch_start_time) as first_tick_time,
                        MAX(batch_end_time) as last_tick_time,
                        SUM(tick_count) as tick_count
                    FROM tick_batches
                    WHERE symbol = ?
                    GROUP BY symbol, year, month
                """
                cursor.execute(query, (symbol,))
            else:
                query = """
                    SELECT 
                        symbol,
                        CAST(strftime('%Y', datetime(batch_start_time, 'unixepoch')) AS INTEGER) as year,
                        CAST(strftime('%m', datetime(batch_start_time, 'unixepoch')) AS INTEGER) as month,
                        MIN(batch_start_time) as first_tick_time,
                        MAX(batch_end_time) as last_tick_time,
                        SUM(tick_count) as tick_count
                    FROM tick_batches
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
            
            cursor.execute("SELECT COUNT(*) FROM tick_batches")
            total_batches = cursor.fetchone()[0]
            
            cursor.execute("SELECT SUM(tick_count) FROM tick_batches")
            total_ticks = cursor.fetchone()[0] or 0
            
            cursor.execute("SELECT COUNT(DISTINCT symbol) FROM tick_batches")
            unique_symbols = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM tick_ranges")
            total_ranges = cursor.fetchone()[0]
            
            db_path = self.get_db_path(server)
            size_bytes = os.path.getsize(db_path) if os.path.exists(db_path) else 0
            
            return {
                "server": server,
                "total_batches": total_batches,
                "total_ticks": total_ticks,
                "unique_symbols": unique_symbols,
                "total_month_ranges": total_ranges,
                "database_path": db_path,
                "database_size_mb": size_bytes / (1024 * 1024) if size_bytes > 0 else 0
            }


# Global compressed tick database manager instance
compressed_tick_db_manager = CompressedTickDatabaseManager()

