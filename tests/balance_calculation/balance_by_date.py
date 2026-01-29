"""
Командный инструмент для расчета баланса на указанную дату
Запуск: python balance_by_date.py --date 2025-11-10
        python tests/balance_calculation/balance_by_date.py --date 2025-11-10
"""

import sys
import os
import argparse
from datetime import datetime, timedelta

# Добавляем корневую папку проекта в путь
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.mt5.mt5_client import mt5_data_provider, mt5_calculator


def parse_date(date_str):
    """Парсинг даты из строки"""
    try:
        # Поддерживаем разные форматы
        formats = [
            "%Y-%m-%d",    # 2025-09-27
            "%d-%m-%Y",    # 27-09-2025
            "%d/%m/%Y",    # 27/09/2025
            "%d.%m.%Y",    # 27.09.2025
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        raise ValueError(f"Неизвестный формат даты: {date_str}")
        
    except Exception as e:
        print(f"❌ Ошибка парсинга даты: {e}")
        print("📅 Поддерживаемые форматы:")
        print("   • 2025-09-27")
        print("   • 27-09-2025") 
        print("   • 27/09/2025")
        print("   • 27.09.2025")
        sys.exit(1)


def main():
    """Главная функция"""
    
    parser = argparse.ArgumentParser(
        description="Расчет баланса на указанную дату",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  python balance_by_date.py --date 2025-09-27
  python balance_by_date.py --date 27-09-2025 --end-of-day
  python balance_by_date.py --date 2025-10-10 --initial-balance 1000
  python balance_by_date.py --date 2025-09-30 --verbose
        """
    )
    
    parser.add_argument(
        '--date', '-d',
        required=True,
        help='Дата для расчета баланса (форматы: 2025-09-27, 27-09-2025, 27/09/2025, 27.09.2025)'
    )
    
    parser.add_argument(
        '--end-of-day',
        action='store_true',
        help='Рассчитать баланс на конец дня (по умолчанию - начало дня)'
    )
    
    parser.add_argument(
        '--initial-balance',
        type=float,
        default=None,
        help='Начальный баланс (по умолчанию 0)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Подробный вывод'
    )
    
    args = parser.parse_args()
    
    print("🧮 РАСЧЕТ БАЛАНСА НА ДАТУ")
    print("=" * 50)
    
    # Парсим дату
    target_date = parse_date(args.date)
    
    print(f"📅 Целевая дата: {target_date.strftime('%d.%m.%Y')}")
    print(f"🕐 Режим: {'Конец дня' if args.end_of_day else 'Начало дня'}")
    if args.initial_balance is not None:
        print(f"💰 Начальный баланс: {args.initial_balance:.2f}")
    print()
    
    # Получаем данные - используем расширенный диапазон для корректного расчета
    print("🔄 Получение данных...")
    
    # Расширяем диапазон для корректного расчета баланса
    # Нужно получить данные с самого начала для правильного расчета
    from_date = datetime(2020, 1, 1)  # Начало истории
    to_date = datetime.now() + timedelta(days=1)  # До завтра
    
    deals, account_info = mt5_data_provider.get_history(
        from_date=from_date,
        to_date=to_date
    )
    
    if deals is None:
        print("❌ Не удалось получить данные")
        return
    
    print(f"✅ Получено сделок: {len(deals)}")
    print(f"📅 Диапазон данных: {from_date.strftime('%d.%m.%Y')} - {to_date.strftime('%d.%m.%Y')}")
    
    if account_info:
        print(f"🏦 Аккаунт: {account_info.login}")
        print(f"📈 Текущий баланс MT5: {account_info.balance:.2f}")
    
    print()
    
    # Рассчитываем баланс
    print("🧮 РЕЗУЛЬТАТ:")
    print("-" * 30)
    
    balance = mt5_calculator.calculate_balance_at_date(
        target_date=target_date,
        deals=deals,
        initial_balance=args.initial_balance,
        end_of_day=args.end_of_day
    )
    
    print(f"📊 Баланс: {balance:.2f}")
    
    if account_info:
        difference = account_info.balance - balance
        print(f"📈 От текущего: {difference:+.2f}")
    
    # Подробный вывод
    if args.verbose:
        print()
        print("📋 ПОДРОБНАЯ ИНФОРМАЦИЯ:")
        print("-" * 40)
        
        # Анализируем сделки в этот день
        sorted_deals = sorted(deals, key=lambda x: x.time)
        
        deals_on_date = []
        for deal in sorted_deals:
            deal_time = datetime.fromtimestamp(deal.time)
            if deal_time.date() == target_date.date():
                deals_on_date.append(deal)
        
        print(f"Сделок в этот день: {len(deals_on_date)}")
        
        if deals_on_date:
            print("\nСделки:")
            total_profit = 0
            total_commission = 0
            total_swap = 0
            
            for deal in deals_on_date:
                deal_time = datetime.fromtimestamp(deal.time)
                print(f"  {deal_time.strftime('%H:%M:%S')} | Тип: {deal.type} | Прибыль: {deal.profit:.2f}")
                total_profit += deal.profit
                total_commission += deal.commission
                total_swap += deal.swap
            
            print(f"\nИтого за день:")
            print(f"  Прибыль: {total_profit:.2f}")
            print(f"  Комиссия: {total_commission:.2f}")
            print(f"  Своп: {total_swap:.2f}")
    
    print()
    print("=" * 50)
    print("✅ Расчет завершен!")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Расчет прерван")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
