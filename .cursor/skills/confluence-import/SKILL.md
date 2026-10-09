---
name: confluence-import
description: >-
  Масовий імпорт Confluence у Markdown через REST, не через MCP. Запитує адресу
  спейсу або кореневої сторінки, якщо її немає в запиті. Пише дерево в
  context/docs/confluence/<назва-спейсу>/. Застосовувати на вигрузку Confluence,
  імпорт спейсу, confluence import, /confluence-import.
---

# Імпорт Confluence

Скрипт: `tools/confluence-import/import.mjs`. Обхід дерева і формат файлів узяті з імпорту Confluence у Folio: REST `child/page`, тіло `export_view`, сторінка з нащадками стає текою з `index.md`, лист — `назва.md`.

## Якщо адреси немає

Зупинись і запитай одну річ: URL спейсу або кореневої сторінки.

Підходить:

- `https://host/wiki/spaces/KEY/overview` — увесь спейс від домашньої сторінки
- `https://host/wiki/spaces/KEY/pages/123/Title` — ця сторінка і нащадки

Не вигадуй хост і ключ спейсу. Не викликай MCP Confluence.

## Ключ

Файл `workspace/keys/confluence` (шаблон `workspace.example/keys/confluence.example`).

- On-prem: лише `CONFLUENCE_TOKEN` (Bearer PAT).
- Cloud: `CONFLUENCE_EMAIL` і `CONFLUENCE_TOKEN` (API token, Basic).

Якщо файлу або токена немає — скажи шлях і зупинись. Не проси вставляти токен у чат.

## Запуск

З кореня репозиторію, один раз `npm install` у `tools/confluence-import`:

```bash
cd tools/confluence-import && npm install
node import.mjs --url '<URL від користувача>'
```

Лише одна сторінка, без дітей: додай `--only-page`.

## Куди лягають файли

`context/docs/confluence/<slug назви спейсу>/`

- імпорт усього спейсу: домашня сторінка — `index.md`, діти поруч або в теках
- імпорт гілки, яка не є домашньою: та сама тека спейсу, корінь гілки — `<slug>/index.md`

У frontmatter кожної сторінки: `title`, `confluenceId`, `sourceUrl`.

Вкладення до 15 МБ — у `_files/` поруч зі сторінкою. Більші пропускаються, сторінка все одно пишеться.

Після прогону скажи, скільки сторінок і який шлях. Вміст вікі в чат не копіюй.
