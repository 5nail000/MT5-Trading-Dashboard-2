# calculate_balance_at_date Function

Documentation for the balance calculation function at a specified date from the `MT5Calculator` module.

## Description

The `calculate_balance_at_date` function calculates the trading account balance at a specified date, taking into account all deals from the trading history.

## Features

- ✅ **Initial balance = 0** (by default)
- ✅ **Beginning/end of day option** (`end_of_day` parameter)
- ✅ **Exact time calculation** (`use_exact_time` parameter) 🆕
- ✅ **Proper timezone handling** (`LOCAL_TIMESHIFT = 3`)
- ✅ **Correct calculation logic** considering all deal types

## Function Parameters

```python
def calculate_balance_at_date(
    target_date: datetime,      # Date and time for balance calculation
    deals: List,                 # List of all deals from history
    initial_balance: float = None,  # Initial balance (0 by default)
    end_of_day: bool = False,   # True = end of day, False = beginning of day
    use_exact_time: bool = False # True = exact time from target_date 🆕
) -> float:
```

## Usage

### Basic Modes (as before)

```python
# Default - beginning of day (00:00:00)
balance = mt5_calculator.calculate_balance_at_date(
    target_date=datetime(2025, 10, 10),
    deals=deals
)

# End of day (23:59:59)
balance = mt5_calculator.calculate_balance_at_date(
    target_date=datetime(2025, 10, 10),
    deals=deals,
    end_of_day=True
)
```

### 🆕 Exact Time Calculation

```python
# Balance at exact time (14:30:25)
balance = mt5_calculator.calculate_balance_at_date(
    target_date=datetime(2025, 10, 10, 14, 30, 25),
    deals=deals,
    use_exact_time=True
)

# Balance at another exact time (18:45:00)
balance = mt5_calculator.calculate_balance_at_date(
    target_date=datetime(2025, 10, 10, 18, 45, 0),
    deals=deals,
    use_exact_time=True
)
```

### Combined Usage

```python
# Parameters can be combined
balance = mt5_calculator.calculate_balance_at_date(
    target_date=datetime(2025, 10, 10, 12, 0, 0),
    deals=deals,
    initial_balance=1000.0,  # Initial balance
    use_exact_time=True      # Exact time
)
```

## Running Tests

### Main Test
```bash
python tests/balance_calculation/test_balance_function.py
```

### 🆕 Exact Time Test
```bash
python test_balance_time.py
```

### Exact Time Test (from tests folder)
```bash
python tests/balance_calculation/test_exact_time.py
```

## Test Results

The test checks:
- **October 10, 2025** - working day with trading
- **September 27, 2025** - Saturday (day off)
- **September 28, 2025** - Sunday (day off)

Expected results:
- Saturday and Sunday should have the same balance (no trading)
- The difference between beginning and end of day shows profit/loss for the day

## Logic

1. **Timezone**: Local time is converted to UTC considering `LOCAL_TIMESHIFT`
2. **Deal types**:
   - `type == 2`: Balance changes (deposits/withdrawals)
   - Others: Trading deals (profit + commission + swap)
3. **Calculation**: Initial balance + all deals up to the specified date
4. **Time modes**:
   - `use_exact_time=False`: Uses beginning/end of day
   - `use_exact_time=True`: Uses exact time from `target_date`

## 🎯 Practical Usage Examples

### Trading Day Analysis
```python
# Balance at the beginning of trading day
morning_balance = mt5_calculator.calculate_balance_at_date(
    target_date=datetime(2025, 10, 15, 9, 0, 0),
    deals=deals,
    use_exact_time=True
)

# Balance at midday
midday_balance = mt5_calculator.calculate_balance_at_date(
    target_date=datetime(2025, 10, 15, 12, 30, 0),
    deals=deals,
    use_exact_time=True
)

# Balance at the end of trading day
evening_balance = mt5_calculator.calculate_balance_at_date(
    target_date=datetime(2025, 10, 15, 18, 0, 0),
    deals=deals,
    use_exact_time=True
)

print(f"Morning balance: {morning_balance:.2f}")
print(f"Midday balance: {midday_balance:.2f}")
print(f"Evening balance: {evening_balance:.2f}")
print(f"Profit for the day: {evening_balance - morning_balance:.2f}")
```

