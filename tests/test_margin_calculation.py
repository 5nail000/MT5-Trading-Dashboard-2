"""
Тест расчета маржи для позиций

python tests/test_margin_calculation.py

"""

import sys
import os
from datetime import datetime

# Добавляем корневую папку проекта в путь
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.mt5.mt5_client import MT5Calculator
from src.mt5.mt5_client import MT5Connection


def main_test():
    """Основной тест расчета маржи"""
    print("🧪 ТЕСТ РАСЧЕТА МАРЖИ")
    print("=" * 70)
    print()
    
    # Инициализация подключения для получения информации об аккаунте
    connection = MT5Connection()
    account_info = None
    account_currency = "USD"  # По умолчанию
    
    if connection.initialize():
        try:
            account_info = connection.get_account_info()
            if account_info:
                account_currency = account_info.currency
                print(f"📊 Информация об аккаунте:")
                print(f"   Логин: {account_info.login}")
                print(f"   Сервер: {account_info.server}")
                print(f"   Валюта: {account_info.currency}")
                print(f"   Плечо: 1:{account_info.leverage}")
                print()
        except Exception as e:
            print(f"⚠️ Ошибка при получении информации об аккаунте: {e}")
            print()
        finally:
            connection.shutdown()
    else:
        print("⚠️ Не удалось подключиться к MT5 для получения информации об аккаунте")
        print("   Тест продолжит работу с параметрами по умолчанию")
        print()
    
    # Тестовые случаи
    test_cases = [
        {
            "symbol": "EURUSD",
            "lot_size": 0.1,
            "price": 1.10000,
            "description": "EURUSD, 0.1 лота, цена 1.10000"
        },
        {
            "symbol": "AUDUSD",
            "lot_size": 1.35,
            "price": 0.65400,
            "description": "AUDUSD, 1.35 лота, цена 0.65400"
        },
        {
            "symbol": "AUDCAD",
            "lot_size": 0.3,
            "price": 0.91075,
            "description": "AUDCAD, 0.3 лота, цена 0.91075"
        },
        {
            "symbol": "GBPUSD",
            "lot_size": 0.86,
            "price": 1.31800,
            "description": "GBPUSD, 0.86 лота, цена 1.31800"
        },
        {
            "symbol": "USDJPY",
            "lot_size": 0.1,
            "price": 150.000,
            "description": "USDJPY, 0.1 лота, цена 150.000"
        },
        {
            "symbol": "XAUUSD",
            "lot_size": 0.07,
            "price": 4083.040,
            "description": "XAUUSD, 0.07 лота, цена 4083.040"
        },
        {
            "symbol": "USDCAD",
            "lot_size": 0.1,
            "price": 1.3858,
            "description": "USDCAD, 0.1 лота, цена 1.3858"
        },
        {
            "symbol": "USDCHF",
            "lot_size": 1.73,
            "price": 0.80507,
            "description": "USDCHF, 1.73 лота, цена 0.80507"
        },
        {
            "symbol": "USTEC",
            "lot_size": 1.43,
            "price": 25178.7,
            "description": "USTEC, 1.43 лота, цена 25178.7"
        },
    ]
    
    print("📊 Тестовые расчеты маржи:")
    print("-" * 70)
    
    for i, test_case in enumerate(test_cases, 1):
        symbol = test_case["symbol"]
        lot_size = test_case["lot_size"]
        price = test_case["price"]
        description = test_case["description"]
        
        print(f"\n{i}. {description}")
        print(f"   Символ: {symbol}")
        print(f"   Размер лота: {lot_size}")
        print(f"   Цена: {price}")
        
        margin = MT5Calculator.calculate_margin(symbol, lot_size, price)
        
        if margin is not None:
            print(f"   ✅ Маржа: {margin:.2f} {account_currency}")
        else:
            print(f"   ❌ Не удалось рассчитать маржу")
    
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

