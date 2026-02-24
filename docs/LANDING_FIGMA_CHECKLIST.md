# Чеклист: лендинг vs Figma

Дизайн: [Figma — Frame 1](https://www.figma.com/design/3XG5jV8f08BdRMWDhLUm1O/Untitled?node-id=5-365)

## Как запустить и проверить локально

1. Установить зависимости (если ещё не установлены):
   ```bash
   cd apps/web && npm install
   ```
2. Запустить dev-сервер:
   ```bash
   npm run dev
   ```
3. Открыть лендинг: **http://localhost:5173/landing** (или порт из вывода Vite).

---

## Список созданных/изменённых файлов

| Файл | Описание |
|------|----------|
| `apps/web/src/components/landing/Container.tsx` | Обёртка секций (max-width, отступы) |
| `apps/web/src/components/landing/SectionTitle.tsx` | Заголовок и подзаголовок секции |
| `apps/web/src/components/landing/Header.tsx` | Шапка, навигация, CTA-кнопки |
| `apps/web/src/components/landing/Hero.tsx` | Hero-блок с заголовком и плейсхолдером иллюстрации |
| `apps/web/src/components/landing/Features.tsx` | Секция «Возможности» (карточки) |
| `apps/web/src/components/landing/HowItWorks.tsx` | Секция «Как это работает» (шаги) |
| `apps/web/src/components/landing/Pricing.tsx` | Секция «Тарифы» (карточки планов) |
| `apps/web/src/components/landing/Testimonials.tsx` | Секция отзывов |
| `apps/web/src/components/landing/FAQ.tsx` | Секция FAQ (Accordion) |
| `apps/web/src/components/landing/CTA.tsx` | Блок призыва к действию |
| `apps/web/src/components/landing/Footer.tsx` | Подвал |
| `apps/web/src/components/landing/index.ts` | Реэкспорт компонентов |
| `apps/web/src/pages/Landing.tsx` | Страница лендинга |
| `apps/web/src/App.tsx` | Добавлен маршрут `/landing` |
| `apps/web/src/assets/landing/.gitkeep` | Папка для ассетов из Figma |

---

## Что сверить с Figma (после экспорта макета)

- [ ] **Шрифты** — размеры и начертания заголовков/текста (сейчас: Inter, размеры через Tailwind).
- [ ] **Цвета** — фоны секций, акценты, текст (сейчас: CSS-переменные проекта `--primary`, `--muted` и т.д.).
- [ ] **Отступы** — padding секций, gap между блоками (сейчас: py-16/20/24, gap-6/8).
- [ ] **Сетка** — количество колонок и брейкпоинты (сейчас: 1 / 2 / 4 колонки на 375 / 768 / 1024+).
- [ ] **Кнопки** — стили, радиус, размеры (сейчас: компонент `Button` из UI).
- [ ] **Карточки** — тени, радиус, отступы (сейчас: rounded-xl, border, shadow-sm/md).
- [ ] **Тексты** — все заголовки и параграфы один в один из Figma (сейчас — черновые; в коде есть TODO).
- [ ] **Логотип** — заменить текстовый «Service Analytics» на `src/assets/landing/logo.svg`.
- [ ] **Hero-иллюстрация** — заменить плейсхолдер на `src/assets/landing/hero-illustration.svg` (или .png).
- [ ] **Навигация** — пункты меню и якоря (#features, #how-it-works, #pricing, #faq).
- [ ] **Секции** — наличие/порядок: Hero, Features, How it works, Pricing, Testimonials, FAQ, CTA, Footer (при отличии в Figma — добавить/убрать/переименовать).

После экспорта ассетов из Figma положить файлы в `apps/web/src/assets/landing/` и заменить плейсхолдеры по TODO в компонентах.
