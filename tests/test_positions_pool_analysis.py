"""
Тест анализа пула позиций

python tests/test_positions_pool_analysis.py
"""

import sys
import os
from datetime import datetime

# Добавляем корневую папку проекта в путь
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.mt5.mt5_client import MT5Calculator, MT5Connection


def main_test():
    """Основной тест анализа пула позиций"""
    print("ТЕСТ АНАЛИЗА ПУЛА ПОЗИЦИЙ")
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
            "name": "Один символ, одно направление (Buy)",
            "positions": [
                {"symbol": "EURUSD", "direction": "Buy", "volume": 0.1, "price_open": 1.10000},
                {"symbol": "EURUSD", "direction": "Buy", "volume": 0.2, "price_open": 1.10100},
            ],
            "time_in": datetime(2025, 9, 13, 0, 0, 0),
            "time_out": datetime(2025, 9, 13, 23, 59, 59),
        },
        {
            "name": "Один символ, разнонаправленные позиции (хедж)",
            "positions": [
                {"symbol": "EURUSD", "direction": "Buy", "volume": 0.1, "price_open": 1.10000},
                {"symbol": "EURUSD", "direction": "Sell", "volume": 0.1, "price_open": 1.10100},
            ],
            "time_in": datetime(2025, 9, 13, 0, 0, 0),
            "time_out": datetime(2025, 9, 13, 23, 59, 59),
        },
        {
            "name": "Несколько символов, разные направления",
            "positions": [
                {"symbol": "EURUSD", "direction": "Buy", "volume": 0.1, "price_open": 1.10000},
                {"symbol": "GBPUSD", "direction": "Sell", "volume": 0.1, "price_open": 1.25000},
                {"symbol": "XAUUSD", "direction": "Buy", "volume": 0.25, "price_open": 2000.00},
            ],
            "time_in": datetime(2025, 9, 11, 0, 0, 0),
            "time_out": datetime(2025, 9, 12, 23, 59, 59),
        },
        {
            "name": "Сложный случай: несколько позиций по разным символам",
            "positions": [
                {"symbol": "EURUSD", "direction": "Buy", "volume": 0.1, "price_open": 1.10000},
                {"symbol": "EURUSD", "direction": "Buy", "volume": 0.2, "price_open": 1.10100},
                {"symbol": "EURUSD", "direction": "Sell", "volume": 0.15, "price_open": 1.10200},
                {"symbol": "GBPUSD", "direction": "Sell", "volume": 0.1, "price_open": 1.25000},
                {"symbol": "XAUUSD", "direction": "Buy", "volume": 0.25, "price_open": 2000.00},
            ],
            "time_in": datetime(2025, 9, 11, 0, 0, 0),
            "time_out": datetime(2025, 9, 12, 23, 59, 59),
        },
    ]
    
    print("Тестовые случаи анализа пула позиций:")
    print("-" * 70)
    
    for i, test_case in enumerate(test_cases, 1):
        name = test_case["name"]
        positions = test_case["positions"]
        time_in = test_case["time_in"]
        time_out = test_case["time_out"]
        
        print(f"\n{i}. {name}")
        print(f"   Входные позиции ({len(positions)} шт.):")
        for j, pos in enumerate(positions, 1):
            print(f"      {j}. {pos['symbol']} {pos['direction']} {pos['volume']} лот(ов) @ {pos['price_open']}")
        print(f"   Период: {time_in.strftime('%d.%m.%Y %H:%M:%S')} - {time_out.strftime('%d.%m.%Y %H:%M:%S')}")
        
        result = MT5Calculator.analyze_positions_pool(
            positions, time_in, time_out
        )
        
        if result:
            print(f"\n   Результат:")
            print(f"      Агрегированных позиций: {len(result['aggregated_positions'])}")
            
            for agg_pos in result['aggregated_positions']:
                print(f"      - {agg_pos['symbol']} {agg_pos['direction']}: "
                      f"{agg_pos['total_volume']:.2f} лот(ов) @ {agg_pos['average_price']:.5f}")
                if 'high' in agg_pos and 'low' in agg_pos and agg_pos['high'] and agg_pos['low']:
                    print(f"        HIGH: {agg_pos['high']:.5f}, LOW: {agg_pos['low']:.5f}")
                if 'worst_profit_loss' in agg_pos:
                    worst_pl = agg_pos['worst_profit_loss']
                    worst_str = f"{worst_pl:+.2f}" if worst_pl is not None else 'N/A'
                    print(f"        Наихудший P/L: {worst_str}")
            
            print(f"      Общая маржа: {result['total_margin']:.2f}")
            worst_equity = result['total_worst_equity']
            worst_equity_str = f"{worst_equity:+.2f}" if worst_equity is not None else 'N/A'
            print(f"      Наихудшее эквити: {worst_equity_str}")
            
            # Интерпретация результата
            if worst_equity is not None:
                if worst_equity < 0:
                    print(f"      ⚠️  Потенциальный убыток: {abs(worst_equity):.2f}")
                elif worst_equity > 0:
                    print(f"      ✅ Потенциальная прибыль: {worst_equity:.2f}")
                else:
                    print(f"      ➖ Нейтральное состояние")
        else:
            print(f"   Не удалось проанализировать пул позиций")
    
    # Тест с пустым пулом
    print(f"\n{len(test_cases) + 1}. Тест с пустым пулом:")
    print("-" * 70)
    result = MT5Calculator.analyze_positions_pool(
        [], datetime(2025, 9, 13, 0, 0, 0), datetime(2025, 9, 13, 23, 59, 59)
    )
    if result and result['aggregated_positions'] == [] and result['total_margin'] == 0.0:
        print("   OK - Корректно обработан пустой пул")
    else:
        print(f"   ERROR - Неожиданный результат: {result}")
    
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