### Tracking Specific Deals
```python
# Balance before a specific deal
before_deal = mt5_calculator.calculate_balance_at_date(
    target_date=datetime(2025, 10, 15, 14, 25, 30),
    deals=deals,
    use_exact_time=True
)

# Balance after a specific deal
after_deal = mt5_calculator.calculate_balance_at_date(
    target_date=datetime(2025, 10, 15, 14, 26, 15),
    deals=deals,
    use_exact_time=True
)

print(f"Balance before deal: {before_deal:.2f}")
print(f"Balance after deal: {after_deal:.2f}")
print(f"Deal impact: {after_deal - before_deal:.2f}")
```

### Comparing Different Periods
```python
# Balance at the beginning of week
week_start = mt5_calculator.calculate_balance_at_date(
    target_date=datetime(2025, 10, 13, 0, 0, 0),  # Monday
    deals=deals,
    use_exact_time=True
)

# Balance at the end of week
week_end = mt5_calculator.calculate_balance_at_date(
    target_date=datetime(2025, 10, 17, 23, 59, 59),  # Friday
    deals=deals,
    use_exact_time=True
)

print(f"Balance at week start: {week_start:.2f}")
print(f"Balance at week end: {week_end:.2f}")
print(f"Profit for the week: {week_end - week_start:.2f}")
```

## Output Examples

### Main Test
```
🧮 TEST OF calculate_balance_at_date FUNCTION
==================================================
🔄 Fetching data...
✅ Deals received: 3004
🏦 Account: 25235504
📈 Current MT5 balance: 11968.11

📅 October 10 (2025-10-10):
   • 🌅 Beginning of day: 10938.49
   • 🌆 End of day:  10491.50
   • 📊 Difference:    -446.99
   • 📈 From current: +1476.61

📅 Saturday (2025-09-27):
   • 🌅 Beginning of day: 6833.09
   • 🌆 End of day:  6833.09
   • 📊 Difference:    +0.00
   • 📈 From current: +5135.02

📅 Sunday (2025-09-28):
   • 🌅 Beginning of day: 6833.09
   • 🌆 End of day:  6833.09
   • 📊 Difference:    +0.00
   • 📈 From current: +5135.02

==================================================
✅ Test completed!
```

### 🆕 Exact Time Test
```
🧪 Testing balance calculation by exact time
============================================================
📊 Fetching data from MT5...
✅ Received 3004 deals
📅 Testing on date: 15.10.2025

🌅 Balance at beginning of day (00:00:00): 10938.49
🌙 Balance at end of day (23:59:59): 10491.50
⏰ Balance at exact time (12:00:00): 10715.25
⏰ Balance at exact time (18:30:45): 10589.30

📈 Analysis:
   Difference beginning → end of day: -446.99
   Difference 12:00 → 18:30: -125.95
✅ Logic is correct: beginning ≤ exact time ≤ end

============================================================
🎯 Test with custom time
Enter hour (0-23): 14
Enter minutes (0-59): 30
Enter seconds (0-59): 15
💰 Balance at 14:30:15: 10652.80
```

### Command Line Tool
For quick balance calculation at a specific date from command line:

```bash
# Calculate balance at beginning of day
python tests/balance_calculation/balance_by_date.py --date 2025-09-27

# Calculate balance at end of day
python tests/balance_calculation/balance_by_date.py --date 2025-09-27 --end-of-day

# Calculate with custom initial balance
python tests/balance_calculation/balance_by_date.py --date 2025-10-10 --initial-balance 1000

# Detailed output with deal information
python tests/balance_calculation/balance_by_date.py --date 2025-09-30 --verbose
```

**Supported date formats:**
- `2025-09-27` (ISO format)
- `27-09-2025` (European format)
- `27/09/2025` (Slash format)
- `27.09.2025` (Dot format)

## Output Examples

```
🧮 BALANCE CALCULATION AT DATE
==================================================
📅 Target date: 27.09.2025
🕐 Mode: Beginning of day

🔄 Fetching data...
✅ Deals received: 3004
🏦 Account: 25235504
📈 Current MT5 balance: 11968.11

🧮 RESULT:
------------------------------
📊 Balance: 6833.09
📈 From current: +5135.02

==================================================
✅ Calculation completed!
```

