"""
Основной тест функции calculate_balance_at_date
"""

import sys
import os
from datetime import datetime

# Добавляем корневую папку проекта в путь
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.mt5.mt5_client import mt5_data_provider, mt5_calculator


def main_test():
    """Основной тест функции calculate_balance_at_date"""
    
    print("🧮 ТЕСТ ФУНКЦИИ calculate_balance_at_date")
    print("=" * 50)
    
    # Получаем данные
    from_date = datetime(2025, 9, 1)
    to_date = datetime(2025, 10, 15)
    
    print("🔄 Получение данных...")
    deals, account_info = mt5_data_provider.get_history(
        from_date=from_date,
        to_date=to_date
    )
    
    if deals is None:
        print("❌ Не удалось получить данные")
        return
    
    print(f"✅ Получено сделок: {len(deals)}")
    
    if account_info:
        print(f"🏦 Аккаунт: {account_info.login}")
        print(f"📈 Текущий баланс MT5: {account_info.balance:.2f}")
    
    print()
    
    # Тестируем разные даты
    test_dates = [
        ("10 октября", "2025-10-10"),
        ("Суббота", "2025-09-27"),
        ("Воскресенье", "2025-09-28"),
    ]
    
    for day_name, date_str in test_dates:
        target_date = datetime.strptime(date_str, "%Y-%m-%d")
        
        print(f"📅 {day_name} ({date_str}):")
        
        # Баланс на начало дня (по умолчанию)
        balance_beginning = mt5_calculator.calculate_balance_at_date(
            target_date=target_date,
            deals=deals
            # end_of_day не указан - по умолчанию False (начало дня)
        )
        
        # Баланс на конец дня
        balance_end = mt5_calculator.calculate_balance_at_date(
            target_date=target_date,
            deals=deals,
            end_of_day=True
        )
        
        print(f"   • 🌅 Начало дня: {balance_beginning:.2f}")
        print(f"   • 🌆 Конец дня:  {balance_end:.2f}")
        print(f"   • 📊 Разница:    {balance_end - balance_beginning:+.2f}")
        
        if account_info:
            print(f"   • 📈 От текущего: {account_info.balance - balance_end:+.2f}")
        
        print()
    
    print("=" * 50)
    print("✅ Тест завершен!")
    
    print("\n💡 ИСПОЛЬЗОВАНИЕ:")
    print("• По умолчанию: calculate_balance_at_date(date, deals)")
    print("• Начало дня:   calculate_balance_at_date(date, deals, end_of_day=False)")
    print("• Конец дня:    calculate_balance_at_date(date, deals, end_of_day=True)")


if __name__ == "__main__":
    try:
        main_test()
    except KeyboardInterrupt:
        print("\n👋 Тест прерван")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
