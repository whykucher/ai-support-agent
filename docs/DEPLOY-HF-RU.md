# Переезд на Hugging Face Spaces

Зачем: бесплатный Render даёт 0.1 CPU и 512 МБ, засыпает через 15 минут и
просыпается ~50 секунд. Для ссылки в отклике на Upwork это плохо — клиент
кликает и ждёт минуту. Hugging Face Spaces на бесплатном тарифе даёт **2 vCPU и
16 ГБ**, не требует карту и засыпает только после 48 часов простоя.

Тот же Dockerfile работает и там, и на Render — форк не нужен.

---

## Что нужно от тебя: один вход

### 1. Аккаунт

Если нет — https://huggingface.co/join. Бесплатно, карта не нужна.

### 2. Токен доступа

https://huggingface.co/settings/tokens → **Create new token** → тип **Write** →
имя любое, например `deploy`. Скопируй токен, он показывается один раз.

### 3. Вход в CLI

Открой PowerShell в папке проекта и выполни:

```powershell
cd "C:\Users\whykucher\Новая папка (4)\ai-support-agent"
.\.venv\Scripts\hf.exe auth login
```

Вставь токен, когда попросит. На вопрос про git credentials можно ответить `n`.

Проверить, что вошёл:

```powershell
.\.venv\Scripts\hf.exe auth whoami
```

Дальше всё остальное делается командами ниже — или скажи мне, и я выполню.

---

## Развёртывание

### Создать Space

```powershell
.\.venv\Scripts\hf.exe repo create ai-support-agent --repo-type space --space_sdk docker
```

Space появится по адресу `https://huggingface.co/spaces/ТВОЙ-НИК/ai-support-agent`,
а сайт будет жить на `https://ТВОЙ-НИК-ai-support-agent.hf.space`.

### Залить код

```powershell
.\.venv\Scripts\hf.exe upload ai-support-agent . . --repo-type space `
  --exclude ".venv/*" "data/*" ".git/*" "__pycache__/*" "*.pyc" "README.md" ".env"
```

`README.md` исключён намеренно: у Space свой README с YAML-заголовком, который
Hugging Face создаёт сам и по которому определяет порт и обложку. Перезаписывать
его нашим README нельзя.

### Настроить переменные

В интерфейсе Space: **Settings** → **Variables and secrets**.

| Имя | Значение | Тип |
|---|---|---|
| `LLM_PROVIDER` | `demo` | Variable |
| `SEED_ON_START` | `true` | Variable |
| `ADMIN_TOKEN` | придумай свой пароль | **Secret** |

`ADMIN_TOKEN` кладётся именно в Secret, а не в Variable: Variables видны всем,
кто открывает Space, Secrets — нет.

Сборка идёт 3–5 минут, прогресс виден на вкладке **Logs**.

---

## Обновление после правок

```powershell
git add . ; git commit -m "что изменил" ; git push          # на GitHub
.\.venv\Scripts\hf.exe upload ai-support-agent . . --repo-type space `
  --exclude ".venv/*" "data/*" ".git/*" "__pycache__/*" "*.pyc" "README.md" ".env"
```

GitHub остаётся местом, где лежит история и куда смотрит клиент. Hugging Face —
только рантайм.

---

## Что остаётся на Render

Ничего удалять не надо. Пусть висит вторым адресом: когда их авария кончится,
будет две живые ссылки, и если одна ляжет — есть вторая. Стоит это по-прежнему
ноль.

---

## Если сборка упала

**`Permission denied` при записи базы.** Space запускает контейнер от
пользователя 1000. В Dockerfile уже есть `useradd -m -u 1000 user` и
`COPY --chown=user`, а база лежит в `/home/user/app/data`. Если ошибка всё же
появилась — проверь, что не добавил `COPY` без `--chown=user`.

**Порт.** Hugging Face по умолчанию проксирует на 7860, и Dockerfile слушает
именно его, если `PORT` не задан. Не ставь переменную `PORT` в настройках Space.

**Пустая панель `/admin`.** Данные на Spaces не переживают перезапуск, поэтому
включён `SEED_ON_START=true` — при старте база наполняется примерами.
