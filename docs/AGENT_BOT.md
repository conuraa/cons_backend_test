# Clobus Support Agent Bot

## Назначение

Agent Bot "Clobus Support" используется для отправки автоматических сообщений клиентам без влияния на SLA (First Response Time).

## Проблема, которую решает

При создании консультации система отправляет автоматическое сообщение:
> "Ваша заявка на консультацию принята. Номер заявки: 00000546458..."

**Проблема:** Если отправлять это сообщение от имени агента, Chatwoot засчитывает его как First Response, и SLA показывает 100% (ответ за 0 секунд).

**Решение:** Сообщения от Agent Bot не влияют на SLA — система ждёт реального ответа от консультанта.

## Конфигурация

### Chatwoot Agent Bot

| Параметр | Значение |
|----------|----------|
| ID | 3 |
| Имя | Clobus Support |
| Токен | см. .env |
| Тип | webhook |

### Переменная окружения (.env)

```env
CHATWOOT_AGENT_BOT_TOKEN=<token>
```

## Где используется

| Файл | Метод | Описание |
|------|-------|----------|
| `consultations.py` | создание консультации | "Ваша заявка принята..." |
| `consultations.py` | перенос даты | "Консультация перенесена..." |
| `consultations.py` | отмена | "Заявка аннулирована" |
| `manager_notifications.py` | назначение менеджера | "Вам назначен консультант..." |

## Сравнение типов сообщений

| Метод | Видно клиенту | Влияет на SLA | Использование |
|-------|---------------|---------------|---------------|
| `send_message` | Да | Да | Ответы агентов |
| `send_activity_message` | Нет | Нет | Системные записи |
| `send_bot_message` | Да | Нет | Автоуведомления |

## Проверка работы

```bash
# Проверить first_reply_created_at консультации
curl -s "https://suppdev.clobus.uz/api/v1/accounts/1/conversations/{id}" \
  -H "api_access_token: TOKEN" | jq '.first_reply_created_at'
```

- `0` — агент ещё не ответил
- `timestamp` — агент ответил, FRT засчитан

## Управление

### UI
Настройки → Боты → Agent Bots → Clobus Support

### API
```bash
# Список ботов
curl "https://suppdev.clobus.uz/api/v1/accounts/1/agent_bots" -H "api_access_token: TOKEN"

# Обновить имя
curl -X PATCH "https://suppdev.clobus.uz/api/v1/accounts/1/agent_bots/3" \
  -H "api_access_token: TOKEN" -d '{"name": "New Name"}'
```
