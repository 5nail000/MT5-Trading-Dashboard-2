# MT5 Trading Dashboard

Персональная торговая панель для MetaTrader 5 с бэкендом на FastAPI и фронтендом на Next.js.

## Возможности

- **Данные в реальном времени**: Подключение к терминалу MetaTrader 5
- **Мониторинг открытых позиций**: Отслеживание текущего плавающего P/L по магикам
- **Исторический анализ**: Анализ торговых результатов
- **Управление магиками**: Организация и описание торговых стратегий
- **Группы магиков**: Группировка для агрегированной статистики
- **Графики баланса/эквити**: Временная визуализация состояния счёта
- **История сделок**: Детальный просмотр закрытых позиций
- **Сравнение аккаунтов**: Сопоставление сделок между двумя аккаунтами по времени входа
- **Редактор чартов**: Массовое редактирование параметров советников в .chr файлах

## Архитектура

```
MT5_Trading_Dashboard/
├── src/                      # Python бэкенд
│   ├── api/                  # FastAPI приложение
│   │   └── main.py          # REST API эндпоинты
│   ├── config/              # Конфигурация
│   │   └── settings.py      # Настройки из .env
│   ├── services/            # Слой бизнес-логики
│   │   ├── account_service.py   # Управление аккаунтами
│   │   ├── sync_service.py      # Операции синхронизации
│   │   ├── group_service.py     # Управление группами
│   │   └── chart_service.py     # Редактирование .chr файлов
│   ├── db_sa/               # SQLAlchemy ORM
│   │   ├── models.py        # Модели базы данных
│   │   ├── session.py       # Управление сессиями
│   │   └── init_db.py       # Инициализация БД
│   ├── mt5/                 # Интеграция с MT5
│   │   ├── mt5_client.py    # Подключение и расчёты
│   │   └── tick_data.py     # Работа с тиками
│   ├── sync/                # Синхронизация данных
│   │   ├── mt5_sync.py      # Синхронизация сделок
│   │   └── orchestrator.py  # Оркестрация
│   ├── analytics/           # Аналитика
│   │   └── drawdown.py      # Расчёт просадки
│   ├── readmodels/          # Обработчики запросов (CQRS)
│   │   └── dashboard_queries.py
│   ├── security/            # Безопасность
│   │   ├── crypto.py        # Шифрование паролей (Fernet)
│   │   └── ip_filter.py     # IP whitelist middleware
│   └── utils/               # Утилиты
│       ├── helpers.py       # Вспомогательные функции
│       ├── logger.py        # Настройка логирования
│       └── timezone.py      # Работа с часовыми поясами
├── dashboard-next/          # Next.js фронтенд
│   ├── src/
│   │   ├── app/            # Страницы App Router
│   │   ├── components/     # React компоненты
│   │   ├── lib/            # API клиент
│   │   └── types/          # TypeScript типы
│   └── package.json
├── tests/                   # Тесты
├── scripts/                 # Скрипты
├── requirements.txt         # Python зависимости
└── .env.example            # Шаблон конфигурации
```

## Установка

### Требования

- Python 3.10+
- Node.js 18+
- Терминал MetaTrader 5

### Настройка бэкенда

```bash
# Создать виртуальное окружение
python -m venv venv

# Активировать (Windows)
venv\Scripts\activate

# Установить зависимости
pip install -r requirements.txt

# Скопировать и настроить конфигурацию
cp .env.example .env
# Отредактируйте .env
```

### Настройка фронтенда

```bash
cd dashboard-next

# Установить зависимости
npm install
```

## Использование

### Запуск бэкенда

```bash
# Из корня проекта
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

### Запуск фронтенда

```bash
cd dashboard-next
npm run dev
```

Откройте http://localhost:3000 в браузере.

## Конфигурация

Отредактируйте файл `.env`:

```env
# База данных
SQLALCHEMY_DATABASE_URL=sqlite:///./mt5_dashboard.db

# Торговля
LOCAL_TIMESHIFT=3

# Безопасность
MT5_CRED_KEY=<ваш-fernet-ключ>
ALLOWED_ORIGINS=http://localhost:3000
IP_WHITELIST=
```

Генерация Fernet ключа:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

## API эндпоинты

| Метод | Эндпоинт | Описание |
|-------|----------|----------|
| GET | /health | Проверка здоровья |
| GET | /accounts | Список аккаунтов |
| GET | /terminal/active | Активный аккаунт терминала |
| GET | /magics | Список магиков |
| GET | /groups | Список групп |
| GET | /open-positions | Открытые позиции |
| GET | /aggregates | Агрегаты за период |
| GET | /deals | История сделок |
| GET | /compare-deals | Сравнение сделок между аккаунтами |
| POST | /sync/open | Синхронизация позиций |
| POST | /sync/history | Синхронизация истории |
| GET | /charts/config | Конфигурация редактора чартов |
| PUT | /charts/config | Обновить путь к папке чартов |
| GET | /charts/folders | Список папок профилей |
| GET | /charts/sections | Список секций редактирования |
| POST | /charts/validate | Валидация секции |
| POST | /charts/write/{id} | Записать изменения в файл |

## Ключевые классы

- `MT5Connection`: Управление подключением к MT5 (singleton)
- `MT5DataProvider`: Получение данных из MT5
- `MT5Calculator`: Торговые расчёты (баланс, эквити, маржа)
- `SessionLocal`: Сессия SQLAlchemy

## Разработка

```bash
# Запуск тестов
pytest

# Форматирование
black src/

# Проверка типов
mypy src/
```

## Лицензия

MIT License
