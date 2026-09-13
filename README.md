# Allika Studio — сайт

Статический сайт (HTML/CSS/JS, без сборки и зависимостей) — готов к публикации
на GitHub Pages.

## Структура

```
index.html                        — главная
projects/index.html               — список проектов
projects/*/index.html             — 6 карточек-кейсов
explorations/index.html           — Benzina: Fuel Prices & Map
legal/terms-of-use/               — Terms of Use (сайта)
legal/privacy-policy/             — Privacy Policy (сайта)
benzina/terms-of-use/             — Terms & Conditions приложения Benzina
benzina/privacy-policy/           — Privacy Policy приложения Benzina
                                    (текст тянется из gist, см. ниже)
404.html                          — страница «не найдено»
assets/style.css                  — все стили
assets/main.js                    — меню, аккордеон, скролл-анимации, часы,
                                     hover-видео, лайтбокс видео по двойному клику
assets/legal.js                   — подтягивает юр. тексты Benzina из gist
assets/img/                       — изображения и постеры (favicon-master.png —
                                     исходник 512×512 для пересборки иконки)
assets/video/                     — видео проектов
.nojekyll                         — чтобы GitHub Pages не трогал файлы через Jekyll
```

## Перед публикацией — осталось вручную

1. **Почта.** Во всех страницах стоит заглушка `hello@allikastudio.com`
   (футер + юридические страницы сайта). Заменить на настоящий адрес:
   ```
   grep -rl "hello@allikastudio.com" . | xargs sed -i '' 's/hello@allikastudio.com/НОВАЯ@ПОЧТА/g'
   ```
2. **Ссылка на App Store.** В `explorations/index.html` кнопка «Download on the
   App Store» ведёт на общий `apps.apple.com` — заменить на прямую ссылку,
   когда приложение опубликуется.

## Юридические страницы: две разные пары

| | про что | адрес |
|---|---|---|
| `legal/privacy-policy/`, `legal/terms-of-use/` | сам сайт allikastudio.com | — |
| `benzina/privacy-policy/`, `benzina/terms-of-use/` | приложение Benzina | для App Store Connect |

В App Store Connect в поле **Privacy Policy URL** указывается
`https://allikastudio.com/benzina/privacy-policy/`.

Тексты для страниц Benzina берутся из gist
`gist.github.com/redkiborg/7fb3761e57dd6a2763307f7307ef5b06` (файл `changelogIOS`,
ключи `legal.privacyPolicy` и `legal.termsOfService`). Работает это так:

* в HTML **вшита статическая копия** текста — страница читается без JavaScript
  и без интернета (это важно для проверки Apple);
* `assets/legal.js` при открытии страницы дочитывает gist и подменяет текст,
  так что правки в gist появляются на сайте сами, без перезаливки сайта;
* если gist недоступен или ответ пустой — остаётся вшитая копия.

Раз в какое-то время статическую копию стоит освежить, чтобы она не отставала
от gist. Это делает скрипт `tools/refresh-benzina-legal.py` — запустить
`python3 tools/refresh-benzina-legal.py` из корня сайта.

## Как выложить на GitHub Pages

1. Создай репозиторий на GitHub (например `allikastudio-site`).
2. Залей туда все файлы из этой папки:
   ```
   git init
   git add .
   git commit -m "Site"
   git branch -M main
   git remote add origin https://github.com/<твой-логин>/allikastudio-site.git
   git push -u origin main
   ```
   (или через веб-интерфейс: «Add file → Upload files»).
3. В репозитории: Settings → Pages → Source → ветка `main`, папка `/ (root)` → Save.
4. Через минуту-две сайт появится по адресу
   `https://<твой-логин>.github.io/allikastudio-site/`.
5. Свой домен (allikastudio.com) подключается там же, в Settings → Pages →
   Custom domain — в DNS-настройках домена нужно добавить CNAME-запись на
   `<твой-логин>.github.io`.

## Шрифты

Оригинальные платные шрифты Framer заменены на бесплатные аналоги с Google Fonts:
Fraunces (крупный курсивный заголовок) и Inter + JetBrains Mono (текст/моно).
Меняются через `@import` и `--font-*` переменные в начале `assets/style.css`.
