# Рассылка гистов по ученикам из интерфейса


## .env

- TG_API_ID=айди приложения с my.telegram.org
- TG_API_HASH=хэш приложения с my.telegram.org
- SESSION=строка сессии из Telethon
- DVMN_USERNAME=логин на сайте менторов
- DVMN_PASSWORD=пароль на сайте менторов

- SELENIUM_USER=пользователь от селениума
- SELENIUM_PASSWORD=пароль от селениума

## Как пользоваться

- Создание виртуального окружения
```console
python -m venv venv
```

- Активация виртуального окружения

(Linux)
```console
. ./venv/bin/activate
```

(Windows)
```console
venv\Scripts\activate
```

- Установка зависимостей

```console
pip install -r requirements.txt
```

- Запуск скрипта

```console
python main.py
```