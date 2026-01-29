#!/usr/bin/env python3
"""
Примеры использования функции расчета баланса по дате и времени
"""
import sys
import os

# Добавляем корневую папку проекта в путь
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from datetime import datetime, time
from src.mt5.mt5_client import mt5_calculator, mt5_data_provider

def test_balance_calculation():
    """Тестирование различных способов расчета баланса"""
    
    # Получаем данные
    deals, account_info = mt5_data_provider.get_history()
    if not deals:
        print("❌ Не удалось получить данные")
        return
    
    print("🧪 Тестирование расчета баланса по дате и времени")
    print("=" * 60)
    
    # Примеры дат
    test_date = datetime(2025, 10, 15)  # 15 октября 2025
    
    # 1. Баланс на начало дня (00:00:00)
    balance_start = mt5_calculator.calculate_balance_at_date(
        target_date=test_date,
        deals=deals,
        end_of_day=False,
        use_exact_time=False
    )
    print(f"📅 Баланс на начало дня {test_date.date()}: {balance_start:.2f}")
    
    # 2. Баланс на конец дня (23:59:59)
    balance_end = mt5_calculator.calculate_balance_at_date(
        target_date=test_date,
        deals=deals,
        end_of_day=True,
        use_exact_time=False
    )
    print(f"🌙 Баланс на конец дня {test_date.date()}: {balance_end:.2f}")
    
    # 3. Баланс на точное время (14:30:00)
    exact_time = datetime(2025, 10, 15, 14, 30, 0)
    balance_exact = mt5_calculator.calculate_balance_at_date(
        target_date=exact_time,
        deals=deals,
        use_exact_time=True
    )
    print(f"⏰ Баланс на {exact_time.strftime('%H:%M:%S')}: {balance_exact:.2f}")
    
    # 4. Баланс на другое точное время (18:45:30)
    exact_time2 = datetime(2025, 10, 15, 18, 45, 30)
    balance_exact2 = mt5_calculator.calculate_balance_at_date(
        target_date=exact_time2,
        deals=deals,
        use_exact_time=True
    )
    print(f"⏰ Баланс на {exact_time2.strftime('%H:%M:%S')}: {balance_exact2:.2f}")
    
    print("\n🎯 Разница в балансах:")
    print(f"   Начало дня → Конец дня: {balance_end - balance_start:.2f}")
    print(f"   14:30 → 18:45: {balance_exact2 - balance_exact:.2f}")

def calculate_balance_at_specific_time():
    """Функция для расчета баланса на конкретное время"""
    
    # Пример: баланс на 15 октября 2025 в 16:20:15
    target_datetime = datetime(2025, 10, 15, 16, 20, 15)
    
    deals, account_info = mt5_data_provider.get_history()
    if not deals:
        return None
    
    balance = mt5_calculator.calculate_balance_at_date(
        target_date=target_datetime,
        deals=deals,
        use_exact_time=True
    )
    
    print(f"💰 Баланс на {target_datetime.strftime('%d.%m.%Y %H:%M:%S')}: {balance:.2f}")
    return balance

if __name__ == "__main__":
    test_balance_calculation()
    print("\n" + "="*60)
    calculate_balance_at_specific_time()
