"""
Тест расчета прибыли/убытка для позиций

python tests/test_profit_loss_calculation.py
"""

import sys
import os
from datetime import datetime

# Добавляем корневую папку проекта в путь
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.mt5.mt5_client import MT5Calculator
from src.mt5.mt5_client import MT5Connection


def main_test():
    """Основной тест расчета прибыли/убытка"""
    print("ТЕСТ РАСЧЕТА ПРИБЫЛИ/УБЫТКА")
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
            "lot_size": 0.1,
            "price_open": 1.10000,
            "direction": "Buy",
            "price_target": 1.10500,
            "description": "EURUSD, 0.1 лота, Buy, вход 1.10000, цель 1.10500"
        },
        {
            "symbol": "AUDCAD",
            "lot_size": 0.3,
            "price_open": 0.91075,
            "direction": "Sell",
            "price_target": 0.90075,
            "description": "AUDCAD, 0.3 лота, Sell, вход 0.91075, цель 0.90075"
        },
        {
            "symbol": "GBPUSD",
            "lot_size": 0.1,
            "price_open": 1.25000,
            "direction": "Sell",
            "price_target": 1.3125,
            "description": "GBPUSD, 0.1 лот, Sell, вход 1.25000, цель 1.3125"
        },
        {
            "symbol": "USDJPY",
            "lot_size": 0.1,
            "price_open": 150.000,
            "direction": "Buy",
            "price_target": 150.500,
            "description": "USDJPY, 0.1 лота, Buy, вход 150.000, цель 150.500"
        },
        {
            "symbol": "XAUUSD",
            "lot_size": 0.25,
            "price_open": 4082.010,
            "direction": "Buy",
            "price_target": 3919.61,
            "description": "XAUUSD, 0.25 лота, Buy, вход 4082.010, цель 3919.61"
        },
        {
            "symbol": "USTEC",
            "lot_size": 1.43,
            "price_open": 25178.7,
            "direction": "Sell",
            "price_target": 22989.73,
            "description": "USTEC, 1.43 лота, Sell, вход 25178.7, цель 22989.73"
        },
    ]
    
    print("Тестовые расчеты прибыли/убытка:")
    print("-" * 70)
    
    for i, test_case in enumerate(test_cases, 1):
        symbol = test_case["symbol"]
        lot_size = test_case["lot_size"]
        price_open = test_case["price_open"]
        direction = test_case["direction"]
        price_target = test_case["price_target"]
        description = test_case["description"]
        
        print(f"\n{i}. {description}")
        print(f"   Символ: {symbol}")
        print(f"   Размер лота: {lot_size}")
        print(f"   Направление: {direction}")
        print(f"   Цена входа: {price_open}")
        print(f"   Целевая цена: {price_target}")
        
        profit_loss = MT5Calculator.calculate_profit_loss(
            symbol, lot_size, price_open, direction, price_target
        )
        
        if profit_loss is not None:
            status = "прибыль" if profit_loss >= 0 else "убыток"
            print(f"   Результат: {profit_loss:.2f} {account_currency} ({status})")
        else:
            print(f"   Не удалось рассчитать прибыль/убыток")
    
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

