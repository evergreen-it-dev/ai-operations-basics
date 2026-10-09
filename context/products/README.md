# Продукти

Код і документація продуктів. Одна тека — один продукт.

`context/products/<product-name>/` — git submodule: сюди клонується репозиторій продукту. Цей репозиторій зберігає лише коміт, на який вказує submodule.

```bash
git submodule add <url-репозиторію> context/products/<product-name>
```

Ім’я теки — латиниця, kebab-case.

Після клону operations-approach:

```bash
git submodule update --init --recursive
```

Факти про команду й процеси — у `context/company/`. Політики — у `context/onboarding/`.
