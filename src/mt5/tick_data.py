"""
MT5 Tick Data Provider
Handles downloading and storing tick data from MetaTrader 5
"""

import MetaTrader5 as mt5
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from ..config.settings import Config
from ..database.tick_db_manager import tick_db_manager
from .mt5_client import MT5Connection
from ..utils.logger import get_logger

logger = get_logger()


class MT5TickProvider:
    """Provides tick data from MetaTrader 5"""
    
    def __init__(self):
        self.connection = MT5Connection()
    
    def get_ticks_from_mt5(self, symbol: str, from_date: datetime, 
                          to_date: datetime, account: Dict[str, Any] = None) -> Optional[List]:
        """
        Get ticks from MT5 terminal for the specified symbol and date range
        
        Args:
            symbol: Trading symbol (e.g., 'EURUSD')
            from_date: Start date (local time)
            to_date: End date (local time)
            account: Account info dict (optional)
            
        Returns:
            List of tick objects or None if error
        """
        if not self.connection.initialize(account):
            logger.error("get_ticks_from_mt5: failed to initialize MT5 connection")
            return None
        
        # Convert local time to UTC for MT5 API
        from_date_utc = from_date - timedelta(hours=Config.LOCAL_TIMESHIFT)
        to_date_utc = to_date - timedelta(hours=Config.LOCAL_TIMESHIFT)
        
        logger.info(
            "get_ticks_from_mt5: request ticks %s - %s (UTC)",
            from_date_utc.strftime("%Y-%m-%d %H:%M:%S"),
            to_date_utc.strftime("%Y-%m-%d %H:%M:%S"),
        )
        
        # Check if symbol is available
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            logger.error("get_ticks_from_mt5: symbol not found in MT5: %s", symbol)
            self.connection.shutdown()
            return None
        
        if not symbol_info.visible:
            logger.warning("get_ticks_from_mt5: symbol not visible in Market Watch: %s", symbol)
            if not mt5.symbol_select(symbol, True):
                logger.error("get_ticks_from_mt5: failed to add symbol to Market Watch: %s", symbol)
                self.connection.shutdown()
                return None
        
        # Get ticks from MT5
        ticks = mt5.copy_ticks_range(
            symbol,
            from_date_utc,
            to_date_utc,
            mt5.COPY_TICKS_ALL
        )
        
        error_code = mt5.last_error()
        # Check if it's actually an error (not success)
        # In MT5: code 0 or 1 with 'Success' message means success
        # Only show error if code > 1 or message is not 'Success'
        if error_code[0] > 1 or (error_code[0] != 0 and error_code[1] != "Success"):
            logger.warning("get_ticks_from_mt5: MT5 error while fetching ticks: %s", error_code)
        
        self.connection.shutdown()
        
        if ticks is None:
            logger.error("get_ticks_from_mt5: MT5 returned None for ticks")
            return None
        
        ticks_list = list(ticks)
        if len(ticks_list) == 0:
            logger.warning("get_ticks_from_mt5: MT5 returned empty ticks list")
        
        return ticks_list
    
    def get_server_name(self, account: Dict[str, Any] = None) -> Optional[str]:
        """Get server name from account info"""
        if not self.connection.initialize(account):
            return None
        
        account_info = self.connection.get_account_info()
        self.connection.shutdown()
        
        if account_info:
            return getattr(account_info, 'server', None)
        return None
    
    def download_and_save_ticks(self, symbol: str, from_date: datetime, 
                                to_date: datetime, account: Dict[str, Any] = None,
                                auto_fill_months: bool = True) -> Dict[str, Any]:
        """
        Download ticks from MT5 and save to database
        
        Args:
            symbol: Trading symbol
            from_date: Start date (local time)
            to_date: End date (local time)
            account: Account info dict (optional)
            auto_fill_months: If True, automatically download missing months
            
        Returns:
            Dict with download statistics
        """
        # Get server name
        server = self.get_server_name(account)
        if not server:
            # Try to get from account dict
            server = account.get('server', 'unknown') if account else 'unknown'
        
        # Initialize database if needed
        tick_db_manager.init_database(server)
        
        result = {
            "server": server,
            "symbol": symbol,
            "from_date": from_date,
            "to_date": to_date,
            "ticks_downloaded": 0,
            "months_processed": [],
            "errors": []
        }
        
        if auto_fill_months:
            # Get missing months in requested range
            missing_months = tick_db_manager.get_missing_months(
                server, symbol, from_date, to_date
            )
            
            if missing_months:
                # Determine download range for continuous data:
                # - If no data exists: download from first missing month to current moment
                # - If data exists: download from first missing month to first available month
                #   (to fill gaps and ensure continuous series)
                first_missing = missing_months[0]
                first_missing_date = datetime(first_missing[0], first_missing[1], 1)
                
                # Check if we have any data
                first_available = tick_db_manager.get_first_available_month(server, symbol)
                
                if first_available is None:
                    # No data exists - download from first missing month to current moment
                    download_to = datetime.now()
                    logger.info(
                        "download_and_save_ticks: no DB data, downloading from %s to now",
                        first_missing_date.strftime("%Y-%m"),
                    )
                else:
                    # Data exists - download from first missing month to first available month
                    # This ensures continuous series without gaps
                    first_available_date = datetime(first_available[0], first_available[1], 1)
                    download_to = first_available_date - timedelta(seconds=1)
                    logger.info(
                        "download_and_save_ticks: DB has data, downloading from %s to %s for continuous series",
                        first_missing_date.strftime("%Y-%m"),
                        first_available_date.strftime("%Y-%m"),
                    )
                
                # Generate all months from first missing to download_to
                months_to_download = []
                current = first_missing_date
                while current <= download_to:
                    months_to_download.append((current.year, current.month))
                    # Move to next month
                    if current.month == 12:
                        current = datetime(current.year + 1, 1, 1)
                    else:
                        current = datetime(current.year, current.month + 1, 1)
                
                # Download data for each month
                # For new months: load full month
                # For existing months (current month update): load from last tick to now
                for year, month in months_to_download:
                    try:
                        # Check if this month already exists in DB (needs update, not full load)
                        month_key = (year, month)
                        available_ranges = tick_db_manager.get_available_ranges(server, symbol)
                        existing_range = next((r for r in available_ranges 
                                             if r["year"] == year and r["month"] == month), None)
                        
                        now = datetime.now()
                        is_current_month = (year == now.year and month == now.month)
                        
                        if existing_range and existing_range.get('last_tick_time'):
                            # Month exists - load only missing data
                            # UTC timestamp нужно конвертировать правильно: fromtimestamp с timezone.utc
                            from datetime import timezone as tz
                            last_tick_dt_utc = datetime.fromtimestamp(existing_range['last_tick_time'], tz=tz.utc)
                            # Convert to local time (UTC+LOCAL_TIMESHIFT)
                            last_tick_dt_local = last_tick_dt_utc.replace(tzinfo=None) + timedelta(hours=Config.LOCAL_TIMESHIFT)
                            
                            if is_current_month:
                                # Current month - load from last tick to now
                                month_start = last_tick_dt_local + timedelta(seconds=1)  # Start from next second after last tick
                                month_end = datetime.now()
                            else:
                                # Past month - load from last tick to end of month
                                month_start = last_tick_dt_local + timedelta(seconds=1)
                                if month == 12:
                                    month_end = datetime(year + 1, 1, 1) - timedelta(seconds=1)
                                else:
                                    month_end = datetime(year, month + 1, 1) - timedelta(seconds=1)
                            
                            # Don't load if no time has passed
                            if month_start >= month_end:
                                logger.info(
                                    "download_and_save_ticks: month %d-%02d already up to date (last tick %s)",
                                    year,
                                    month,
                                    last_tick_dt_local.strftime("%Y-%m-%d %H:%M:%S"),
                                )
                                continue
                            
                            logger.info(
                                "download_and_save_ticks: updating month %d-%02d for %s on %s: %s - %s",
                                year,
                                month,
                                symbol,
                                server,
                                month_start.strftime("%Y-%m-%d %H:%M:%S"),
                                month_end.strftime("%Y-%m-%d %H:%M:%S"),
                            )
                        else:
                            # New month - load full month
                            month_start = datetime(year, month, 1)
                            # Last day of month (23:59:59)
                            if month == 12:
                                month_end = datetime(year + 1, 1, 1) - timedelta(seconds=1)
                            else:
                                month_end = datetime(year, month + 1, 1) - timedelta(seconds=1)
                            
                            # For the last month, don't go beyond current moment
                            if month_end > datetime.now():
                                month_end = datetime.now()
                            
                            logger.info(
                                "download_and_save_ticks: downloading ticks for %s on %s: month %s (%s - %s)",
                                symbol,
                                server,
                                month_start.strftime("%Y-%m"),
                                month_start.strftime("%Y-%m-%d"),
                                month_end.strftime("%Y-%m-%d"),
                            )
                        
                        ticks = self.get_ticks_from_mt5(symbol, month_start, month_end, account)
                        
                        if ticks:
                            tick_db_manager.save_ticks(server, symbol, ticks)
                            result["ticks_downloaded"] += len(ticks)
                            result["months_processed"].append({
                                "year": year,
                                "month": month,
                                "ticks": len(ticks)
                            })
                            logger.info(
                                "download_and_save_ticks: downloaded %d ticks for %s",
                                len(ticks),
                                month_start.strftime("%Y-%m"),
                            )
                        else:
                            result["errors"].append(f"No ticks for {year}-{month:02d}")
                            logger.warning(
                                "download_and_save_ticks: no ticks found for %d-%02d",
                                year,
                                month,
                            )
                    except Exception as e:
                        error_msg = f"Error loading {year}-{month:02d}: {str(e)}"
                        result["errors"].append(error_msg)
                        logger.error("download_and_save_ticks: %s", error_msg)
                        import traceback
                        traceback.print_exc()
        else:
            # Download only for the specified range
            # But if we're in current month, make sure we don't go beyond now
            actual_to_date = to_date
            if to_date > datetime.now():
                actual_to_date = datetime.now()
            
            # Для надежности: если запрашиваем до конца дня (23:59:59), расширяем запрос
            # до начала следующего дня в UTC, чтобы гарантировать получение всех тиков
            # Проверяем, является ли actual_to_date концом дня (23:59:59)
            if actual_to_date.hour == 23 and actual_to_date.minute == 59 and actual_to_date.second == 59:
                # Конвертируем в UTC
                actual_to_date_utc_naive = actual_to_date - timedelta(hours=Config.LOCAL_TIMESHIFT)
                # Запрашиваем до начала следующего дня в UTC
                next_day_start_utc = actual_to_date_utc_naive.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
                # Конвертируем обратно в локальное время
                next_day_start_local = next_day_start_utc + timedelta(hours=Config.LOCAL_TIMESHIFT)
                # Но не выходим за пределы текущего момента
                if next_day_start_local <= datetime.now():
                    actual_to_date = next_day_start_local
                    logger.debug(f"download_and_save_ticks: Расширен запрос до начала следующего дня для гарантии получения всех тиков: "
                               f"{actual_to_date} (было: {to_date})")
            
            ticks = self.get_ticks_from_mt5(symbol, from_date, actual_to_date, account)
            if ticks:
                tick_db_manager.save_ticks(server, symbol, ticks)
                result["ticks_downloaded"] = len(ticks)
                result["months_processed"].append({
                    "from": from_date.strftime('%Y-%m-%d'),
                    "to": actual_to_date.strftime('%Y-%m-%d'),
                    "ticks": len(ticks)
                })
                logger.info(
                    "download_and_save_ticks: downloaded %d ticks for %s - %s",
                    len(ticks),
                    from_date.strftime("%Y-%m-%d"),
                    actual_to_date.strftime("%Y-%m-%d"),
                )
            else:
                result["errors"].append(f"No ticks for {from_date} - {actual_to_date}")
                logger.warning(
                    "download_and_save_ticks: no ticks found for %s - %s",
                    from_date.strftime("%Y-%m-%d"),
                    actual_to_date.strftime("%Y-%m-%d"),
                )
        
        return result
    
    def get_ticks_from_db(self, symbol: str, from_date: datetime, 
                         to_date: datetime, server: str = None,
                         account: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Get ticks from database (with auto-download if missing)
        
        Args:
            symbol: Trading symbol
            from_date: Start date (local time)
            to_date: End date (local time)
            server: Server name (optional, will be detected if not provided)
            account: Account info dict (optional)
            
        Returns:
            List of tick dictionaries
        """
        # Get server name if not provided
        if not server:
            server = self.get_server_name(account)
            if not server:
                server = account.get('server', 'unknown') if account else 'unknown'
        
        # Initialize database for this server
        tick_db_manager.init_database(server)
        
        # Ограничиваем to_date до предыдущего дня (не включая сегодня) перед проверкой missing_months
        now = datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        original_to_date = to_date
        
        if to_date >= today_start:
            # Ограничиваем до конца предыдущего дня
            yesterday_end = today_start - timedelta(seconds=1)
            if to_date > yesterday_end:
                to_date = yesterday_end
                logger.info(f"get_ticks_from_db: Ограничиваем запрос до предыдущего дня: {to_date} (было: {original_to_date})")
        
        # Check for missing data and download if needed
        # For continuous series, we need to ensure all months in the requested range are loaded
        # Use a retry mechanism to avoid race conditions
        max_retries = 3
        for attempt in range(max_retries):
            # Проверяем missing_months с ограниченным to_date
            missing_months = tick_db_manager.get_missing_months(server, symbol, from_date, to_date)
            if not missing_months:
                # No missing months, break out of retry loop
                break
            
            if attempt > 0:
                # Wait a bit before retry (another thread might be loading data)
                import time
                time.sleep(0.5)
            
            logger.warning(
                "get_ticks_from_db: missing months for %s on %s: %s",
                symbol,
                server,
                missing_months,
            )
            logger.info("get_ticks_from_db: starting download of missing full months")
            
            # Calculate the range: from first missing month to last missing month
            first_missing = missing_months[0]
            last_missing = missing_months[-1]
            
            # Start from the beginning of the first missing month
            download_from = datetime(first_missing[0], first_missing[1], 1)
            
            # Determine download_to based on whether we're requesting current/future months
            # Use the same 'now' and 'today_start' from above (already defined)
            is_current_or_future_month = (
                (last_missing[0] > now.year) or 
                (last_missing[0] == now.year and last_missing[1] >= now.month)
            )
            
            if is_current_or_future_month:
                # Для текущего месяца, загружаем только до конца предыдущего дня
                # Устанавливаем время до конца предыдущего дня (23:59:59 локальное)
                # Но для надежности запрашиваем тики до начала следующего дня в UTC
                # Это гарантирует, что мы получим все тики до конца дня
                # Конвертируем конец предыдущего дня в UTC
                yesterday_end_local = today_start - timedelta(seconds=1)  # 23:59:59 локальное
                yesterday_end_utc_naive = yesterday_end_local - timedelta(hours=Config.LOCAL_TIMESHIFT)  # 20:59:59 UTC
                # Запрашиваем до начала следующего дня в UTC (00:00:00 следующего дня)
                # Это гарантирует получение всех тиков до конца предыдущего дня
                next_day_start_utc = yesterday_end_utc_naive.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
                # Конвертируем обратно в локальное время
                download_to = next_day_start_utc + timedelta(hours=Config.LOCAL_TIMESHIFT)
                # Но не выходим за пределы конца предыдущего дня (на всякий случай)
                if download_to > today_start:
                    download_to = today_start - timedelta(seconds=1)
                
                logger.info(f"get_ticks_from_db: Загрузка текущего месяца ограничена до предыдущего дня: {download_to} "
                           f"(запрашиваем до начала следующего дня в UTC для гарантии получения всех тиков)")
                logger.info(
                    "get_ticks_from_db: current month download limited to previous day: %s",
                    download_to.strftime("%Y-%m-%d %H:%M:%S"),
                )
            else:
                # For historical months, download to the end of the last missing month
                if last_missing[1] == 12:
                    download_to = datetime(last_missing[0] + 1, 1, 1) - timedelta(seconds=1)
                else:
                    download_to = datetime(last_missing[0], last_missing[1] + 1, 1) - timedelta(seconds=1)
                
                # Don't go beyond current moment
                if download_to > datetime.now():
                    download_to = datetime.now()
                
                logger.info(
                    "get_ticks_from_db: downloading historical data from %s to %s",
                    download_from.strftime("%Y-%m"),
                    download_to.strftime("%Y-%m-%d"),
                )
            
            try:
                # Download full months to ensure continuous series
                # Use auto_fill_months=False to avoid recursive logic issues
                # We've already determined what needs to be downloaded
                self.download_and_save_ticks(symbol, download_from, download_to, account, auto_fill_months=False)
            except Exception as e:
                logger.warning(f"Ошибка при загрузке тиков (попытка {attempt + 1}/{max_retries}): {e}")
                if attempt == max_retries - 1:
                    # Last attempt failed, raise the exception
                    raise
        
        # Get ticks from database
        return tick_db_manager.get_ticks(server, symbol, from_date, to_date)
    
    def get_high_low_prices(self, symbol: str, from_date: datetime, 
                           to_date: datetime, server: str = None,
                           account: Dict[str, Any] = None) -> Dict[str, float]:
        """
        Get HIGH and LOW prices from tick data for the specified period
        
        Args:
            symbol: Trading symbol
            from_date: Start date (local time)
            to_date: End date (local time)
            server: Server name (optional, will be detected from account if not provided)
            account: Account info dict (optional)
            
        Returns:
            Dict with 'high' and 'low' prices (using ask for high, bid for low)
        """
        # Ensure server is determined
        if not server:
            server = self.get_server_name(account)
            if not server:
                server = account.get('server', None) if account else None
                if not server:
                    raise ValueError("Server must be provided or determined from account info")
        
        ticks = self.get_ticks_from_db(symbol, from_date, to_date, server=server, account=account)
        
        if not ticks:
            return {"high": None, "low": None}
        
        # get_ticks_from_db уже фильтрует тики по времени при запросе к БД
        # Тики из БД имеют UTC timestamps, и они уже отфильтрованы по нужному диапазону
        # Используем тики напрямую без дополнительной фильтрации
        
        # Find highest ask and lowest bid
        high = max(tick["ask"] for tick in ticks)
        low = min(tick["bid"] for tick in ticks)
        
        return {"high": high, "low": low}


# Global tick provider instance
mt5_tick_provider = MT5TickProvider()

