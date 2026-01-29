"""
Тестовая функция для получения тиков золота из терминала и сохранения в файл

python tests/test_ticks_debug.py
"""

import sys
import os
from datetime import datetime, timedelta

# Добавляем корневую папку проекта в путь
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.mt5.mt5_client import MT5Connection
from src.mt5.tick_data import MT5TickProvider
from src.config.settings import Config
import MetaTrader5 as mt5

# ============================================================================
# НАСТРОЙКА СДВИГА ВРЕМЕНИ
# Измените это значение для экспериментов с конвертацией времени
# Например: 0, 1, 2, -1, -2 и т.д.
# ============================================================================
TIME_SHIFT_CORRECTION = 0  # Коррекция к Config.LOCAL_TIMESHIFT (в часах)
# ============================================================================


def main_test():
    """Тестовая функция для получения и сохранения тиков"""
    print("ТЕСТ ПОЛУЧЕНИЯ ТИКОВ ЗОЛОТА")
    print("=" * 70)
    print()
    
    # Параметры теста
    symbol = "XAUUSD"
    time_in = datetime(2025, 11, 14, 23, 32, 47)
    time_out = datetime(2025, 11, 14, 23, 59, 59)
    
    # Вычисляем эффективный сдвиг времени
    effective_timeshift = Config.LOCAL_TIMESHIFT + TIME_SHIFT_CORRECTION
    
    print(f"Символ: {symbol}")
    print(f"Период: {time_in.strftime('%d.%m.%Y %H:%M:%S')} - {time_out.strftime('%d.%m.%Y %H:%M:%S')}")
    print(f"LOCAL_TIMESHIFT: {Config.LOCAL_TIMESHIFT} часов")
    print(f"TIME_SHIFT_CORRECTION: {TIME_SHIFT_CORRECTION} часов")
    print(f"Эффективный сдвиг: {effective_timeshift} часов")
    print()
    
    # Инициализация подключения
    connection = MT5Connection()
    if not connection.initialize():
        print("Ошибка: Не удалось подключиться к MT5")
        return
    
    try:
        account_info = connection.get_account_info()
        if account_info:
            print(f"Аккаунт: {account_info.login}")
            print(f"Сервер: {account_info.server}")
            print()
        
        # Проверяем символ
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            print(f"Ошибка: Символ {symbol} не найден")
            return
        
        if not symbol_info.visible:
            if not mt5.symbol_select(symbol, True):
                print(f"Ошибка: Не удалось добавить символ {symbol} в Market Watch")
                return
        
        # Конвертируем локальное время в UTC для MT5 API
        time_in_utc = time_in - timedelta(hours=effective_timeshift)
        time_out_utc = time_out - timedelta(hours=effective_timeshift)
        
        print(f"Запрос тиков из MT5 (UTC):")
        print(f"  От: {time_in_utc.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  До: {time_out_utc.strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Получаем тики из MT5
        print("Получение тиков из MT5...")
        ticks = mt5.copy_ticks_range(
            symbol,
            time_in_utc,
            time_out_utc,
            mt5.COPY_TICKS_ALL
        )
        
        if ticks is None:
            print("Ошибка: MT5 вернул None")
            return
        
        ticks_list = list(ticks)
        print(f"Получено тиков: {len(ticks_list)}")
        print()
        
        if len(ticks_list) == 0:
            print("Тики не найдены")
            return
        
        # Сохраняем в файл
        output_file = "tests/ticks_debug_output.txt"
        print(f"Сохранение в файл: {output_file}")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write(f"ТИКИ {symbol}\n")
            f.write(f"Период: {time_in.strftime('%d.%m.%Y %H:%M:%S')} - {time_out.strftime('%d.%m.%Y %H:%M:%S')} (локальное время)\n")
            f.write(f"Период UTC: {time_in_utc.strftime('%d.%m.%Y %H:%M:%S')} - {time_out_utc.strftime('%d.%m.%Y %H:%M:%S')}\n")
            f.write(f"LOCAL_TIMESHIFT: {Config.LOCAL_TIMESHIFT} часов\n")
            f.write(f"TIME_SHIFT_CORRECTION: {TIME_SHIFT_CORRECTION} часов\n")
            f.write(f"Эффективный сдвиг: {effective_timeshift} часов\n")
            f.write("=" * 80 + "\n\n")
            
            f.write(f"{'№':<6} {'UTC Timestamp':<15} {'UTC Время':<20} {'Локальное время':<20} {'Bid':<12} {'Ask':<12} {'Volume':<10} {'Flags':<8}\n")
            f.write("-" * 120 + "\n")
            
            for i, tick in enumerate(ticks_list, 1):
                # Извлекаем данные тика
                if hasattr(tick, 'dtype') and tick.dtype.names:
                    tick_time_utc = int(tick['time'])
                    tick_bid = float(tick['bid'])
                    tick_ask = float(tick['ask'])
                    tick_volume = int(tick['volume'])
                    tick_flags = int(tick['flags'] if 'flags' in tick.dtype.names else 0)
                elif isinstance(tick, dict):
                    tick_time_utc = int(tick['time'])
                    tick_bid = float(tick['bid'])
                    tick_ask = float(tick['ask'])
                    tick_volume = int(tick.get('volume', 0))
                    tick_flags = int(tick.get('flags', 0))
                elif hasattr(tick, 'time'):
                    tick_time_utc = int(tick.time)
                    tick_bid = float(tick.bid)
                    tick_ask = float(tick.ask)
                    tick_volume = int(tick.volume)
                    tick_flags = int(getattr(tick, 'flags', 0))
                else:
                    tick_time_utc = int(tick[0])
                    tick_bid = float(tick[1])
                    tick_ask = float(tick[2])
                    tick_volume = int(tick[3])
                    tick_flags = int(tick[4] if len(tick) > 4 else 0)
                
                # Конвертируем UTC timestamp в datetime
                tick_dt_utc = datetime.fromtimestamp(tick_time_utc)
                tick_dt_local = tick_dt_utc + timedelta(hours=effective_timeshift)
                
                # Форматируем время
                utc_time_str = tick_dt_utc.strftime('%Y-%m-%d %H:%M:%S')
                local_time_str = tick_dt_local.strftime('%Y-%m-%d %H:%M:%S')
                
                f.write(f"{i:<6} {tick_time_utc:<15} {utc_time_str:<20} {local_time_str:<20} "
                       f"{tick_bid:<12.5f} {tick_ask:<12.5f} {tick_volume:<10} {tick_flags:<8}\n")
            
            f.write("\n" + "=" * 80 + "\n")
            f.write(f"Всего тиков: {len(ticks_list)}\n")
            f.write("=" * 80 + "\n")
        
        print(f"Тики сохранены в файл: {output_file}")
        print()
        
        # Выводим статистику
        if ticks_list:
            first_tick = ticks_list[0]
            last_tick = ticks_list[-1]
            
            # Извлекаем время первого и последнего тика
            if hasattr(first_tick, 'dtype') and first_tick.dtype.names:
                first_time_utc = int(first_tick['time'])
                last_time_utc = int(last_tick['time'])
            elif isinstance(first_tick, dict):
                first_time_utc = int(first_tick['time'])
                last_time_utc = int(last_tick['time'])
            elif hasattr(first_tick, 'time'):
                first_time_utc = int(first_tick.time)
                last_time_utc = int(last_tick.time)
            else:
                first_time_utc = int(first_tick[0])
                last_time_utc = int(last_tick[0])
            
            first_dt_utc = datetime.fromtimestamp(first_time_utc)
            last_dt_utc = datetime.fromtimestamp(last_time_utc)
            first_dt_local = first_dt_utc + timedelta(hours=effective_timeshift)
            last_dt_local = last_dt_utc + timedelta(hours=effective_timeshift)
            
            print("Статистика:")
            print(f"  Первый тик (UTC): {first_dt_utc.strftime('%Y-%m-%d %H:%M:%S')} (timestamp: {first_time_utc})")
            print(f"  Первый тик (локальное): {first_dt_local.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"  Последний тик (UTC): {last_dt_utc.strftime('%Y-%m-%d %H:%M:%S')} (timestamp: {last_time_utc})")
            print(f"  Последний тик (локальное): {last_dt_local.strftime('%Y-%m-%d %H:%M:%S')}")
            print()
            
            # Проверяем соответствие запрошенному диапазону
            print("Проверка соответствия запрошенному диапазону:")
            print(f"  Запрошено (локальное): {time_in.strftime('%Y-%m-%d %H:%M:%S')} - {time_out.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"  Получено (локальное): {first_dt_local.strftime('%Y-%m-%d %H:%M:%S')} - {last_dt_local.strftime('%Y-%m-%d %H:%M:%S')}")
            
            if first_dt_local < time_in or last_dt_local > time_out:
                print("  ВНИМАНИЕ: Тики выходят за пределы запрошенного диапазона!")
            else:
                print("  OK: Тики в пределах запрошенного диапазона")
    
    finally:
        connection.shutdown()
    
    print()
    print("=" * 70)
    print("Тест завершен!")


if __name__ == "__main__":
    try:
        main_test()
    except KeyboardInterrupt:
        print("\n\nТест прерван пользователем")
    except Exception as e:
        print(f"\nОшибка: {e}")
        import traceback
        traceback.print_exc()

