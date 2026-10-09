# Confluence import

Масовий знімок спейсу або гілки сторінок у Markdown. REST, не MCP.

Конвертація з `body.export_view`: прибраний TOC, панелі стають цитатами, таблиці з абзацами в клітинках не розвалюються, внутрішні посилання на вивантажені сторінки стають відносними. Логіка обходу дерева взята з імпорту Confluence у Folio (`child/page`, сторінка з дітьми — `index.md`).

```bash
cd tools/confluence-import
npm install
node import.mjs --url 'https://host/wiki/spaces/KEY/overview'
node import.mjs --url 'https://host/wiki/spaces/KEY/pages/123/Title' --only-page
```

Токен: `workspace/keys/confluence`. Результат: `context/docs/confluence/<назва-спейсу>/`.

Адресу спейсу або кореневої сторінки скрипт сам не вигадує. Без `--url` він зупиняється.
