"""
Тест получения HIGH/LOW цен по тиковым данным

python tests/test_high_low_prices.py
"""

import sys
import os
from datetime import datetime, timedelta

# Добавляем корневую папку проекта в путь
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.mt5.mt5_client import MT5Calculator, MT5Connection
from src.config.settings import Config


def main_test():
    """Основной тест получения HIGH/LOW цен"""
    print("ТЕСТ ПОЛУЧЕНИЯ HIGH/LOW ЦЕН")
    print("=" * 70)
    print()
    
    # Инициализация подключения для получения информации об аккаунте
    connection = MT5Connection()
    account_info = None
    
    if connection.initialize():
        try:
            account_info = connection.get_account_info()
            if account_info:
                print(f"Информация об аккаунте:")
                print(f"   Логин: {account_info.login}")
                print(f"   Сервер: {account_info.server}")
                print(f"   Валюта: {account_info.currency}")
                print()
        except Exception as e:
            print(f"Ошибка при получении информации об аккаунте: {e}")
            print()
        finally:
            connection.shutdown()
    else:
        print("Не удалось подключиться к MT5 для получения информации об аккаунте")
        print("   Тест продолжит работу с параметрами по умолчанию")
        print()
    
    # Тестовые случаи
    test_cases = [
        {
            "symbol": "EURUSD",
            "time_in": datetime(2025, 10, 13, 0, 0, 0),
            "time_out": datetime(2025, 10, 13, 23, 59, 59),
            "description": "EURUSD, 13 сентября 2024"
        },
        {
            "symbol": "GBPUSD",
            "time_in": datetime(2025, 9, 15, 0, 0, 0),
            "time_out": datetime(2025, 9, 15, 23, 59, 59),
            "description": "GBPUSD, 13 сентября 2024"
        },
        {
            "symbol": "XAUUSD",
            "time_in": datetime(2025, 9, 11, 0, 0, 0),
            "time_out": datetime(2025, 9, 12, 23, 59, 59),
            "description": "XAUUSD, 13 сентября 2024"
        },
        {
            "symbol": "XAUUSD",
            "time_in": datetime(2025, 11, 13, 16, 40, 21),
            "time_out": datetime(2025, 11, 13, 16, 44, 16),
            "description": "XAUUSD, 13 ноября 2025"
        },
        {
            "symbol": "XAUUSD",
            "time_in": datetime(2025, 11, 14, 16, 32, 47),
            "time_out": datetime(2025, 11, 14, 16, 34, 36),
            "description": "XAUUSD, 13 ноября 2025"
        },
    ]
    
    print("Тестовые запросы HIGH/LOW цен:")
    print("-" * 70)
    
    for i, test_case in enumerate(test_cases, 1):
        symbol = test_case["symbol"]
        time_in = test_case["time_in"]
        time_out = test_case["time_out"]
        description = test_case["description"]
        
        print(f"\n{i}. {description}")
        print(f"   Символ: {symbol}")
        print(f"   Период: {time_in.strftime('%d.%m.%Y %H:%M:%S')} - {time_out.strftime('%d.%m.%Y %H:%M:%S')}")
        
        high_low = MT5Calculator.get_high_low_prices(
            symbol, time_in, time_out
        )
        
        if high_low:
            high_str = f"{high_low['high']:.5f}" if high_low['high'] is not None else 'N/A'
            low_str = f"{high_low['low']:.5f}" if high_low['low'] is not None else 'N/A'
            print(f"   HIGH (ask): {high_str}")
            print(f"   LOW (bid): {low_str}")
            
            if high_low['high'] is not None and high_low['low'] is not None:
                spread = high_low['high'] - high_low['low']
                print(f"   Диапазон: {spread:.5f}")
        else:
            print(f"   Не удалось получить HIGH/LOW цены")
    
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

