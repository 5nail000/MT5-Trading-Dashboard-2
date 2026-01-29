# 🕐 Шпаргалка: Расчет баланса по точному времени

## 🚀 Быстрый старт

```python
from datetime import datetime
from src.mt5.mt5_client import mt5_calculator, mt5_data_provider

# Получить данные
deals, _ = mt5_data_provider.get_history()

# Баланс на точное время
balance = mt5_calculator.calculate_balance_at_date(
    target_date=datetime(2025, 10, 15, 14, 30, 25),  # 15.10.2025 14:30:25
    deals=deals,
    use_exact_time=True
)
```

## 📋 Все режимы работы

### 1. Начало дня (00:00:00)
```python
balance = mt5_calculator.calculate_balance_at_date(
    target_date=datetime(2025, 10, 15),
    deals=deals
)
```

### 2. Конец дня (23:59:59)
```python
balance = mt5_calculator.calculate_balance_at_date(
    target_date=datetime(2025, 10, 15),
    deals=deals,
    end_of_day=True
)
```

### 3. Точное время 🆕
```python
balance = mt5_calculator.calculate_balance_at_date(
    target_date=datetime(2025, 10, 15, 14, 30, 25),
    deals=deals,
    use_exact_time=True
)
```

## 🎯 Практические примеры

### Анализ торгового дня
```python
# Утром
morning = mt5_calculator.calculate_balance_at_date(
    datetime(2025, 10, 15, 9, 0, 0), deals, use_exact_time=True
)

# В обед
midday = mt5_calculator.calculate_balance_at_date(
    datetime(2025, 10, 15, 12, 30, 0), deals, use_exact_time=True
)

# Вечером
evening = mt5_calculator.calculate_balance_at_date(
    datetime(2025, 10, 15, 18, 0, 0), deals, use_exact_time=True
)

print(f"Прибыль за день: {evening - morning:.2f}")
```

### Отслеживание сделок
```python
# До сделки
before = mt5_calculator.calculate_balance_at_date(
    datetime(2025, 10, 15, 14, 25, 30), deals, use_exact_time=True
)

# После сделки
after = mt5_calculator.calculate_balance_at_date(
    datetime(2025, 10, 15, 14, 26, 15), deals, use_exact_time=True
)

print(f"Влияние сделки: {after - before:.2f}")
```

## ⚡ Быстрые команды

```python
# Создать datetime с точным временем
dt = datetime(2025, 10, 15, 14, 30, 25)  # год, месяц, день, час, минута, секунда

# Или из строки
from datetime import datetime
dt = datetime.strptime("2025-10-15 14:30:25", "%Y-%m-%d %H:%M:%S")

# Рассчитать баланс
balance = mt5_calculator.calculate_balance_at_date(dt, deals, use_exact_time=True)
```

## 🔧 Параметры функции

| Параметр | Тип | По умолчанию | Описание |
|----------|-----|--------------|----------|
| `target_date` | datetime | - | Дата и время для расчета |
| `deals` | List | - | Список сделок из MT5 |
| `initial_balance` | float | None | Начальный баланс (0 если None) |
| `end_of_day` | bool | False | True = конец дня, False = начало дня |
| `use_exact_time` | bool | False | **🆕** True = точное время из target_date |

## 📊 Логика работы

1. **Время**: Местное время → UTC (с учетом LOCAL_TIMESHIFT)
2. **Сделки**: Сортируются по времени
3. **Расчет**: Начальный баланс + все сделки до указанного времени
4. **Типы сделок**:
   - `type == 2`: Изменения баланса (депозиты/снятия)
   - Остальные: Торговые сделки (прибыль + комиссия + своп)

## 🧪 Тестирование

```bash
# Основной тест
python tests/balance_calculation/test_balance_function.py

# Тест точного времени
python test_balance_time.py

# Интерактивный тест
python tests/balance_calculation/test_exact_time.py
```

## 💡 Советы

- ✅ **Всегда используйте `use_exact_time=True`** для точного времени
- ✅ **Проверяйте логику**: начало дня ≤ точное время ≤ конец дня
- ✅ **Используйте datetime** вместо строк для времени
- ✅ **Тестируйте** на реальных данных перед продакшеном
