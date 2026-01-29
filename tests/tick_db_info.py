"""
Утилита для анализа содержимого базы данных с тиковыми данными

# Общая статистика
python tests/tick_db_info.py
python tests/tick_db_info.py --compressed

# Детальная информация по конкретному серверу/символу
python tests/tick_db_info.py --detailed --server "Tickmill-Demo" --symbol "EURUSD"

"""

import sys
import os
from datetime import datetime, timedelta
from collections import defaultdict
import glob

# Добавляем корневую папку проекта в путь
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.tick_db_manager import tick_db_manager
from src.database.tick_db_manager_compressed import compressed_tick_db_manager
from src.config.settings import Config
import sqlite3
import glob


def get_detailed_statistics(use_compressed: bool = False):
    """Получить детальную статистику по БД"""
    print("📊 ДЕТАЛЬНАЯ СТАТИСТИКА БАЗЫ ДАННЫХ ТИКОВ")
    if use_compressed:
        print("   (Сжатые данные)")
    print("=" * 80)
    print()
    
    # Choose manager
    manager = compressed_tick_db_manager if use_compressed else tick_db_manager
    
    # Find all server database files
    db_files = glob.glob(os.path.join(manager.data_dir, "*.db"))
    
    if not db_files:
        data_type = "compressed" if use_compressed else "uncompressed"
        print(f"⚠️ Не найдено файлов БД в папке {manager.data_dir}")
        return
    
    print(f"📁 Найдено файлов БД: {len(db_files)}")
    print()
    
    # Process each server database
    for db_file in sorted(db_files):
        server_name = os.path.splitext(os.path.basename(db_file))[0]
        print(f"🔹 СЕРВЕР: {server_name}")
        print("-" * 80)
        
        # Get statistics for this server
        stats = manager.get_statistics(server_name)
        
        print(f"   Файл БД: {stats['database_path']}")
        print(f"   Размер: {stats['database_size_mb']:.2f} MB")
        if use_compressed and 'total_batches' in stats:
            print(f"   Батчей: {stats['total_batches']:,}")
        print(f"   Тиков: {stats['total_ticks']:,}")
        print(f"   Символов: {stats['unique_symbols']}")
        print(f"   Диапазонов (месяцев): {stats['total_month_ranges']}")
        print()
        
        # Get detailed info for each symbol
        with manager.get_connection(server_name) as conn:
            cursor = conn.cursor()
            
            # Статистика по символам для этого сервера
            cursor.execute("""
                SELECT symbol, SUM(tick_count) as tick_count, COUNT(*) as batch_count
                FROM tick_batches
                GROUP BY symbol
                ORDER BY tick_count DESC
            """)
            symbols = cursor.fetchall()
            if symbols:
                print("   Символы:")
                for symbol, tick_count, batch_count in symbols:
                    print(f"      {symbol}:")
                    print(f"         Тиков: {tick_count:,}")
                    print(f"         Батчей: {batch_count:,}")
            else:
                print("   Нет данных")
            print()
            
            # Статистика по парам символ-период
            cursor.execute("""
                SELECT symbol, MIN(batch_start_time) as first_tick, MAX(batch_end_time) as last_tick,
                       SUM(tick_count) as tick_count
                FROM tick_batches
                GROUP BY symbol
                ORDER BY tick_count DESC
            """)
            pairs = cursor.fetchall()
            if pairs:
                print("   Периоды данных по символам:")
                for symbol, first_tick, last_tick, tick_count in pairs:
                    first_dt = (datetime.fromtimestamp(first_tick) + timedelta(hours=Config.LOCAL_TIMESHIFT)) if first_tick else None
                    last_dt = (datetime.fromtimestamp(last_tick) + timedelta(hours=Config.LOCAL_TIMESHIFT)) if last_tick else None
                    print(f"      {symbol}:")
                    print(f"         Тиков: {tick_count:,}")
                    if first_dt and last_dt:
                        print(f"         Период: {first_dt.strftime('%d.%m.%Y %H:%M:%S')} - {last_dt.strftime('%d.%m.%Y %H:%M:%S')} (местное время)")
                        duration = last_dt - first_dt
                        print(f"         Длительность: {duration.days} дней")
            else:
                print("   Нет данных")
            print()
            
            # Детальная информация по диапазонам для этого сервера
            cursor.execute("""
                SELECT symbol, year, month, 
                       first_tick_time, last_tick_time, tick_count
                FROM tick_ranges
                ORDER BY symbol, year, month
            """)
            ranges = cursor.fetchall()
            if ranges:
                print("   Детальная информация по диапазонам (месяцам):")
                current_symbol = None
                for symbol, year, month, first_tick, last_tick, tick_count in ranges:
                    if symbol != current_symbol:
                        if current_symbol is not None:
                            print()
                        current_symbol = symbol
                        print(f"      📌 {symbol}:")
                    
                    # Convert UTC timestamp to local time
                    first_dt = (datetime.fromtimestamp(first_tick) + timedelta(hours=Config.LOCAL_TIMESHIFT)) if first_tick else None
                    last_dt = (datetime.fromtimestamp(last_tick) + timedelta(hours=Config.LOCAL_TIMESHIFT)) if last_tick else None
                    
                    first_str = first_dt.strftime('%d.%m.%Y %H:%M:%S') if first_dt else 'N/A'
                    last_str = last_dt.strftime('%d.%m.%Y %H:%M:%S') if last_dt else 'N/A'
                    
                    print(f"         {year}-{month:02d}: {tick_count:,} тиков")
                    print(f"            {first_str} - {last_str} (местное время)")
            else:
                print("   Нет данных")
            print()
        
        print()
    
    print("=" * 80)
    print("✅ Анализ завершен!")


