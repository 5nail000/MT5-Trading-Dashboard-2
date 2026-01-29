"""
Тест расчета агрегированной позиции (общий уровень входа и объём)

python tests/test_aggregated_position.py
"""

import sys
import os
from datetime import datetime

# Добавляем корневую папку проекта в путь
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.mt5.mt5_client import MT5Calculator


def main_test():
    """Основной тест расчета агрегированной позиции"""
    print("ТЕСТ РАСЧЕТА АГРЕГИРОВАННОЙ ПОЗИЦИИ")
    print("=" * 70)
    print()
    
    # Тестовые случаи
    test_cases = [
        {
            "name": "EURUSD - несколько Buy позиций",
            "positions": [
                {"symbol": "EURUSD", "direction": "Buy", "volume": 0.1, "price_open": 1.10000},
                {"symbol": "EURUSD", "direction": "Buy", "volume": 0.2, "price_open": 1.10100},
                {"symbol": "EURUSD", "direction": "Buy", "volume": 0.1, "price_open": 1.10200},
            ]
        },
        {
            "name": "GBPUSD - несколько Sell позиций",
            "positions": [
                {"symbol": "GBPUSD", "direction": "Sell", "volume": 0.5, "price_open": 1.25000},
                {"symbol": "GBPUSD", "direction": "Sell", "volume": 0.3, "price_open": 1.25100},
                {"symbol": "GBPUSD", "direction": "Sell", "volume": 0.2, "price_open": 1.25200},
            ]
        },
        {
            "name": "XAUUSD - одна большая позиция",
            "positions": [
                {"symbol": "XAUUSD", "direction": "Buy", "volume": 1.0, "price_open": 2000.00},
            ]
        },
        {
            "name": "USDJPY - много маленьких позиций",
            "positions": [
                {"symbol": "USDJPY", "direction": "Buy", "volume": 0.01, "price_open": 150.000},
                {"symbol": "USDJPY", "direction": "Buy", "volume": 0.01, "price_open": 150.100},
                {"symbol": "USDJPY", "direction": "Buy", "volume": 0.01, "price_open": 150.200},
                {"symbol": "USDJPY", "direction": "Buy", "volume": 0.01, "price_open": 150.300},
                {"symbol": "USDJPY", "direction": "Buy", "volume": 0.01, "price_open": 150.400},
            ]
        },
    ]
    
    print("Тестовые расчеты агрегированных позиций:")
    print("-" * 70)
    
    for i, test_case in enumerate(test_cases, 1):
        name = test_case["name"]
        positions = test_case["positions"]
        
        print(f"\n{i}. {name}")
        print(f"   Входные позиции:")
        for j, pos in enumerate(positions, 1):
            print(f"      {j}. {pos['symbol']} {pos['direction']} {pos['volume']} лот(ов) @ {pos['price_open']}")
        
        result = MT5Calculator.calculate_aggregated_position(positions)
        
        if result:
            print(f"   Результат:")
            print(f"      Символ: {result['symbol']}")
            print(f"      Направление: {result['direction']}")
            print(f"      Общий объём: {result['total_volume']:.2f} лот(ов)")
            print(f"      Средневзвешенная цена: {result['average_price']:.5f}")
            print(f"      Количество позиций: {result['positions_count']}")
            
            # Проверка расчета
            manual_total_volume = sum(p['volume'] for p in positions)
            manual_total_price_volume = sum(p['volume'] * p['price_open'] for p in positions)
            manual_average = manual_total_price_volume / manual_total_volume
            
            print(f"   Проверка:")
            print(f"      Общий объём (вручную): {manual_total_volume:.2f}")
            print(f"      Средняя цена (вручную): {manual_average:.5f}")
            match = "OK" if abs(result['average_price'] - manual_average) < 0.00001 else "ERROR"
            print(f"      Совпадение: {match}")
        else:
            print(f"   Не удалось рассчитать агрегированную позицию")
    
    # Тест с некорректными данными
    print(f"\n{len(test_cases) + 1}. Тест с некорректными данными:")
    print("-" * 70)
    
    invalid_cases = [
        {
            "name": "Пустой список",
            "positions": []
        },
        {
            "name": "Разные символы",
            "positions": [
                {"symbol": "EURUSD", "direction": "Buy", "volume": 0.1, "price_open": 1.10000},
                {"symbol": "GBPUSD", "direction": "Buy", "volume": 0.1, "price_open": 1.25000},
            ]
        },
        {
            "name": "Разные направления",
            "positions": [
                {"symbol": "EURUSD", "direction": "Buy", "volume": 0.1, "price_open": 1.10000},
                {"symbol": "EURUSD", "direction": "Sell", "volume": 0.1, "price_open": 1.10000},
            ]
        },
    ]
    
    for invalid_case in invalid_cases:
        print(f"\n   {invalid_case['name']}:")
        result = MT5Calculator.calculate_aggregated_position(invalid_case['positions'])
        if result is None:
            print(f"      OK - Корректно обработано (вернул None)")
        else:
            print(f"      ERROR - Должен был вернуть None, но вернул {result}")
    
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

