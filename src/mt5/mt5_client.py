"""
MetaTrader 5 integration module
"""

import MetaTrader5 as mt5
import psutil
import atexit
import signal
import threading
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any, Tuple
from ..config.settings import Config
from ..utils.logger import get_logger

logger = get_logger()


class MT5Connection:
    """
    Singleton класс для управления соединением с MetaTrader 5
    
    Обеспечивает:
    - Единое соединение на все время работы приложения
    - Автоматическую проверку и восстановление соединения
    - Отслеживание текущего аккаунта
    - Корректное завершение при закрытии приложения
    - Thread safety
    """
    
    _instance = None
    _lock = threading.Lock()
    _initialized = False
    
    def __new__(cls):
        """Singleton pattern - создает только один экземпляр"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._is_initialized = False
                    cls._instance._current_account = None
                    cls._instance._initialization_lock = threading.Lock()
                    cls._instance._signal_handlers_registered = False
                    # Регистрируем cleanup при завершении приложения
                    atexit.register(cls._instance._cleanup)
                    # Регистрируем обработчики сигналов только в главном потоке
                    # (signal.signal работает только в главном потоке)
                    if Config.MT5_REGISTER_SIGNAL_HANDLERS and threading.current_thread() is threading.main_thread():
                        try:
                            signal.signal(signal.SIGTERM, cls._instance._signal_handler)
                            signal.signal(signal.SIGINT, cls._instance._signal_handler)
                            cls._instance._signal_handlers_registered = True
                        except (ValueError, AttributeError):
                            # Если не удалось зарегистрировать (не главный поток или Windows),
                            # полагаемся только на atexit
                            pass
        return cls._instance
    
    def _cleanup(self):
        """Закрытие соединения при завершении приложения"""
        with self._initialization_lock:
            if self._is_initialized:
                try:
                    mt5.shutdown()
                except Exception:
                    pass  # Игнорируем ошибки при завершении
                finally:
                    self._is_initialized = False
                    self._current_account = None
    
    def _signal_handler(self, signum, frame):
        """Обработчик сигналов завершения (Ctrl+C, закрытие окна)"""
        logger.info(f"MT5Connection: received signal {signum}, shutting down")
        self._cleanup()
        return
    
    def check_mt5_process(self) -> List[psutil.Process]:
        """Check for running MT5 processes"""
        processes = []
        try:
            for proc in psutil.process_iter():
                try:
                    if 'terminal64.exe' in proc.name():
                        processes.append(proc)
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    # Процесс был закрыт или недоступен, пропускаем
                    continue
        except Exception:
            # Игнорируем ошибки при итерации процессов
            pass
        return processes
    
    def _is_connection_alive(self) -> bool:
        """Проверяет, действительно ли соединение активно"""
        if not self._is_initialized:
            return False
        try:
            # Пробуем получить информацию о терминале
            terminal_info = mt5.terminal_info()
            if terminal_info is None:
                return False
            # Проверяем, что терминал подключен
            return terminal_info.connected
        except (psutil.NoSuchProcess, psutil.AccessDenied, RuntimeError, Exception) as e:
            # Процесс был закрыт или произошла другая ошибка
            # Помечаем соединение как неактивное для переподключения
            self._is_initialized = False
            return False
    
    def _needs_reconnect(self, account: Dict[str, Any] = None) -> bool:
        """Проверяет, нужно ли переподключение"""
        # Если не инициализировано - нужно подключиться
        if not self._is_initialized:
            return True
        
        # Если соединение не активно - нужно переподключиться
        if not self._is_connection_alive():
            return True
        
        # Если указан другой аккаунт - нужно переподключиться
        if account is not None:
            current_login = self._current_account.get('login') if self._current_account else None
            if current_login != account.get('login'):
                return True
        
        return False
    
    def initialize(self, account: Dict[str, Any] = None) -> bool:
        """
        Инициализирует соединение с MT5
        
        Args:
            account: Словарь с данными аккаунта {'login', 'password', 'server'}
                    Если None, используется текущее соединение или создается новое без авторизации
        
        Returns:
            True если соединение успешно установлено, False в противном случае
        """
        with self._initialization_lock:
            # Проверяем, нужно ли переподключение
            if not self._needs_reconnect(account):
                return True
            
            # Если нужно переподключиться, закрываем старое соединение
            if self._is_initialized:
                try:
                    mt5.shutdown()
                except Exception:
                    pass
                self._is_initialized = False
                self._current_account = None
            
            # Ищем запущенные процессы MT5
            mt5_processes = self.check_mt5_process()
            terminal_path = None
            
            if mt5_processes:
                try:
                    terminal_path = mt5_processes[0].exe()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    # Процесс был закрыт между проверкой и использованием
                    terminal_path = None
            
            # Инициализируем соединение
            if terminal_path:
                logger.debug(f"Initializing MT5 connection with terminal path: {terminal_path}")
                if not mt5.initialize(terminal_path):
                    # Если не удалось с конкретным путем, пробуем без него
                    logger.warning("Failed to initialize with terminal path, trying default")
                    if not mt5.initialize():
                        logger.error("Failed to initialize MT5 connection")
                        return False
            else:
                logger.debug("Initializing MT5 connection (default path)")
                if not mt5.initialize():
                    logger.error("Failed to initialize MT5 connection")
                    return False
            
            # Авторизация, если указан аккаунт
            if account:
                logger.debug(f"Logging in to MT5 account: {account.get('login')} on {account.get('server')}")
                authorized = mt5.login(
                    account['login'], 
                    account['password'], 
                    account['server']
                )
                if not authorized:
                    error_code = mt5.last_error()
                    logger.error(f"Failed to login to MT5: error code {error_code}")
                    mt5.shutdown()
                    return False
                logger.info(f"Successfully logged in to MT5 account: {account.get('login')}")
                self._current_account = account.copy()
            else:
                # Если аккаунт не указан, проверяем, есть ли уже авторизованное соединение
                account_info = mt5.account_info()
                if account_info:
                    # Сохраняем информацию о текущем аккаунте
                    self._current_account = {
                        'login': account_info.login,
                        'server': account_info.server
                    }
            
            self._is_initialized = True
            return True
    
    def ensure_connected(self, account: Dict[str, Any] = None) -> bool:
        """
        Убеждается, что соединение активно, переподключается при необходимости
        
        Args:
            account: Данные аккаунта для переподключения (если нужно)
        
        Returns:
            True если соединение активно, False в противном случае
        """
        if self._needs_reconnect(account):
            # Если account не содержит password, передаем None
            # (соединение должно быть уже установлено)
            account_for_init = account
            if account and 'password' not in account:
                account_for_init = None
            return self.initialize(account_for_init)
        return True
    
    def shutdown(self):
        """Закрывает соединение (явно, если нужно)"""
        self._cleanup()
    
    def get_account_info(self) -> Optional[Any]:
        """
        Получает информацию об аккаунте
        
        Returns:
            Информация об аккаунте или None если соединение не активно
        """
        if not self.ensure_connected():
            return None
        try:
            return mt5.account_info()
        except Exception:
            return None
    
    @property
    def is_initialized(self) -> bool:
        """Проверяет, инициализировано ли соединение"""
        return self._is_initialized and self._is_connection_alive()


class MT5DataProvider:
    """Provides data from MetaTrader 5"""
    
    def __init__(self):
        self.connection = MT5Connection()  # Singleton - всегда один экземпляр
    
    def get_history(self, account: Dict[str, Any] = None, 
                   from_date: datetime = None, 
                   to_date: datetime = None) -> Tuple[Optional[List], Optional[Any]]:
        """Get trading history"""
        try:
            if from_date is None:
                from_date = datetime(2020, 1, 1)
            if to_date is None:
                to_date = datetime.now()
            
            logger.debug(f"Fetching history from {from_date} to {to_date}")

            # Convert to UTC for MT5 API. If datetimes are naive, assume they are
            # already in UTC (frontend sends UTC ISO strings).
            if from_date.tzinfo is not None:
                from_date_utc = from_date.astimezone(timezone.utc).replace(tzinfo=None)
            else:
                from_date_utc = from_date

            if to_date.tzinfo is not None:
                to_date_utc = to_date.astimezone(timezone.utc).replace(tzinfo=None)
            else:
                to_date_utc = to_date
            
            # Используем ensure_connected - соединение переиспользуется
            if not self.connection.ensure_connected(account):
                logger.error("MT5 connection not available")
                return None, None
            
            account_info = self.connection.get_account_info()
            if account_info is None:
                logger.error("Failed to get account info")
                return None, None
            
            deals = mt5.history_deals_get(from_date_utc, to_date_utc)
            if deals is None:
                error_code = mt5.last_error()
                logger.error(f"Failed to get history deals: error code {error_code}")
                return None, None
            
            logger.info(f"Retrieved {len(deals)} deals from MT5")
            # Не закрываем соединение - оно долгоживущее
            return deals, account_info
        
        except Exception as e:
            logger.error(f"Error in get_history: {e}", exc_info=True)
            return None, None
    
    def get_open_positions(self, account: Dict[str, Any] = None) -> Tuple[Optional[List], Optional[Any]]:
        """Get open positions"""
        # Используем ensure_connected - соединение переиспользуется
        if not self.connection.ensure_connected(account):
            return None, None
        
        account_info = self.connection.get_account_info()
        if account_info is None:
            return None, None
        
        positions = mt5.positions_get()
        # Не закрываем соединение - оно долгоживущее
        
        return list(positions), account_info


class MT5Calculator:
    """Calculates trading metrics"""
    
    @staticmethod
    def calculate_balance_at_date(target_date: datetime, deals: List, 
                                 initial_balance: float = None, 
                                 end_of_day: bool = False,
                                 use_exact_time: bool = False) -> float:
        """
        Вычисляет баланс на указанную дату
        
        Args:
            target_date: Дата и время, на которые нужно вычислить баланс
            deals: Список всех сделок из истории
            initial_balance: Начальный баланс (если None, используется 0)
            end_of_day: Если True - баланс на конец дня (23:59:59), 
                       если False - баланс на начало дня (00:00:00)
            use_exact_time: Если True - использует точное время из target_date,
                          если False - использует начало/конец дня
            
        Returns:
            Баланс на указанную дату и время
        """
        try:
            from ..utils.helpers import validation_utils
            
            # Validate inputs
            if not isinstance(target_date, datetime):
                logger.error(f"target_date must be a datetime object, got {type(target_date).__name__}")
                return initial_balance or 0.0
            
            is_valid, error_msg = validation_utils.validate_deals_list(deals)
            if not is_valid:
                logger.error(f"Invalid deals list: {error_msg}")
                return initial_balance or 0.0
            
            if initial_balance is not None and not isinstance(initial_balance, (int, float)):
                logger.error(f"initial_balance must be a number, got {type(initial_balance).__name__}")
                return 0.0
            
            logger.debug(f"Calculating balance at date: {target_date}, end_of_day={end_of_day}, use_exact_time={use_exact_time}")
            
            if not deals:
                logger.debug("No deals provided, returning initial balance")
                return initial_balance or 0.0
            
            # Если initial_balance не указан, используем 0 (начинаем с самого начала)
            if initial_balance is None:
                initial_balance = 0.0
            
            # Конвертируем местное время в UTC для сравнения с данными MT5
            if use_exact_time:
                # Используем точное время из target_date
                target_date_time = target_date
            elif end_of_day:
                # Используем конец дня (23:59:59) в местном времени
                target_date_time = target_date.replace(hour=23, minute=59, second=59)
            else:
                # Используем начало дня (00:00:00) в местном времени
                target_date_time = target_date.replace(hour=0, minute=0, second=0)
            
            # Вычитаем LOCAL_TIMESHIFT для конвертации локального времени в UTC
            target_date_utc = target_date_time - timedelta(hours=Config.LOCAL_TIMESHIFT)
            target_timestamp = target_date_utc.timestamp()
            
            # Сортируем сделки по времени
            sorted_deals = sorted(deals, key=lambda x: x.time)
            
            # Начинаем с начального баланса и добавляем сделки до указанной даты
            balance = initial_balance
            
            for deal in sorted_deals:
                # Пропускаем сделки после целевой даты
                if deal.time > target_timestamp:
                    break
                
                # Учитываем только сделки изменения баланса (type == 2)
                if deal.type == 2:
                    balance += deal.profit
                else:
                    # Для обычных сделок добавляем прибыль/убыток
                    balance += deal.profit + deal.commission + deal.swap
            
            logger.debug(f"Calculated balance: {balance:.2f} at {target_date}")
            return balance
        
        except Exception as e:
            logger.error(f"Error in calculate_balance_at_date: {e}", exc_info=True)
            return initial_balance or 0.0
    
    @staticmethod
    def calculate_open_profits_by_magics(positions: List) -> Dict[str, Any]:
        """Calculate open profits grouped by magic numbers"""
        magic_profits = {}
        magics_total = {}
        magic_symbol_type = {}
        
        for pos in positions:
            if pos.type == 0:  # Buy
                type_str = "Buy"
            elif pos.type == 1:  # Sell
                type_str = "Sell"
            else:
                continue
            
            magic_key = pos.magic
            symbol_key = pos.symbol
            full_key = (magic_key, symbol_key, type_str)
            
            # Initialize nested dict
            if magic_key not in magic_symbol_type:
                magic_symbol_type[magic_key] = {}
            if symbol_key not in magic_symbol_type[magic_key]:
                magic_symbol_type[magic_key][symbol_key] = {}
            if type_str not in magic_symbol_type[magic_key][symbol_key]:
                magic_symbol_type[magic_key][symbol_key][type_str] = 0.0
            
            profit = pos.profit + pos.swap
            magic_symbol_type[magic_key][symbol_key][type_str] += profit
            
            # Update totals
            if magic_key not in magics_total:
                magics_total[magic_key] = 0.0
            magics_total[magic_key] += profit
            
            if full_key not in magic_profits:
                magic_profits[full_key] = 0.0
            magic_profits[full_key] += profit
        
        total_floating = sum(magics_total.values())
        return {
            "by_magic": magics_total,
            "total_floating": total_floating,
            "detailed": magic_symbol_type
        }
    
    @staticmethod
    def calculate_by_magics(deals: List, symbol: str = None, 
                          from_date: datetime = None, 
                          to_date: datetime = None,
                          magic_groups: Optional[Dict[int, List[int]]] = None) -> Dict[str, Any]:
        """Calculate profits grouped by magic numbers or groups"""
        magic_profits = {}
        magics_summ = 0
        magic_total_sums = {}
        
        # Create reverse mapping: magic -> group_id (if grouped)
        magic_to_group = {}
        if magic_groups:
            for group_id, magics in magic_groups.items():
                for magic in magics:
                    magic_to_group[magic] = group_id
        
        # Create position_id -> magic mapping once for efficient lookup
        position_to_magic = {}
        for d in deals:
            if d.position_id != 0 and d.magic != 0:
                position_to_magic[d.position_id] = d.magic
        
        for deal in deals:
            # deal.time is UTC timestamp, convert to local time (UTC+LOCAL_TIMESHIFT) for comparison with from_date/to_date
            from datetime import timezone as tz
            deal_time_utc = datetime.fromtimestamp(deal.time, tz=tz.utc)
            deal_time = deal_time_utc.replace(tzinfo=None) + timedelta(hours=Config.LOCAL_TIMESHIFT)
            if deal.type == 2:  # Balance changes
                continue
            if from_date and deal_time < from_date:
                continue
            if to_date and deal_time > to_date:
                continue
            
            magic_key = deal.magic
            if magic_key == 0:
                # Use pre-built mapping for efficient lookup
                magic_key = position_to_magic.get(deal.position_id, 0)
            
            # If grouping is enabled, use group_id instead of magic_key
            display_key = magic_key
            if magic_groups and magic_key in magic_to_group:
                display_key = magic_to_group[magic_key]
            
            symbol_key = deal.symbol if symbol is None else symbol
            key = (display_key, symbol_key)
            
            if key not in magic_profits:
                magic_profits[key] = 0.0
            
            deal_profit = deal.profit + deal.commission + deal.swap
            magic_profits[key] += deal_profit
            magics_summ += deal_profit
            
            if display_key not in magic_total_sums:
                magic_total_sums[display_key] = 0.0
            magic_total_sums[display_key] += deal_profit
        
        magic_profits["Summ"] = magics_summ
        if magic_total_sums and magic_total_sums.get(0) is not None:
            magic_profits["Summ only magics"] = magics_summ - magic_total_sums[0]
        magic_profits["Total by Magic"] = magic_total_sums
        
        return magic_profits
    
    @staticmethod
    def get_positions_timeline(from_date: datetime, to_date: datetime, 
                               magics: List[int], deals: List,
                               account: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Получает серию временных промежутков с пулом позиций
        
        Args:
            from_date: Время начала среза (IN)
            to_date: Время конца среза (OUT)
            magics: Список мэджиков для фильтрации
            deals: Список всех сделок из истории (должен включать период до from_date)
            account: Информация об аккаунте (опционально, для получения баланса)
            
        Returns:
            Список словарей, каждый содержит:
            - 'aggregated_positions': список агрегированных позиций (через analyze_positions_pool)
            - 'time_in': время начала промежутка
            - 'time_out': время конца промежутка
            - 'total_margin': общая маржа для пула
            - 'total_worst_equity': наихудшее эквити для пула
            - 'total_last_equity': последнее эквити для пула (на момент time_out)
            - 'total_start_equity': начальное эквити для пула (на момент time_in)
            - 'balance': баланс на начало промежутка
            - 'balance_change': изменение баланса относительно предыдущего промежутка
            - 'pool_changes': текстовое описание изменений в пуле относительно предыдущего
                * Для первого промежутка баланс рассчитывается через calculate_balance_at_date
                * Для последующих промежутков баланс накапливается: начальный + все изменения
                  (SWAP, комиссии, прибыль при закрытии позиций)
                * При закрытии позиции учитывается двойная комиссия (открытие + закрытие)
        """
        # Конвертируем даты в UTC timestamp
        from_date_utc = from_date - timedelta(hours=Config.LOCAL_TIMESHIFT)
        to_date_utc = to_date - timedelta(hours=Config.LOCAL_TIMESHIFT)
        from_timestamp = from_date_utc.timestamp()
        to_timestamp = to_date_utc.timestamp()
        
        # Фильтруем сделки (исключаем изменения баланса)
        trading_deals = [d for d in deals if d.type != 2]
        
        # Создаем маппинг position_id -> magic (для связи позиций с нулевым мэджиком)
        position_id_to_magic = {}
        for deal in trading_deals:
            if deal.position_id != 0 and deal.magic != 0:
                position_id_to_magic[deal.position_id] = deal.magic
        
        # Находим релевантные position_id (позиции с нужными мэджиками)
        relevant_position_ids = set()
        for deal in trading_deals:
            deal_magic = deal.magic
            position_id = deal.position_id
            
            # Определяем мэджик позиции
            if deal_magic in magics:
                relevant_position_ids.add(position_id)
            elif position_id != 0 and position_id in position_id_to_magic:
                if position_id_to_magic[position_id] in magics:
                    relevant_position_ids.add(position_id)
        
        # Получаем ВСЕ сделки для релевантных позиций (включая открытие до from_date)
        all_relevant_deals = []
        for deal in trading_deals:
            if deal.position_id in relevant_position_ids:
                all_relevant_deals.append(deal)
        
        # Сортируем сделки по времени и deal номеру
        all_relevant_deals.sort(key=lambda x: (x.time, x.deal if hasattr(x, 'deal') else 0))
        
        # Группируем сделки, которые происходят в радиусе 2 секунд
        # Это нужно для объединения нескольких входов/выходов в один момент
        grouped_deals = []
        current_group = []
        group_time = None
        
        for deal in all_relevant_deals:
            if deal.time < from_timestamp:
                continue
            if deal.time > to_timestamp:
                break
            
            if group_time is None:
                # Начинаем новую группу
                current_group = [deal]
                group_time = deal.time
            elif abs(deal.time - group_time) <= 2.0:
                # Сделка в пределах 2 секунд - добавляем в текущую группу
                current_group.append(deal)
            else:
                # Сделка вне радиуса - закрываем текущую группу и начинаем новую
                if current_group:
                    grouped_deals.append(current_group)
                current_group = [deal]
                group_time = deal.time
        
        # Добавляем последнюю группу
        if current_group:
            grouped_deals.append(current_group)
        
        # Восстанавливаем состояние позиций на начало периода
        # Позиция считается открытой, если есть сделки открытия до from_timestamp
        # и нет сделок закрытия до from_timestamp
        positions_at_start = {}  # position_id -> позиция
        
        for deal in all_relevant_deals:
            if deal.time >= from_timestamp:
                break
            
            position_id = deal.position_id
            if position_id == 0:
                continue
            
            entry = deal.entry  # 0 = in (открытие), 1 = out (закрытие)
            
            if entry == 0:  # Сделка открытия
                if position_id not in positions_at_start:
                    # Определяем мэджик для позиции
                    magic = deal.magic
                    if magic == 0 and position_id in position_id_to_magic:
                        magic = position_id_to_magic[position_id]
                    
                    positions_at_start[position_id] = {
                        'position_id': position_id,
                        'symbol': deal.symbol,
                        'direction': 'Buy' if deal.type == 0 else 'Sell',
                        'volume': abs(deal.volume),
                        'price_open': deal.price,
                        'magic': magic,
                        'total_volume': abs(deal.volume),
                        'total_price_volume': deal.price * abs(deal.volume)  # Для расчета средней цены
                    }
                else:
                    # Добавляем объем к существующей позиции
                    pos = positions_at_start[position_id]
                    pos['total_volume'] += abs(deal.volume)
                    pos['total_price_volume'] += deal.price * abs(deal.volume)
                    pos['price_open'] = pos['total_price_volume'] / pos['total_volume']
            elif entry == 1:  # Сделка закрытия
                if position_id in positions_at_start:
                    # Уменьшаем объем или удаляем позицию
                    close_volume = abs(deal.volume)
                    pos = positions_at_start[position_id]
                    pos['total_volume'] -= close_volume
                    if pos['total_volume'] <= 0:
                        del positions_at_start[position_id]
                    else:
                        # Пересчитываем среднюю цену (упрощенно, без учета закрытого объема)
                        # В реальности нужно учитывать FIFO или другую логику
                        pass
        
        # Теперь проходим по сделкам в периоде и отслеживаем изменения
        timeline = []
        current_positions = {}
        for pid, pos in positions_at_start.items():
            current_positions[pid] = {
                'position_id': pos['position_id'],
                'symbol': pos['symbol'],
                'direction': pos['direction'],
                'volume': pos['total_volume'],
                'price_open': pos['price_open'],
                'magic': pos['magic'],
                'total_volume': pos['total_volume'],
                'total_price_volume': pos['total_price_volume']
            }
        
        # Вспомогательная функция для генерации комментария об изменениях
        def generate_pool_changes_comment(prev_positions: Dict, curr_positions: Dict) -> str:
            """Генерирует текстовое описание изменений в пуле позиций"""
            if not prev_positions:
                if not curr_positions:
                    return "Пустой пул"
                changes = []
                for pos in curr_positions.values():
                    changes.append(f"+{pos['total_volume']:.2f} {pos['symbol']} {pos['direction']}")
                return ", ".join(changes) if changes else "Пустой пул"
            
            if not curr_positions:
                changes = []
                for pos in prev_positions.values():
                    changes.append(f"-{pos['total_volume']:.2f} {pos['symbol']} {pos['direction']}")
                return ", ".join(changes) if changes else "Пустой пул"
            
            # Создаем словари для сравнения: (symbol, direction) -> volume
            prev_dict = {}
            for pos in prev_positions.values():
                key = (pos['symbol'], pos['direction'])
                prev_dict[key] = prev_dict.get(key, 0.0) + pos['total_volume']
            
            curr_dict = {}
            for pos in curr_positions.values():
                key = (pos['symbol'], pos['direction'])
                curr_dict[key] = curr_dict.get(key, 0.0) + pos['total_volume']
            
            changes = []
            all_keys = set(prev_dict.keys()) | set(curr_dict.keys())
            
            for key in all_keys:
                prev_vol = prev_dict.get(key, 0.0)
                curr_vol = curr_dict.get(key, 0.0)
                diff = curr_vol - prev_vol
                
                if abs(diff) > 0.001:  # Учитываем только значимые изменения
                    symbol, direction = key
                    if diff > 0:
                        changes.append(f"+{diff:.2f} {symbol} {direction}")
                    else:
                        changes.append(f"{diff:.2f} {symbol} {direction}")
            
            return ", ".join(changes) if changes else "Без изменений"
        
        # Добавляем начальное состояние
        # Баланс для первого промежутка рассчитывается через calculate_balance_at_date
        initial_balance = MT5Calculator.calculate_balance_at_date(
            from_date, deals, use_exact_time=True
        )
        
        # Подготавливаем начальные позиции для analyze_positions_pool
        initial_positions_list = [{
            'symbol': pos['symbol'],
            'direction': pos['direction'],
            'volume': pos['total_volume'],
            'price_open': pos['price_open']
        } for pos in current_positions.values()]
        
        # Определяем time_out для начального анализа
        # Если есть группы сделок, используем время первой группы, иначе to_date
        initial_analysis_time_out = to_date
        if grouped_deals:
            # deal.time is UTC timestamp, convert to local time (UTC+LOCAL_TIMESHIFT)
            from datetime import timezone as tz
            first_group_time_utc = datetime.fromtimestamp(grouped_deals[0][0].time, tz=tz.utc)
            first_group_time = first_group_time_utc.replace(tzinfo=None) + timedelta(hours=Config.LOCAL_TIMESHIFT)
            initial_analysis_time_out = first_group_time
        
        # Анализируем начальный пул с правильными временными рамками
        initial_analysis = MT5Calculator.analyze_positions_pool(
            initial_positions_list, from_date, initial_analysis_time_out, account
        ) if initial_positions_list else {
            'aggregated_positions': [],
            'total_margin': 0.0,
            'total_worst_equity': 0.0,
            'total_last_equity': 0.0,
            'total_start_equity': 0.0
        }
        
        timeline.append({
            'aggregated_positions': initial_analysis.get('aggregated_positions', []),
            'time_in': from_date,
            'time_out': None,  # Будет установлено при следующем изменении
            'total_margin': initial_analysis.get('total_margin', 0.0),
            'total_worst_equity': initial_analysis.get('total_worst_equity', 0.0),
            'total_last_equity': initial_analysis.get('total_last_equity', 0.0),
            'total_start_equity': initial_analysis.get('total_start_equity', 0.0),
            'balance': 0.0,  # Первое значение баланса равно нулю
            'balance_change': 0.0,
            'pool_changes': "Начальное состояние"
        })
        
        # Текущий баланс для накопления изменений (начинаем с нуля)
        current_balance = 0.0
        previous_positions = current_positions.copy()
        
        # Обрабатываем группы сделок в периоде
        for group_index, deal_group in enumerate(grouped_deals):
            # Проверяем, что группа в нужном периоде
            if deal_group[0].time < from_timestamp:
                continue
            if deal_group[0].time > to_timestamp:
                break
            
            # Обрабатываем все сделки в группе
            # Время группы = время первой сделки (convert UTC timestamp to local time)
            from datetime import timezone as tz
            group_time_utc = datetime.fromtimestamp(deal_group[0].time, tz=tz.utc)
            group_time_local = group_time_utc.replace(tzinfo=None) + timedelta(hours=Config.LOCAL_TIMESHIFT)
            positions_changed = False
            group_balance_change = 0.0  # Общее изменение баланса от всех сделок в группе
            
            for deal in deal_group:
                position_id = deal.position_id
                if position_id == 0:
                    continue
                
                entry = deal.entry
                balance_change = 0.0  # Изменение баланса от этой сделки
                
                if entry == 0:  # Сделка открытия
                    if position_id not in current_positions:
                        # Новая позиция
                        magic = deal.magic
                        if magic == 0 and position_id in position_id_to_magic:
                            magic = position_id_to_magic[position_id]
                        
                        current_positions[position_id] = {
                            'position_id': position_id,
                            'symbol': deal.symbol,
                            'direction': 'Buy' if deal.type == 0 else 'Sell',
                            'volume': abs(deal.volume),
                            'price_open': deal.price,
                            'magic': magic,
                            'total_volume': abs(deal.volume),
                            'total_price_volume': deal.price * abs(deal.volume)
                        }
                        positions_changed = True
                    else:
                        # Добавляем объем к существующей позиции
                        pos = current_positions[position_id]
                        new_volume = abs(deal.volume)
                        pos['total_volume'] += new_volume
                        pos['total_price_volume'] += deal.price * new_volume
                        pos['price_open'] = pos['total_price_volume'] / pos['total_volume']
                        pos['volume'] = pos['total_volume']
                        positions_changed = True
                    
                    # При открытии учитываем только SWAP (если есть)
                    # Комиссия за открытие будет учтена при закрытии
                    balance_change = deal.swap if hasattr(deal, 'swap') else 0.0
                
                elif entry == 1:  # Сделка закрытия или SWAP
                    close_volume = abs(deal.volume)
                    
                    if position_id in current_positions:
                        # Позиция существует - это может быть закрытие или SWAP
                        pos = current_positions[position_id]
                        
                        if close_volume > 0:
                            # Это закрытие позиции (полное или частичное)
                            pos['total_volume'] -= close_volume
                            
                            if pos['total_volume'] <= 0:
                                # Позиция полностью закрыта
                                del current_positions[position_id]
                                positions_changed = True
                            else:
                                # Позиция частично закрыта
                                pos['volume'] = pos['total_volume']
                                positions_changed = True
                        
                        # При закрытии учитываем:
                        # - Прибыль/убыток (profit)
                        # - SWAP
                        # - Двойную комиссию (открытие + закрытие), только если это реальное закрытие
                        profit = deal.profit if hasattr(deal, 'profit') else 0.0
                        swap = deal.swap if hasattr(deal, 'swap') else 0.0
                        commission = deal.commission if hasattr(deal, 'commission') else 0.0
                        
                        if close_volume > 0:
                            # Реальное закрытие - двойная комиссия
                            balance_change = profit + swap + (commission * 2)
                        else:
                            # Только SWAP-сделка (volume=0 или очень маленький)
                            balance_change = swap
                    else:
                        # Позиция уже закрыта ранее, но есть SWAP или другая сделка
                        # Учитываем только SWAP (комиссия и profit уже были учтены при закрытии)
                        swap = deal.swap if hasattr(deal, 'swap') else 0.0
                        balance_change = swap
                    
                    # Накапливаем изменение баланса группы
                    group_balance_change += balance_change
            
            # Накапливаем общее изменение баланса после обработки всех сделок в группе
            current_balance += group_balance_change
            
            # Если пул позиций изменился, создаем новый элемент в timeline
            if positions_changed:
                # Закрываем предыдущий промежуток
                if timeline:
                    timeline[-1]['time_out'] = group_time_local
                
                # Подготавливаем текущие позиции для analyze_positions_pool
                current_positions_list = [{
                    'symbol': pos['symbol'],
                    'direction': pos['direction'],
                    'volume': pos['total_volume'],
                    'price_open': pos['price_open']
                } for pos in current_positions.values()]
                
                # Определяем time_out для анализа - время следующего изменения или конец периода
                if group_index + 1 < len(grouped_deals):
                    # Есть следующая группа - используем её время как time_out
                    # deal.time is UTC timestamp, convert to local time (UTC+LOCAL_TIMESHIFT)
                    from datetime import timezone as tz
                    next_group_time_utc = datetime.fromtimestamp(grouped_deals[group_index + 1][0].time, tz=tz.utc)
                    next_group_time = next_group_time_utc.replace(tzinfo=None) + timedelta(hours=Config.LOCAL_TIMESHIFT)
                    analysis_time_out = next_group_time
                else:
                    # Это последняя группа - используем to_date
                    analysis_time_out = to_date
                
                # Анализируем текущий пул с правильными временными рамками
                current_analysis = MT5Calculator.analyze_positions_pool(
                    current_positions_list, group_time_local, analysis_time_out, account
                ) if current_positions_list else {
                    'aggregated_positions': [],
                    'total_margin': 0.0,
                    'total_worst_equity': 0.0,
                    'total_last_equity': 0.0,
                    'total_start_equity': 0.0
                }
                
                # Генерируем комментарий об изменениях
                pool_changes = generate_pool_changes_comment(previous_positions, current_positions)
                
                # Добавляем новый промежуток
                timeline.append({
                    'aggregated_positions': current_analysis.get('aggregated_positions', []),
                    'time_in': group_time_local,
                    'time_out': None,  # Будет установлено при следующем изменении
                    'total_margin': current_analysis.get('total_margin', 0.0),
                    'total_worst_equity': current_analysis.get('total_worst_equity', 0.0),
                    'total_last_equity': current_analysis.get('total_last_equity', 0.0),
                    'total_start_equity': current_analysis.get('total_start_equity', 0.0),
                    'balance': current_balance,
                    'balance_change': group_balance_change,
                    'pool_changes': pool_changes
                })
                
                # Обновляем предыдущие позиции для следующей итерации
                previous_positions = current_positions.copy()
            # Если пул не изменился, но баланс изменился (например, SWAP),
            # обновляем баланс в последнем промежутке
            elif group_balance_change != 0 and timeline:
                timeline[-1]['balance'] = current_balance
                timeline[-1]['balance_change'] = timeline[-1].get('balance_change', 0.0) + group_balance_change
        
        # Закрываем последний промежуток
        if timeline:
            timeline[-1]['time_out'] = to_date
        
        return timeline
    
    @staticmethod
    def calculate_margin(symbol: str, lot_size: float, price: float, 
                        account: Dict[str, Any] = None) -> Optional[float]:
        """
        Рассчитывает размер маржи для позиции
        
        Args:
            symbol: Торговый символ (например, 'EURUSD')
            lot_size: Размер лота (например, 0.1, 1.0)
            price: Цена открытия позиции
            account: Информация об аккаунте (опционально, для получения leverage)
            
        Returns:
            Размер маржи в валюте депозита или None в случае ошибки
        """
        connection = MT5Connection()  # Singleton - всегда один экземпляр
        # Используем ensure_connected - соединение переиспользуется, не создается заново
        if not connection.ensure_connected(account):
            print(f"❌ Не удалось установить соединение с MT5")
            return None
        
        try:
            # Получить информацию о символе
            symbol_info = mt5.symbol_info(symbol)
            if symbol_info is None:
                print(f"❌ Символ {symbol} не найден")
                return None
            
            # Проверить, видим ли символ в Market Watch
            if not symbol_info.visible:
                if not mt5.symbol_select(symbol, True):
                    print(f"❌ Не удалось добавить символ {symbol} в Market Watch")
                    return None
            
            # Получить информацию об аккаунте для leverage
            account_info = connection.get_account_info()
            if account_info is None:
                print(f"❌ Не удалось получить информацию об аккаунте")
                return None
            
            leverage = account_info.leverage
            if leverage <= 0:
                leverage = 1  # Защита от деления на ноль
            
            # Используем встроенную функцию MT5 для точного расчета маржи
            # Это самый надежный способ, так как MT5 сам знает все спецификации символов
            
            # Определяем тип ордера (BUY или SELL) - для расчета маржи это не критично,
            # но используем BUY по умолчанию
            order_type = mt5.ORDER_TYPE_BUY
            
            # Используем встроенную функцию MT5 для расчета маржи
            # order_calc_margin учитывает всю спецификацию символа, включая плавающую маржу
            margin = mt5.order_calc_margin(order_type, symbol, lot_size, price)
            
            if margin is None or margin < 0:
                # Если order_calc_margin вернул ошибку, пробуем альтернативный метод
                print(f"⚠️ order_calc_margin вернул ошибку, используем альтернативный расчет")
                
                # Получаем параметры символа для альтернативного расчета
                contract_size = symbol_info.trade_contract_size
                margin_initial = symbol_info.margin_initial
                margin_currency = getattr(symbol_info, 'currency_margin', None)
                account_currency = account_info.currency
                
                # Если указана начальная маржа, используем её
                if margin_initial > 0:
                    margin = (lot_size * margin_initial) / leverage
                else:
                    # Пробуем определить тип инструмента по profit_calculation_mode
                    profit_calc_mode = getattr(symbol_info, 'profit_calculation_mode', None)
                    
                    if profit_calc_mode == 0:  # FOREX
                        # Для Forex: margin = (lot_size * contract_size) / leverage (БЕЗ цены)
                        margin = (lot_size * contract_size) / leverage
                    else:
                        # Для CFD и других: margin = (lot_size * contract_size * price) / leverage (С ценой)
                        margin = (lot_size * contract_size * price) / leverage
                
                # Конвертация в валюту депозита, если валюта маржи отличается
                if margin_currency and margin_currency != account_currency:
                    # Нужно получить курс конвертации
                    # Создаем символ для конвертации (например, для конвертации JPY в USD используем USDJPY)
                    conversion_symbol = f"{margin_currency}{account_currency}"
                    if conversion_symbol != symbol:  # Избегаем рекурсии
                        conversion_info = mt5.symbol_info(conversion_symbol)
                        if conversion_info:
                            # Получаем текущую цену для конвертации
                            tick = mt5.symbol_info_tick(conversion_symbol)
                            if tick:
                                # Если базовая валюта = валюта маржи, используем ask
                                # Иначе используем обратный курс (1/bid)
                                if margin_currency == conversion_symbol[:3]:
                                    conversion_rate = tick.ask
                                else:
                                    conversion_rate = 1.0 / tick.bid if tick.bid > 0 else 1.0
                                margin = margin * conversion_rate
                            else:
                                # Если не удалось получить тик, пробуем обратный символ
                                reverse_symbol = f"{account_currency}{margin_currency}"
                                reverse_info = mt5.symbol_info(reverse_symbol)
                                if reverse_info:
                                    tick = mt5.symbol_info_tick(reverse_symbol)
                                    if tick:
                                        # Для обратного символа: если базовая = валюта депозита, используем 1/ask
                                        if account_currency == reverse_symbol[:3]:
                                            conversion_rate = 1.0 / tick.ask if tick.ask > 0 else 1.0
                                        else:
                                            conversion_rate = tick.bid
                                        margin = margin * conversion_rate
            
            # Не закрываем соединение - оно долгоживущее
            return margin
            
        except Exception as e:
            print(f"❌ Ошибка при расчете маржи: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    @staticmethod
    def calculate_profit_loss(symbol: str, lot_size: float, price_open: float, 
                              direction: str, price_target: float,
                              account: Dict[str, Any] = None) -> Optional[float]:
        """
        Рассчитывает прибыль/убыток для позиции при достижении целевой цены
        
        Args:
            symbol: Торговый символ (например, 'EURUSD')
            lot_size: Размер лота (например, 0.1, 1.0)
            price_open: Цена открытия позиции
            direction: Направление позиции ('Buy' или 'Sell')
            price_target: Целевая цена для расчета
            account: Информация об аккаунте (опционально)
            
        Returns:
            Прибыль/убыток в валюте депозита. Положительное значение - прибыль, отрицательное - убыток.
            None в случае ошибки
        """
        connection = MT5Connection()  # Singleton - всегда один экземпляр
        if not connection.ensure_connected(account):
            print(f"❌ Не удалось установить соединение с MT5")
            return None
        
        try:
            # Получить информацию о символе
            symbol_info = mt5.symbol_info(symbol)
            if symbol_info is None:
                print(f"❌ Символ {symbol} не найден")
                return None
            
            # Проверить, видим ли символ в Market Watch
            if not symbol_info.visible:
                if not mt5.symbol_select(symbol, True):
                    print(f"❌ Не удалось добавить символ {symbol} в Market Watch")
                    return None
            
            # Определить тип ордера
            direction_upper = direction.upper()
            if direction_upper in ['BUY', '0']:
                order_type = mt5.ORDER_TYPE_BUY
            elif direction_upper in ['SELL', '1']:
                order_type = mt5.ORDER_TYPE_SELL
            else:
                print(f"❌ Неверное направление: {direction}. Используйте 'Buy' или 'Sell'")
                return None
            
            # Используем встроенную функцию MT5 для расчета прибыли/убытка
            # order_calc_profit(order_type, symbol, volume, price_open, price_close)
            profit = mt5.order_calc_profit(order_type, symbol, lot_size, price_open, price_target)
            
            if profit is None:
                # Если order_calc_profit не работает, рассчитываем вручную
                # Получаем параметры символа
                point = symbol_info.point  # Минимальное изменение цены
                tick_value = symbol_info.trade_tick_value  # Стоимость одного тика
                tick_size = symbol_info.trade_tick_size  # Размер тика
                contract_size = symbol_info.trade_contract_size  # Размер контракта
                profit_calc_mode = getattr(symbol_info, 'profit_calculation_mode', None)
                profit_currency = getattr(symbol_info, 'currency_profit', None)
                
                # Получаем информацию об аккаунте для конвертации валюты
                account_info = connection.get_account_info()
                if account_info is None:
                    print(f"❌ Не удалось получить информацию об аккаунте")
                    return None
                
                account_currency = account_info.currency
                
                # Рассчитываем разницу в цене
                if order_type == mt5.ORDER_TYPE_BUY:
                    price_diff = price_target - price_open
                else:  # SELL
                    price_diff = price_open - price_target
                
                # Рассчитываем прибыль/убыток в зависимости от режима расчета
                if profit_calc_mode == 0:  # FOREX
                    # Для Forex: profit = (price_diff / point) * tick_value * lot_size
                    # tick_value обычно указан для 1 лота
                    if tick_value > 0 and point > 0:
                        profit = (price_diff / point) * tick_value * lot_size
                    else:
                        # Альтернативный расчет для Forex
                        # Для большинства Forex: 1 пункт (point) = tick_value за 1 лот
                        profit = (price_diff / point) * lot_size * (tick_value if tick_value > 0 else 1.0)
                else:
                    # Для CFD и других инструментов
                    # profit = price_diff * contract_size * lot_size
                    profit = price_diff * contract_size * lot_size
                
                # Конвертация в валюту депозита, если валюта прибыли отличается
                if profit_currency and profit_currency != account_currency:
                    # Нужно получить курс конвертации
                    conversion_symbol = f"{profit_currency}{account_currency}"
                    if conversion_symbol != symbol:  # Избегаем рекурсии
                        conversion_info = mt5.symbol_info(conversion_symbol)
                        if conversion_info:
                            tick = mt5.symbol_info_tick(conversion_symbol)
                            if tick:
                                # Определяем курс конвертации
                                if profit_currency == conversion_symbol[:3]:
                                    conversion_rate = tick.ask
                                else:
                                    conversion_rate = 1.0 / tick.bid if tick.bid > 0 else 1.0
                                profit = profit * conversion_rate
                            else:
                                # Пробуем обратный символ
                                reverse_symbol = f"{account_currency}{profit_currency}"
                                reverse_info = mt5.symbol_info(reverse_symbol)
                                if reverse_info:
                                    tick = mt5.symbol_info_tick(reverse_symbol)
                                    if tick:
                                        if account_currency == reverse_symbol[:3]:
                                            conversion_rate = 1.0 / tick.ask if tick.ask > 0 else 1.0
                                        else:
                                            conversion_rate = tick.bid
                                        profit = profit * conversion_rate
            
            # Не закрываем соединение - оно долгоживущее
            return profit
            
        except Exception as e:
            print(f"❌ Ошибка при расчете прибыли/убытка: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    @staticmethod
    def get_high_low_prices(symbol: str, time_in: datetime, time_out: datetime,
                            account: Dict[str, Any] = None) -> Dict[str, Optional[float]]:
        """
        Находит цены HIGH и LOW по тиковым данным в указанном временном промежутке
        
        Args:
            symbol: Торговый символ (например, 'EURUSD')
            time_in: Время начала периода (IN)
            time_out: Время окончания периода (OUT)
            account: Информация об аккаунте (опционально, для определения сервера)
            
        Returns:
            Словарь с ключами 'high' и 'low':
            - 'high': Максимальная цена ask за период
            - 'low': Минимальная цена bid за период
            - Значения могут быть None, если тиковые данные отсутствуют
        """
        try:
            # Ленивый импорт для избежания циклической зависимости
            from .tick_data import mt5_tick_provider
            
            # Используем MT5TickProvider для получения HIGH/LOW цен
            # Он автоматически определит сервер из account или использует текущее соединение
            result = mt5_tick_provider.get_high_low_prices(
                symbol=symbol,
                from_date=time_in,
                to_date=time_out,
                account=account
            )
            
            return {
                'high': result.get('high'),
                'low': result.get('low')
            }
            
        except Exception as e:
            print(f"❌ Ошибка при получении HIGH/LOW цен: {e}")
            import traceback
            traceback.print_exc()
            return {'high': None, 'low': None}
    
    @staticmethod
    def get_price_at_time(symbol: str, target_time: datetime,
                         account: Dict[str, Any] = None) -> Dict[str, Optional[float]]:
        """
        Получает цену (bid/ask) на конкретный момент времени
        
        Args:
            symbol: Торговый символ (например, 'EURUSD')
            target_time: Целевой момент времени
            account: Информация об аккаунте (опционально, для определения сервера)
            
        Returns:
            Словарь с ключами 'bid' и 'ask':
            - 'bid': Цена bid на момент target_time (или последний доступный тик до этого момента)
            - 'ask': Цена ask на момент target_time (или последний доступный тик до этого момента)
            - Значения могут быть None, если тиковые данные отсутствуют
        """
        try:
            # Ленивый импорт для избежания циклической зависимости
            from .tick_data import mt5_tick_provider
            
            now = datetime.now()
            
            # Если запрашивается будущее время, используем последний доступный тик
            if target_time > now:
                logger.debug(f"get_price_at_time: Запрошено будущее время {target_time} (текущее: {now}), "
                            f"используем последний доступный тик")
                # Расширяем диапазон поиска назад, чтобы найти последний доступный тик
                from_time = now - timedelta(hours=1)  # Ищем за последний час
                to_time = now
                compare_time = now
            else:
                # Получаем тики за небольшой период до target_time (например, 1 минута)
                from_time = target_time - timedelta(minutes=1)
                to_time = target_time
                compare_time = target_time
            
            # Конвертируем в UTC для запроса к БД и сравнения
            # target_time, from_time, to_time, compare_time уже в локальном времени терминала (UTC+LOCAL_TIMESHIFT)
            # Тики в БД хранятся с UTC timestamps
            # Чтобы получить UTC datetime из локального: вычитаем LOCAL_TIMESHIFT
            from datetime import timezone
            
            # target_time уже локальное время терминала, конвертируем в UTC
            # Локальное время = UTC + LOCAL_TIMESHIFT, поэтому UTC = локальное - LOCAL_TIMESHIFT
            from_time_utc_naive = from_time - timedelta(hours=Config.LOCAL_TIMESHIFT)
            to_time_utc_naive = to_time - timedelta(hours=Config.LOCAL_TIMESHIFT)
            compare_time_utc_naive = compare_time - timedelta(hours=Config.LOCAL_TIMESHIFT)
            
            # Mark as UTC timezone for correct timestamp conversion
            from_time_utc = from_time_utc_naive.replace(tzinfo=timezone.utc)
            to_time_utc = to_time_utc_naive.replace(tzinfo=timezone.utc)
            compare_time_utc = compare_time_utc_naive.replace(tzinfo=timezone.utc)
            
            from_timestamp_utc = int(from_time_utc.timestamp())
            to_timestamp_utc = int(to_time_utc.timestamp())
            compare_timestamp_utc = int(compare_time_utc.timestamp())
            
            # Для диагностики: проверим, правильно ли конвертируется время
            logger.debug(f"get_price_at_time: Конвертация времени - target_time (локальное): {target_time}, "
                        f"compare_time (локальное): {compare_time}, "
                        f"compare_time_utc (UTC): {compare_time_utc}, "
                        f"compare_timestamp_utc: {compare_timestamp_utc}")
            
            logger.debug(f"get_price_at_time: Поиск цены для {symbol} на момент {target_time} (локальное время), "
                        f"диапазон поиска: {from_time} - {to_time} (локальное), "
                        f"UTC timestamps: {from_timestamp_utc} ({datetime.fromtimestamp(from_timestamp_utc)}) - "
                        f"{to_timestamp_utc} ({datetime.fromtimestamp(to_timestamp_utc)}), "
                        f"сравнение: {compare_timestamp_utc} ({datetime.fromtimestamp(compare_timestamp_utc)})")
            
            # Получаем тики из БД
            server = None
            if account:
                server = account.get('server', None)
            
            if not server:
                server = mt5_tick_provider.get_server_name(account)
            
            if not server:
                logger.warning(f"get_price_at_time: Не удалось определить сервер для {symbol}")
                return {'bid': None, 'ask': None}
            
            ticks = mt5_tick_provider.get_ticks_from_db(
                symbol=symbol,
                from_date=from_time,
                to_date=to_time,
                server=server,
                account=account
            )
            
            logger.debug(f"get_price_at_time: Найдено {len(ticks) if ticks else 0} тиков для {symbol}")
            
            if not ticks:
                logger.warning(f"get_price_at_time: Тики не найдены для {symbol} в диапазоне {from_time} - {to_time}")
                return {'bid': None, 'ask': None}
            
            # Убеждаемся, что тики отсортированы по времени
            sorted_ticks = sorted(ticks, key=lambda x: x['time'])
            
            # Логируем первый и последний тик для диагностики
            if sorted_ticks:
                # UTC timestamps нужно конвертировать правильно: fromtimestamp с timezone.utc
                from datetime import timezone as tz
                first_tick_time_utc = datetime.fromtimestamp(sorted_ticks[0]['time'], tz=tz.utc)
                last_tick_time_utc = datetime.fromtimestamp(sorted_ticks[-1]['time'], tz=tz.utc)
                # Конвертируем в локальное время (UTC+LOCAL_TIMESHIFT)
                first_tick_time_local = first_tick_time_utc.replace(tzinfo=None) + timedelta(hours=Config.LOCAL_TIMESHIFT)
                last_tick_time_local = last_tick_time_utc.replace(tzinfo=None) + timedelta(hours=Config.LOCAL_TIMESHIFT)
                logger.debug(f"get_price_at_time: Первый тик: {first_tick_time_local} (UTC timestamp: {sorted_ticks[0]['time']}), "
                            f"последний тик: {last_tick_time_local} (UTC timestamp: {sorted_ticks[-1]['time']})")
            
            # Находим последний тик до или в момент compare_time
            last_tick = None
            for tick in sorted_ticks:
                if tick['time'] <= compare_timestamp_utc:
                    last_tick = tick
                else:
                    break
            
            if last_tick:
                # UTC timestamp нужно конвертировать правильно: fromtimestamp с timezone.utc
                from datetime import timezone as tz
                tick_time_utc = datetime.fromtimestamp(last_tick['time'], tz=tz.utc)
                tick_time_local = tick_time_utc.replace(tzinfo=None) + timedelta(hours=Config.LOCAL_TIMESHIFT)
                logger.debug(f"get_price_at_time: Найден тик для {symbol} на момент {tick_time_local} "
                            f"(запрошено {target_time}), bid={last_tick.get('bid')}, ask={last_tick.get('ask')}")
                return {
                    'bid': last_tick.get('bid'),
                    'ask': last_tick.get('ask')
                }
            
            logger.warning(f"get_price_at_time: Не найден подходящий тик для {symbol} на момент {target_time} "
                          f"(сравнение с {compare_time}, UTC timestamp: {compare_timestamp_utc}), "
                          f"найдено тиков: {len(sorted_ticks)}, "
                          f"диапазон тиков UTC: {sorted_ticks[0]['time'] if sorted_ticks else 'N/A'} - {sorted_ticks[-1]['time'] if sorted_ticks else 'N/A'}")
            return {'bid': None, 'ask': None}
            
        except Exception as e:
            logger.error(f"Ошибка при получении цены на момент времени: {e}", exc_info=True)
            return {'bid': None, 'ask': None}
    
    @staticmethod
    def calculate_aggregated_position(positions: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Рассчитывает общий уровень входа и объём для группы однонаправленных позиций с единым символом
        
        Args:
            positions: Список позиций, каждая должна содержать:
                - 'symbol': торговый символ (например, 'EURUSD')
                - 'direction': направление ('Buy' или 'Sell')
                - 'volume': размер лота (например, 0.1, 1.0)
                - 'price_open': цена открытия позиции
                
        Returns:
            Словарь с ключами:
                - 'symbol': символ позиций
                - 'direction': направление ('Buy' или 'Sell')
                - 'total_volume': общий объём (сумма всех объёмов)
                - 'average_price': средневзвешенная цена входа
                - 'positions_count': количество позиций в группе
            None, если входные данные некорректны или позиции не однонаправленные/не одного символа
        """
        if not positions or len(positions) == 0:
            return None
        
        # Проверяем, что все позиции имеют необходимые поля
        required_fields = ['symbol', 'direction', 'volume', 'price_open']
        for pos in positions:
            if not all(field in pos for field in required_fields):
                print(f"Ошибка: Позиция не содержит все необходимые поля: {required_fields}")
                return None
        
        # Проверяем, что все позиции одного символа
        symbols = set(pos['symbol'] for pos in positions)
        if len(symbols) > 1:
            print(f"Ошибка: Позиции имеют разные символы: {symbols}")
            return None
        
        # Проверяем, что все позиции однонаправленные
        directions = set(pos['direction'].upper() for pos in positions)
        if len(directions) > 1:
            print(f"Ошибка: Позиции имеют разные направления: {directions}")
            return None
        
        symbol = positions[0]['symbol']
        direction = positions[0]['direction']
        
        # Рассчитываем общий объём и средневзвешенную цену
        total_volume = 0.0
        total_price_volume = 0.0
        
        for pos in positions:
            volume = float(pos['volume'])
            price_open = float(pos['price_open'])
            
            total_volume += volume
            total_price_volume += price_open * volume
        
        if total_volume <= 0:
            print(f"Ошибка: Общий объём позиций должен быть больше нуля")
            return None
        
        average_price = total_price_volume / total_volume
        
        return {
            'symbol': symbol,
            'direction': direction,
            'total_volume': total_volume,
            'average_price': average_price,
            'positions_count': len(positions)
        }
    
    @staticmethod
    def analyze_positions_pool(positions: List[Dict[str, Any]], time_in: datetime, time_out: datetime,
                               account: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """
        Анализирует пул позиций: группирует, агрегирует, рассчитывает маржу и наихудшее эквити
        
        Args:
            positions: Список позиций, каждая должна содержать:
                - 'symbol': торговый символ (например, 'EURUSD')
                - 'direction': направление ('Buy' или 'Sell')
                - 'volume': размер лота (например, 0.1, 1.0)
                - 'price_open': цена открытия позиции
            time_in: Время начала периода (IN)
            time_out: Время окончания периода (OUT)
            account: Информация об аккаунте (опционально)
            
        Returns:
            Словарь с ключами:
                - 'aggregated_positions': список агрегированных позиций
                - 'total_margin': общая маржа для всего пула
                - 'total_worst_equity': общее изменение эквити в наихудший момент
                  (отрицательное значение = убыток, положительное = прибыль)
                - 'total_last_equity': общее изменение эквити на момент time_out
                  (отрицательное значение = убыток, положительное = прибыль)
                - 'total_start_equity': общее изменение эквити на момент time_in
                  (отрицательное значение = убыток, положительное = прибыль)
            None в случае ошибки
        """
        if not positions or len(positions) == 0:
            return {
                'aggregated_positions': [],
                'total_margin': 0.0,
                'total_worst_equity': 0.0,
                'total_last_equity': 0.0,
                'total_start_equity': 0.0
            }
        
        # Проверяем, что все позиции имеют необходимые поля
        required_fields = ['symbol', 'direction', 'volume', 'price_open']
        for pos in positions:
            if not all(field in pos for field in required_fields):
                print(f"Ошибка: Позиция не содержит все необходимые поля: {required_fields}")
                return None
        
        # Группируем позиции по символам и направлениям
        # Структура: {symbol: {'Buy': [positions], 'Sell': [positions]}}
        grouped_positions = {}
        
        for pos in positions:
            symbol = pos['symbol']
            direction = pos['direction'].upper()
            
            if symbol not in grouped_positions:
                grouped_positions[symbol] = {'Buy': [], 'Sell': []}
            
            if direction in ['BUY', '0']:
                grouped_positions[symbol]['Buy'].append(pos)
            elif direction in ['SELL', '1']:
                grouped_positions[symbol]['Sell'].append(pos)
            else:
                print(f"Предупреждение: Неизвестное направление '{pos['direction']}' для позиции {symbol}, пропускаем")
                continue
        
        # Обрабатываем каждую группу
        aggregated_positions = []
        symbol_margins = {}  # {symbol: margin}
        symbol_worst_equity = {}  # {symbol: worst_equity}
        symbol_last_equity = {}  # {symbol: last_equity} - эквити на момент time_out
        symbol_start_equity = {}  # {symbol: start_equity} - эквити на момент time_in
        
        for symbol, directions in grouped_positions.items():
            buy_positions = directions['Buy']
            sell_positions = directions['Sell']
            
            buy_aggregated = None
            sell_aggregated = None
            buy_margin = 0.0
            sell_margin = 0.0
            buy_worst_equity = 0.0
            sell_worst_equity = 0.0
            buy_last_equity = 0.0
            sell_last_equity = 0.0
            buy_start_equity = 0.0
            sell_start_equity = 0.0
            
            # Обрабатываем Buy позиции
            if buy_positions:
                if len(buy_positions) > 1:
                    # Агрегируем несколько позиций
                    buy_aggregated = MT5Calculator.calculate_aggregated_position(buy_positions)
                else:
                    # Одна позиция - используем как есть
                    pos = buy_positions[0]
                    buy_aggregated = {
                        'symbol': pos['symbol'],
                        'direction': 'Buy',
                        'total_volume': pos['volume'],
                        'average_price': pos['price_open'],
                        'positions_count': 1
                    }
                
                if buy_aggregated:
                    # Рассчитываем маржу независимо от наличия тиковых данных
                    # Маржа должна рассчитываться всегда, если есть позиции
                    buy_margin = MT5Calculator.calculate_margin(
                        symbol, buy_aggregated['total_volume'], 
                        buy_aggregated['average_price'], account
                    ) or 0.0
                    
                    # Получаем HIGH/LOW для периода (без костыля - используем правильное локальное время)
                    high_low = MT5Calculator.get_high_low_prices(
                        symbol, time_in, time_out, account
                    )
                    
                    if high_low and high_low.get('high') and high_low.get('low'):
                        # Рассчитываем прибыль/убыток при LOW цене (наихудший сценарий для Buy)
                        buy_profit_loss_low = MT5Calculator.calculate_profit_loss(
                            symbol, buy_aggregated['total_volume'],
                            buy_aggregated['average_price'], 'Buy',
                            high_low['low'], account
                        ) or 0.0
                        
                        # Наихудшее эквити = реальное значение прибыли/убытка в наихудший момент
                        # Отрицательное значение = убыток, положительное = прибыль
                        buy_worst_equity = buy_profit_loss_low
                        
                        # Добавляем информацию о HIGH/LOW в агрегированную позицию
                        buy_aggregated['high'] = high_low['high']
                        buy_aggregated['low'] = high_low['low']
                        buy_aggregated['worst_profit_loss'] = buy_profit_loss_low
                    else:
                        # Логируем отсутствие тиковых данных для расчета эквити
                        logger.warning(f"Недостаточно тиковых данных для расчета эквити позиции Buy {symbol} "
                                     f"за период {time_in} - {time_out}. Маржа рассчитана: {buy_margin:.2f}, "
                                     f"но эквити будет равно 0.0")
                        buy_worst_equity = 0.0
                        buy_aggregated['high'] = None
                        buy_aggregated['low'] = None
                        buy_aggregated['worst_profit_loss'] = 0.0
                    
                    # Рассчитываем начальное эквити (на момент time_in)
                    price_at_start = MT5Calculator.get_price_at_time(symbol, time_in, account)
                    if price_at_start and price_at_start.get('bid') is not None:
                        # Для Buy позиции используем bid для закрытия
                        buy_profit_loss_start = MT5Calculator.calculate_profit_loss(
                            symbol, buy_aggregated['total_volume'],
                            buy_aggregated['average_price'], 'Buy',
                            price_at_start['bid'], account
                        ) or 0.0
                        buy_start_equity = buy_profit_loss_start
                    else:
                        logger.warning(f"Не удалось получить цену для расчета начального эквити позиции Buy {symbol} "
                                     f"на момент {time_in}")
                        buy_start_equity = 0.0
                    
                    # Рассчитываем последнее эквити (на момент time_out)
                    price_at_end = MT5Calculator.get_price_at_time(symbol, time_out, account)
                    if price_at_end and price_at_end.get('bid') is not None:
                        # Для Buy позиции используем bid для закрытия
                        buy_profit_loss_end = MT5Calculator.calculate_profit_loss(
                            symbol, buy_aggregated['total_volume'],
                            buy_aggregated['average_price'], 'Buy',
                            price_at_end['bid'], account
                        ) or 0.0
                        buy_last_equity = buy_profit_loss_end
                    else:
                        logger.warning(f"Не удалось получить цену для расчета последнего эквити позиции Buy {symbol} "
                                     f"на момент {time_out}")
                        buy_last_equity = 0.0
                    
                    aggregated_positions.append(buy_aggregated)
            
            # Обрабатываем Sell позиции
            if sell_positions:
                if len(sell_positions) > 1:
                    # Агрегируем несколько позиций
                    sell_aggregated = MT5Calculator.calculate_aggregated_position(sell_positions)
                else:
                    # Одна позиция - используем как есть
                    pos = sell_positions[0]
                    sell_aggregated = {
                        'symbol': pos['symbol'],
                        'direction': 'Sell',
                        'total_volume': pos['volume'],
                        'average_price': pos['price_open'],
                        'positions_count': 1
                    }
                
                if sell_aggregated:
                    # Рассчитываем маржу независимо от наличия тиковых данных
                    # Маржа должна рассчитываться всегда, если есть позиции
                    sell_margin = MT5Calculator.calculate_margin(
                        symbol, sell_aggregated['total_volume'],
                        sell_aggregated['average_price'], account
                    ) or 0.0
                    
                    # Получаем HIGH/LOW для периода (без костыля - используем правильное локальное время)
                    high_low = MT5Calculator.get_high_low_prices(
                        symbol, time_in, time_out, account
                    )
                    
                    if high_low and high_low.get('high') and high_low.get('low'):
                        # Рассчитываем прибыль/убыток при HIGH цене (наихудший сценарий для Sell)
                        sell_profit_loss_high = MT5Calculator.calculate_profit_loss(
                            symbol, sell_aggregated['total_volume'],
                            sell_aggregated['average_price'], 'Sell',
                            high_low['high'], account
                        ) or 0.0
                        
                        # Наихудшее эквити = реальное значение прибыли/убытка в наихудший момент
                        # Отрицательное значение = убыток, положительное = прибыль
                        sell_worst_equity = sell_profit_loss_high
                        
                        # Добавляем информацию о HIGH/LOW в агрегированную позицию
                        sell_aggregated['high'] = high_low['high']
                        sell_aggregated['low'] = high_low['low']
                        sell_aggregated['worst_profit_loss'] = sell_profit_loss_high
                    else:
                        # Логируем отсутствие тиковых данных для расчета эквити
                        logger.warning(f"Недостаточно тиковых данных для расчета эквити позиции Sell {symbol} "
                                     f"за период {time_in} - {time_out}. Маржа рассчитана: {sell_margin:.2f}, "
                                     f"но эквити будет равно 0.0")
                        sell_worst_equity = 0.0
                        sell_aggregated['high'] = None
                        sell_aggregated['low'] = None
                        sell_aggregated['worst_profit_loss'] = 0.0
                    
                    # Рассчитываем начальное эквити (на момент time_in)
                    price_at_start = MT5Calculator.get_price_at_time(symbol, time_in, account)
                    if price_at_start and price_at_start.get('ask') is not None:
                        # Для Sell позиции используем ask для закрытия
                        sell_profit_loss_start = MT5Calculator.calculate_profit_loss(
                            symbol, sell_aggregated['total_volume'],
                            sell_aggregated['average_price'], 'Sell',
                            price_at_start['ask'], account
                        ) or 0.0
                        sell_start_equity = sell_profit_loss_start
                    else:
                        logger.warning(f"Не удалось получить цену для расчета начального эквити позиции Sell {symbol} "
                                     f"на момент {time_in}")
                        sell_start_equity = 0.0
                    
                    # Рассчитываем последнее эквити (на момент time_out)
                    price_at_end = MT5Calculator.get_price_at_time(symbol, time_out, account)
                    if price_at_end and price_at_end.get('ask') is not None:
                        # Для Sell позиции используем ask для закрытия
                        sell_profit_loss_end = MT5Calculator.calculate_profit_loss(
                            symbol, sell_aggregated['total_volume'],
                            sell_aggregated['average_price'], 'Sell',
                            price_at_end['ask'], account
                        ) or 0.0
                        sell_last_equity = sell_profit_loss_end
                    else:
                        logger.warning(f"Не удалось получить цену для расчета последнего эквити позиции Sell {symbol} "
                                     f"на момент {time_out}")
                        sell_last_equity = 0.0
                    
                    aggregated_positions.append(sell_aggregated)
            
            # Обобщаем данные для символа, если есть разнонаправленные позиции
            if buy_aggregated and sell_aggregated:
                # Для хедж-позиций: маржа = максимальная из двух
                symbol_margins[symbol] = max(buy_margin, sell_margin)
                
                # Наихудшее эквити для хедж-позиций: сумма прибыли/убытка обеих позиций
                # Если одна в убытке, а другая в прибыли - они компенсируют друг друга
                # Результат может быть как отрицательным (общий убыток), так и положительным (общая прибыль)
                symbol_worst_equity[symbol] = buy_worst_equity + sell_worst_equity
                symbol_last_equity[symbol] = buy_last_equity + sell_last_equity
                symbol_start_equity[symbol] = buy_start_equity + sell_start_equity
            elif buy_aggregated:
                symbol_margins[symbol] = buy_margin
                symbol_worst_equity[symbol] = buy_worst_equity
                symbol_last_equity[symbol] = buy_last_equity
                symbol_start_equity[symbol] = buy_start_equity
            elif sell_aggregated:
                symbol_margins[symbol] = sell_margin
                symbol_worst_equity[symbol] = sell_worst_equity
                symbol_last_equity[symbol] = sell_last_equity
                symbol_start_equity[symbol] = sell_start_equity
        
        # Суммируем маржу, наихудшее эквити, начальное эквити и последнее эквити по всем символам
        total_margin = sum(symbol_margins.values())
        total_worst_equity = sum(symbol_worst_equity.values())
        total_last_equity = sum(symbol_last_equity.values())
        total_start_equity = sum(symbol_start_equity.values())
        
        return {
            'aggregated_positions': aggregated_positions,
            'total_margin': total_margin,
            'total_worst_equity': total_worst_equity,
            'total_last_equity': total_last_equity,
            'total_start_equity': total_start_equity
        }


# Global instances
mt5_data_provider = MT5DataProvider()
mt5_calculator = MT5Calculator()