def show_server_symbol_info(server: str = None, symbol: str = None, use_compressed: bool = False):
    """Показать детальную информацию по конкретному серверу/символу"""
    print("📋 ДЕТАЛЬНАЯ ИНФОРМАЦИЯ ПО СЕРВЕРУ/СИМВОЛУ")
    if use_compressed:
        print("   (Сжатые данные)")
    print("=" * 80)
    print()
    
    manager = compressed_tick_db_manager if use_compressed else tick_db_manager
    manager.init_database(server)
    
    with manager.get_connection(server) as conn:
        cursor = conn.cursor()
        
        if server and symbol:
            print(f"🔍 Сервер: {server} | Символ: {symbol}")
            print("-" * 80)
            
            # Получить все диапазоны
            ranges = manager.get_available_ranges(server, symbol)
            if ranges:
                print(f"   Доступно диапазонов (месяцев): {len(ranges)}")
                print()
                print("   Диапазоны:")
                for r in ranges:
                    first_dt = (datetime.fromtimestamp(r['first_tick_time']) + timedelta(hours=Config.LOCAL_TIMESHIFT)) if r['first_tick_time'] else None
                    last_dt = (datetime.fromtimestamp(r['last_tick_time']) + timedelta(hours=Config.LOCAL_TIMESHIFT)) if r['last_tick_time'] else None
                    first_str = first_dt.strftime('%d.%m.%Y %H:%M:%S') if first_dt else 'N/A'
                    last_str = last_dt.strftime('%d.%m.%Y %H:%M:%S') if last_dt else 'N/A'
                    print(f"      {r['year']}-{r['month']:02d}: {r['tick_count']:,} тиков")
                    print(f"         {first_str} - {last_str} (местное время)")
            else:
                print("   Нет данных для этой пары")
            
            # Статистика по ценам
            # Get some sample ticks to show price range
            if use_compressed:
                cursor.execute("""
                    SELECT MIN(batch_start_time), MAX(batch_end_time)
                    FROM tick_batches
                    WHERE symbol = ?
                """, (symbol,))
            else:
                cursor.execute("""
                    SELECT MIN(time), MAX(time)
                    FROM ticks
                    WHERE symbol = ?
                """, (symbol,))
            result = cursor.fetchone()
            if result and result[0]:
                from_time = datetime.fromtimestamp(result[0])
                to_time = datetime.fromtimestamp(result[1])
                ticks = manager.get_ticks(server, symbol, from_time, to_time)
                if ticks:
                    bids = [t['bid'] for t in ticks]
                    asks = [t['ask'] for t in ticks]
                    print()
                    print("   Статистика по ценам:")
                    print(f"      Bid: MIN={min(bids):.5f}, MAX={max(bids):.5f}, AVG={sum(bids)/len(bids):.5f}")
                    print(f"      Ask: MIN={min(asks):.5f}, MAX={max(asks):.5f}, AVG={sum(asks)/len(asks):.5f}")
        else:
            print("⚠️ Укажите server и symbol для детальной информации")
            print()
            print("Доступные пары:")
            # List all servers and symbols
            for manager_type, mgr in [("uncompressed", tick_db_manager), ("compressed", compressed_tick_db_manager)]:
                db_files = glob.glob(os.path.join(mgr.data_dir, "*.db"))
                if db_files:
                    print(f"   {manager_type}:")
                    for db_file in sorted(db_files):
                        server_name = os.path.splitext(os.path.basename(db_file))[0]
                        with mgr.get_connection(server_name) as conn2:
                            cursor2 = conn2.cursor()
                            if manager_type == "compressed":
                                cursor2.execute("SELECT DISTINCT symbol FROM tick_batches ORDER BY symbol")
                            else:
                                cursor2.execute("SELECT DISTINCT symbol FROM ticks ORDER BY symbol")
                            symbols = cursor2.fetchall()
                            for (sym,) in symbols:
                                print(f"      {server_name} | {sym}")


def main():
    """Главная функция"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Утилита для анализа БД с тиковыми данными')
    parser.add_argument('--server', type=str, help='Фильтр по серверу')
    parser.add_argument('--symbol', type=str, help='Фильтр по символу')
    parser.add_argument('--detailed', action='store_true', help='Детальная информация по серверу/символу')
    parser.add_argument('--recalculate', action='store_true', help='Пересчитать диапазоны на основе реальных данных')
    parser.add_argument('--compressed', action='store_true', help='Работать со сжатыми данными')
    
    args = parser.parse_args()
    
    use_compressed = args.compressed
    manager = compressed_tick_db_manager if use_compressed else tick_db_manager
    
    if args.recalculate:
        print("🔄 Пересчет диапазонов на основе реальных данных...")
        print("-" * 80)
        if args.server:
            manager.recalculate_ranges(
                server=args.server,
                symbol=args.symbol if args.symbol else None
            )
        else:
            print("⚠️ Для пересчета необходимо указать --server")
        print()
        print("✅ Пересчет завершен!")
        print()
        print("📊 Обновленная статистика:")
        print("-" * 80)
        get_detailed_statistics(use_compressed=use_compressed)
    elif args.detailed and args.server and args.symbol:
        show_server_symbol_info(args.server, args.symbol, use_compressed=use_compressed)
    else:
        get_detailed_statistics(use_compressed=use_compressed)
        if args.server or args.symbol:
            print()
            print("💡 Для детальной информации используйте: --detailed --server SERVER --symbol SYMBOL")
        print()
        print("💡 Для пересчета диапазонов используйте: --recalculate --server SERVER [--symbol SYMBOL]")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Прервано пользователем")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
