"""
Скрипт для построения графика тиков за день с метками по часам

python tests/test_ticks_chart.py
"""

import sys
import os
from datetime import datetime, timedelta

# Добавляем корневую папку проекта в путь
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.mt5.mt5_client import MT5Connection
from src.config.settings import Config
import MetaTrader5 as mt5
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# ============================================================================
# НАСТРОЙКА СДВИГА ВРЕМЕНИ
# Измените это значение для экспериментов с конвертацией времени
# ============================================================================
TIME_SHIFT_CORRECTION = -6  # Коррекция к Config.LOCAL_TIMESHIFT (в часах)
# ============================================================================


def main_test():
    """Построение графика тиков за день"""
    print("ПОСТРОЕНИЕ ГРАФИКА ТИКОВ")
    print("=" * 70)
    print()
    
    # Параметры теста
    symbol = "XAUUSD"
    target_date = datetime(2025, 11, 14)
    time_in = datetime(target_date.year, target_date.month, target_date.day, 0, 0, 0)
    time_out = datetime(target_date.year, target_date.month, target_date.day, 23, 59, 59)
    
    # Вычисляем эффективный сдвиг времени
    effective_timeshift = Config.LOCAL_TIMESHIFT + TIME_SHIFT_CORRECTION
    
    print(f"Символ: {symbol}")
    print(f"Дата: {target_date.strftime('%d.%m.%Y')}")
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
        
        # Обрабатываем тики
        times_local = []
        bids = []
        asks = []
        
        for tick in ticks_list:
            # Извлекаем данные тика
            if hasattr(tick, 'dtype') and tick.dtype.names:
                tick_time_utc = int(tick['time'])
                tick_bid = float(tick['bid'])
                tick_ask = float(tick['ask'])
            elif isinstance(tick, dict):
                tick_time_utc = int(tick['time'])
                tick_bid = float(tick['bid'])
                tick_ask = float(tick['ask'])
            elif hasattr(tick, 'time'):
                tick_time_utc = int(tick.time)
                tick_bid = float(tick.bid)
                tick_ask = float(tick.ask)
            else:
                tick_time_utc = int(tick[0])
                tick_bid = float(tick[1])
                tick_ask = float(tick[2])
            
            # Конвертируем UTC timestamp в локальное время
            tick_dt_utc = datetime.fromtimestamp(tick_time_utc)
            tick_dt_local = tick_dt_utc + timedelta(hours=effective_timeshift)
            
            times_local.append(tick_dt_local)
            bids.append(tick_bid)
            asks.append(tick_ask)
        
        print(f"Первый тик: {times_local[0].strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Последний тик: {times_local[-1].strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Строим график
        print("Построение графика...")
        
        fig, ax = plt.subplots(figsize=(16, 8))
        
        # Рисуем Bid и Ask
        ax.plot(times_local, bids, label='Bid', linewidth=0.5, alpha=0.7, color='blue')
        ax.plot(times_local, asks, label='Ask', linewidth=0.5, alpha=0.7, color='red')
        
        # Заполняем область между Bid и Ask (спред)
        ax.fill_between(times_local, bids, asks, alpha=0.2, color='gray', label='Спред')
        
        # Добавляем вертикальные линии для каждого часа
        hour_markers = []
        current_hour = time_in.replace(minute=0, second=0, microsecond=0)
        while current_hour <= time_out:
            hour_markers.append(current_hour)
            current_hour += timedelta(hours=1)
        
        for hour_marker in hour_markers:
            ax.axvline(x=hour_marker, color='green', linestyle='--', linewidth=0.8, alpha=0.5)
        
        # Настройка осей
        ax.set_xlabel('Время', fontsize=12)
        ax.set_ylabel('Цена', fontsize=12)
        ax.set_title(f'{symbol} - Тики за {target_date.strftime("%d.%m.%Y")}', fontsize=14, fontweight='bold')
        ax.legend(loc='best')
        ax.grid(True, alpha=0.3)
        
        # Форматирование оси времени
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        ax.xaxis.set_major_locator(mdates.HourLocator(interval=1))
        plt.xticks(rotation=45)
        
        # Улучшаем отображение
        plt.tight_layout()
        
        # Сохраняем график
        output_file = f"tests/ticks_chart_{symbol}_{target_date.strftime('%Y%m%d')}.png"
        plt.savefig(output_file, dpi=150, bbox_inches='tight')
        print(f"График сохранен: {output_file}")
        
        # Показываем график
        plt.show()
        
        # Статистика
        print()
        print("Статистика:")
        print(f"  Всего тиков: {len(ticks_list):,}")
        print(f"  Минимальная цена (Bid): {min(bids):.5f}")
        print(f"  Максимальная цена (Ask): {max(asks):.5f}")
        print(f"  Средний спред: {(sum(asks[i] - bids[i] for i in range(len(bids))) / len(bids)):.5f}")
        
        # Статистика по часам
        print()
        print("Статистика по часам:")
        hour_stats = {}
        for i, tick_time in enumerate(times_local):
            hour = tick_time.hour
            if hour not in hour_stats:
                hour_stats[hour] = {'count': 0, 'bids': [], 'asks': []}
            hour_stats[hour]['count'] += 1
            hour_stats[hour]['bids'].append(bids[i])
            hour_stats[hour]['asks'].append(asks[i])
        
        for hour in sorted(hour_stats.keys()):
            stats = hour_stats[hour]
            min_bid = min(stats['bids'])
            max_ask = max(stats['asks'])
            avg_spread = sum(stats['asks'][i] - stats['bids'][i] for i in range(len(stats['bids']))) / len(stats['bids'])
            print(f"  {hour:02d}:00 - Тиков: {stats['count']:>6,}, "
                  f"Диапазон: {min_bid:.5f} - {max_ask:.5f}, "
                  f"Спред: {avg_spread:.5f}")
    
    finally:
        connection.shutdown()
    
    print()
    print("=" * 70)
    print("Готово!")


if __name__ == "__main__":
    try:
        main_test()
    except KeyboardInterrupt:
        print("\n\nПрервано пользователем")
    except Exception as e:
        print(f"\nОшибка: {e}")
        import traceback
        traceback.print_exc()

