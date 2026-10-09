---
name: figma
description: >-
  Макети Figma: каталог у context/design/catalog.yaml і локальний знімок
  у context/design/<figma-name>/design.md (екрани і компоненти з параметрами).
  Спочатку локальні файли. Далі лише Figma MCP або REST API. Браузер не відкривати.
  Застосовувати при Figma, макеті, компоненті, варіанті, дизайні екрана, context/design.
---

# Figma

Локальні файли — джерело для відповіді. MCP або API не викликати, якщо знімок уже відповідає на питання.

Браузер для Figma не відкривати. Не клікати канву, не знімати скрін інтерфейсу Figma, не читати макет з DOM сторінки.

Сиру відповідь MCP чи API, згенерований код і повне дерево шарів у репозиторій не писати.

## Де що лежить

- `context/design/catalog.yaml` — які макети є: ім’я, slug, file key, URL, сторінки.
- `context/design/<figma-name>/design.md` — стисла agent-friendly версія одного макета: екрани і компоненти з параметрами.

`<figma-name>` — латиниця, kebab-case, коротко за назвою файлу у Figma. Оригінальну назву лишати в полі `name`.

## Порядок

1. Прочитати `catalog.yaml` і, якщо питання про конкретний макет, його `design.md`.
2. Цього досить — відповідати звідти. У відповіді дати шлях до локального файлу і URL Figma.
3. Каталогу немає, або користувач просить дізнатися, які макети є — зібрати каталог через MCP і записати `catalog.yaml`.
4. Треба працювати з макетом, а `design.md` немає або користувач просить оновити — зняти один макет і записати `design.md`: екрани і компоненти.
5. MCP не підключений або віддав помилку — взяти файл через REST API, не через браузер.
6. Немає ні MCP, ні токена API — так і сказати. Не вигадувати file key, екрани й токени. Браузер не є запасним шляхом. Як випустити токен — розділ Figma у `workspace.example/README.md`, не переказувати кроки з пам’яті.

Перед викликом MCP прочитати схеми tools поточного сервера Figma. Назви інструментів і параметри не вигадувати.

REST, якщо MCP недоступний: `GET https://api.figma.com/v1/files/{file_key}` і `GET https://api.figma.com/v1/files/{file_key}/nodes?ids=`. Токен — `workspace/keys/figma`, заголовок `X-Figma-Token`. Токен у відповідь і в логи не писати. File key брати з URL (`/design/{file_key}/`), не вгадувати.

Компоненти брати з того ж файлу. Словники `components` і `componentSets` дають ім’я, `node_id`, опис. У вузла `COMPONENT_SET` поле `componentPropertyDefinitions` — параметри. Окремо опубліковані: `GET /v1/files/{file_key}/components` і `GET /v1/files/{file_key}/component_sets`. Локальні компоненти на сторінці, яких немає в цих списках, теж записати.

Каталог збирати легким викликом: список файлів, сторінок, імен фреймів. Не тягнути design context усього файлу, щоб дізнатися назви.

Для `design.md` брати структуру й короткий опис екранів через MCP або REST, і вижимку компонентів. Повний design context — лише для одного фрейма або одного компонента, якщо без нього запис не зібрати. У файл класти вижимку, не відповідь цілком. Діти шарів компонента не розписувати.

## catalog.yaml

```yaml
updated: 2026-10-09
files:
  - name: Operator desktop
    slug: operator-desktop
    file_key: ""
    url: ""
    last_modified: ""
    local: context/design/operator-desktop
    pages:
      - name: Desktop
```

Один запис — один файл Figma. Поле `local` — тека знімка. Немає файлів у Figma — написати порожній `files: []` і сказати про це.

## design.md

```markdown
# Operator desktop

- url:
- file_key:
- slug: operator-desktop
- snapshot: 2026-10-09
- figma_last_modified:

## Екрани

### Inbox
- node_id:
- що на екрані:
- стани:
- примітка:

## Компоненти

### Button
- node_id:
- тип: component set
- опис:
- параметри:
  - Variant: VARIANT, default Primary, options Primary, Secondary
  - Label: TEXT, default Button
  - Has Icon: BOOLEAN, default true
  - Icon: INSTANCE_SWAP, default node 1:5

### Icon / close
- node_id:
- тип: component
- опис:
- параметри: немає

## Не знято

Токени і фрейми, які цього разу не читали.
```

Параметр писати без суфікса `#nodeId` в імені. Тип лишати як у Figma: `VARIANT`, `TEXT`, `BOOLEAN`, `INSTANCE_SWAP`. Для `VARIANT` перелічити `variantOptions` і `defaultValue`. Компонентів немає — у секції один рядок, що їх немає, не вигадувати набір.

Оновлювати секцію екрана або компонента, який змінили. Решту файлу не переписувати з MCP заново.

`design-handoff` і `design-critique` теж спочатку читають цей знімок.

Дизайн-система — не цей файл. Її пишуть у `context/design/<slug>/DESIGN.md` за скілом `design-md`.
