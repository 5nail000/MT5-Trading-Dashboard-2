"""
Тест загрузки и работы с тиковыми данными (без сжатия)
"""

import sys
import os
from datetime import datetime, timedelta

# Добавляем корневую папку проекта в путь
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.mt5.tick_data import mt5_tick_provider
from src.database.tick_db_manager import tick_db_manager
from src.config.settings import Config


def main_test():
    """Основной тест загрузки тиков"""
    print("🧪 ТЕСТ ЗАГРУЗКИ ТИКОВЫХ ДАННЫХ")
    print("=" * 70)
    
    symbol = "EURUSD"
    test_from = datetime(2025, 1, 1)
    test_to = datetime(2025, 9, 30, 23, 59, 59)
    
    print(f"📊 Символ: {symbol}")
    print(f"📅 Период: {test_from.strftime('%d.%m.%Y')} - {test_to.strftime('%d.%m.%Y')}")
    print()
    
    # Инициализация БД
    print("🔧 Инициализация базы данных...")
    # БД будет инициализирована автоматически при первом использовании
    print("✅ База данных готова")
    print()
    
    # Статистика БД до загрузки
    print("📊 Статистика БД до загрузки:")
    # Получаем список серверов из account
    try:
        from src.mt5.mt5_client import MT5Connection
        connection = MT5Connection()
        if connection.initialize():
            account_info = connection.get_account_info()
            server = getattr(account_info, 'server', 'unknown') if account_info else 'unknown'
            connection.shutdown()
        else:
            server = 'unknown'
    except:
        server = 'unknown'
    
    if server != 'unknown':
        stats_before = tick_db_manager.get_statistics(server)
        print(f"   Файл БД: {stats_before['database_path']}")
        print(f"   Размер: {stats_before['database_size_mb']:.2f} MB")
        print(f"   Тиков: {stats_before['total_ticks']:,}")
        print(f"   Символов: {stats_before['unique_symbols']}")
    else:
        print("   Не удалось определить сервер")
    print()
    
    # Загрузка тиков из MT5
    print("📥 Загрузка тиков из MT5...")
    result = mt5_tick_provider.download_and_save_ticks(
        symbol=symbol,
        from_date=test_from,
        to_date=test_to,
        auto_fill_months=True
    )
    
    print()
    print("=" * 70)
    print("📊 РЕЗУЛЬТАТЫ ЗАГРУЗКИ:")
    print("-" * 70)
    print(f"Сервер: {result['server']}")
    print(f"Символ: {result['symbol']}")
    print(f"Тиков загружено: {result['ticks_downloaded']:,}")
    print(f"Месяцев обработано: {len(result['months_processed'])}")
    
    if result['months_processed']:
        print()
        print("Детали по месяцам:")
        for month_info in result['months_processed']:
            print(f"  {month_info['year']}-{month_info['month']:02d}: {month_info['ticks']:,} тиков")
    
    if result.get('errors'):
        print()
        print("⚠️ Ошибки:")
        for error in result['errors']:
            print(f"  {error}")
    print()
    
    # Статистика БД после загрузки
    if result['server'] != 'unknown':
        stats_after = tick_db_manager.get_statistics(result['server'])
        print("📊 Статистика БД после загрузки:")
        print(f"   Файл БД: {stats_after['database_path']}")
        print(f"   Размер: {stats_after['database_size_mb']:.2f} MB")
        print(f"   Тиков: {stats_after['total_ticks']:,}")
        print(f"   Символов: {stats_after['unique_symbols']}")
        print(f"   Диапазонов (месяцев): {stats_after['total_month_ranges']}")
        print()
        
        # Доступные диапазоны данных
        print("📅 Доступные диапазоны данных:")
        ranges = tick_db_manager.get_available_ranges(result['server'], symbol)
        if ranges:
            for r in ranges:
                first_dt = datetime.fromtimestamp(r['first_tick_time']) + timedelta(hours=Config.LOCAL_TIMESHIFT)
                last_dt = datetime.fromtimestamp(r['last_tick_time']) + timedelta(hours=Config.LOCAL_TIMESHIFT)
                print(f"  {r['year']}-{r['month']:02d}: "
                      f"{first_dt.strftime('%d.%m.%Y %H:%M')} - {last_dt.strftime('%d.%m.%Y %H:%M')} "
                      f"({r['tick_count']:,} тиков)")
        else:
            print("  Нет данных")
        print()
    
    # Тест получения тиков из БД
    print("🔍 Тест получения тиков из БД:")
    test_from_single = datetime(2025, 9, 13, 0, 0, 0)
    test_to_single = datetime(2025, 9, 13, 23, 59, 59)
    
    ticks = mt5_tick_provider.get_ticks_from_db(
        symbol=symbol,
        from_date=test_from_single,
        to_date=test_to_single
    )
    
    if ticks:
        print(f"   Период: {test_from_single.strftime('%d.%m.%Y')} - {test_to_single.strftime('%d.%m.%Y')}")
        print(f"   Получено тиков: {len(ticks):,}")
        
        first_tick_dt = datetime.fromtimestamp(ticks[0]['time']) + timedelta(hours=Config.LOCAL_TIMESHIFT)
        last_tick_dt = datetime.fromtimestamp(ticks[-1]['time']) + timedelta(hours=Config.LOCAL_TIMESHIFT)
        print(f"   Первый тик: {first_tick_dt.strftime('%d.%m.%Y %H:%M:%S')}")
        print(f"   Последний тик: {last_tick_dt.strftime('%d.%m.%Y %H:%M:%S')}")
        
        bids = [t['bid'] for t in ticks]
        asks = [t['ask'] for t in ticks]
        print(f"   Bid диапазон: {min(bids):.5f} - {max(bids):.5f}")
        print(f"   Ask диапазон: {min(asks):.5f} - {max(asks):.5f}")
    else:
        print("   Тики не найдены")
    print()
    
    # Тест получения HIGH/LOW
    print("📊 Тест получения HIGH/LOW цен:")
    high_low = mt5_tick_provider.get_high_low_prices(
        symbol=symbol,
        from_date=test_from_single,
        to_date=test_to_single,
        server=result['server']
    )
    print(f"   Сервер: {result['server']}")
    high_str = f"{high_low['high']:.5f}" if high_low['high'] is not None else 'N/A'
    low_str = f"{high_low['low']:.5f}" if high_low['low'] is not None else 'N/A'
    print(f"   HIGH (ask): {high_str}")
    print(f"   LOW (bid): {low_str}")
    
    print()
    print("=" * 70)
    print("✅ Тест завершен!")


if __name__ == "__main__":
    try:
        main_test()
    except KeyboardInterrupt:
        print("\n👋 Тест прерван")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
