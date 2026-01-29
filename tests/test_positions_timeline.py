"""
Тест функции get_positions_timeline

python tests/test_positions_timeline.py

"""

import sys
import os
from datetime import datetime

# Добавляем корневую папку проекта в путь
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.mt5.mt5_client import mt5_data_provider, mt5_calculator


def main_test():
    """Основной тест функции get_positions_timeline"""
    
    print("🧮 ТЕСТ ФУНКЦИИ get_positions_timeline")
    print("=" * 70)
    
    # Параметры теста
    from_date = datetime(2025, 11, 9)
    to_date = datetime(2025, 11, 16)
    magics = [444300, 444152, 444010, 444310, 444230]
    magics = [444700]
    
    print(f"📅 Период: {from_date.strftime('%d.%m.%Y')} - {to_date.strftime('%d.%m.%Y')}")
    print(f"🔢 Мэджики: {magics}")
    print()
    
    # Получаем данные (нужно получить данные с начала истории для корректного восстановления позиций)
    print("🔄 Получение данных...")
    deals, account_info = mt5_data_provider.get_history(
        from_date=datetime(2020, 1, 1),  # С начала истории
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
    print("=" * 70)
    print()
    
    # Вызываем функцию
    print("🔍 Вызов функции get_positions_timeline...")
    timeline = mt5_calculator.get_positions_timeline(
        from_date=from_date,
        to_date=to_date,
        magics=magics,
        deals=deals
    )
    
    if not timeline:
        print("⚠️  Timeline пуст - нет позиций в указанном периоде")
        return
    
    print(f"✅ Получено промежутков: {len(timeline)}")
    print()
    
    # Выводим результаты
    print("📊 РЕЗУЛЬТАТЫ:")
    print("=" * 70)
    
    for i, period in enumerate(timeline, 1):
        time_in = period['time_in']
        time_out = period['time_out']
        balance = period['balance']
        balance_change = period.get('balance_change', 0.0)
        aggregated_positions = period.get('aggregated_positions', [])
        total_margin = period.get('total_margin', 0.0)
        total_worst_equity = period.get('total_worst_equity', 0.0)
        pool_changes = period.get('pool_changes', 'N/A')
        
        print(f"\n🔹 Промежуток #{i}:")
        print(f"   ⏰ Время IN:  {time_in.strftime('%d.%m.%Y %H:%M:%S')}")
        print(f"   ⏰ Время OUT: {time_out.strftime('%d.%m.%Y %H:%M:%S') if time_out else 'N/A'}")
        print(f"   💰 Баланс:    {balance:.2f} (изменение: {balance_change:+.2f})")
        print(f"   📊 Маржа:     {total_margin:.2f}")
        print(f"   📉 Наихудшее эквити: {total_worst_equity:.2f}")
        print(f"   🔄 Изменения в пуле: {pool_changes}")
        print(f"   📈 Агрегированных позиций: {len(aggregated_positions)}")
        
        if aggregated_positions:
            print(f"   📋 Детали агрегированных позиций:")
            for j, pos in enumerate(aggregated_positions, 1):
                high_str = f"{pos.get('high', 0):.5f}" if pos.get('high') else 'N/A'
                low_str = f"{pos.get('low', 0):.5f}" if pos.get('low') else 'N/A'
                print(f"      {j}. {pos['symbol']} | {pos['direction']:4s} | "
                      f"Объем: {pos['total_volume']:.2f} | Цена входа: {pos['average_price']:.5f}")
                print(f"         HIGH: {high_str}, LOW: {low_str}")
        else:
            print(f"   📋 Нет открытых позиций")
    
    print()
    print("=" * 70)
    
    # Статистика
    print("\n📈 СТАТИСТИКА:")
    print("-" * 70)
    total_periods = len(timeline)
    periods_with_positions = sum(1 for p in timeline if len(p.get('aggregated_positions', [])) > 0)
    periods_without_positions = total_periods - periods_with_positions
    
    print(f"Всего промежутков: {total_periods}")
    print(f"С позициями: {periods_with_positions}")
    print(f"Без позиций: {periods_without_positions}")
    
    # Уникальные символы
    all_symbols = set()
    for period in timeline:
        for pos in period.get('aggregated_positions', []):
            all_symbols.add(pos['symbol'])
    
    if all_symbols:
        print(f"\nУникальные символы: {sorted(all_symbols)}")
    
    # Общий объем позиций по символам
    symbol_volumes = {}
    for period in timeline:
        for pos in period.get('aggregated_positions', []):
            symbol = pos['symbol']
            if symbol not in symbol_volumes:
                symbol_volumes[symbol] = {'buy': 0.0, 'sell': 0.0}
            direction = pos['direction'].lower()
            if direction in symbol_volumes[symbol]:
                symbol_volumes[symbol][direction] += pos['total_volume']
    
    if symbol_volumes:
        print(f"\nОбщие объемы по символам:")
        for symbol, volumes in sorted(symbol_volumes.items()):
            print(f"  {symbol}: Buy={volumes['buy']:.2f}, Sell={volumes['sell']:.2f}")
    
    # Статистика по марже и эквити
    total_margins = [p.get('total_margin', 0.0) for p in timeline]
    total_equities = [p.get('total_worst_equity', 0.0) for p in timeline]
    balance_changes = [p.get('balance_change', 0.0) for p in timeline]
    
    if total_margins:
        print(f"\nМаржа:")
        print(f"  Максимальная: {max(total_margins):.2f}")
        print(f"  Минимальная: {min(total_margins):.2f}")
        print(f"  Средняя: {sum(total_margins) / len(total_margins):.2f}")
    
    if total_equities:
        print(f"\nНаихудшее эквити:")
        print(f"  Максимальное (лучший случай): {max(total_equities):.2f}")
        print(f"  Минимальное (худший случай): {min(total_equities):.2f}")
        print(f"  Среднее: {sum(total_equities) / len(total_equities):.2f}")
    
    if balance_changes:
        total_balance_change = sum(balance_changes)
        print(f"\nИзменения баланса:")
        print(f"  Общее изменение: {total_balance_change:+.2f}")
        print(f"  Положительных изменений: {sum(1 for c in balance_changes if c > 0)}")
        print(f"  Отрицательных изменений: {sum(1 for c in balance_changes if c < 0)}")
    
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

