# MT5 Dashboard (Next.js)

Пример реализации нового дашборда на Next.js + React + Tailwind CSS с ночной палитрой.

## Установка и запуск

```bash
cd dashboard-next
npm install
npm run dev
```

Откройте http://localhost:3000 в браузере.

## Структура

```
dashboard-next/
├── src/
│   ├── app/
│   │   ├── globals.css      # Глобальные стили, ночная палитра
│   │   ├── layout.tsx       # Root layout
│   │   └── page.tsx         # Главная страница
│   ├── components/
│   │   ├── TopBar.tsx           # Верхняя панель (account, period, sync)
│   │   ├── OpenPositionsBar.tsx # Полоска открытых позиций
│   │   ├── MainResults.tsx      # Горизонтальные бары результатов
│   │   ├── Filters.tsx          # Фильтры (вариант A)
│   │   ├── SidePanel.tsx        # Боковая панель действий
│   │   └── OpenPositionsModal.tsx # Модалка с гистограммой
│   └── data/
│       └── snapshot.ts      # Тестовые данные из sample_snapshot.json
├── tailwind.config.ts       # Конфиг Tailwind с ночной палитрой
├── package.json
└── README.md
```

## Функциональность

- **TopBar**: выбор аккаунта, пресеты периодов, статус синхронизации
- **OpenPositionsBar**: полоска floating P/L (-10%..+10%), кликабельная
- **MainResults**: горизонтальные бары результатов по группам/мэджикам
- **Filters (вариант A)**: ShowAll / HideAll / Configure с модальным диалогом
- **SidePanel**: кнопки для Labels, Groups, Deals, Balance Chart
- **OpenPositionsModal**: гистограмма по мэджикам при клике на полоску

## Данные

Данные загружаются из `src/data/snapshot.ts` (импорт из `design/sample_snapshot.json`).
