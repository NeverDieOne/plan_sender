import gspread
from telethon import TelegramClient
from telethon.sessions import StringSession
from environs import Env
import asyncio

from textwrap import dedent


async def main():
    gc = gspread.service_account('key.json')
    env = Env()
    env.read_env()

    worksheet = gc.open('Ученики').get_worksheet_by_id(env.int('SHEET_ID'))
    values = worksheet.col_values(4)

    session = StringSession(env.str('SESSION'))
    client = TelegramClient(
        session, api_id=env.str('TG_API_ID'), api_hash=env.str('TG_API_HASH')
    )

    text = f"""\
    Привет! Как и обещал, пишу в личку)
    Обо мне ты можешь почитать в общем чатике, но если есть какие-то вопросы - обязательно задавай, я на всё отвечу)

    Для того чтобы открыть тебе доступы и уже начать заниматься, мне нужна ссылка на профиль на сайте dvmn.org (там можно авторизоваться с помощью соц сетей и профиль появится).
    По этому же профилю я буду следить за твоей активностью и прогрессом :)

    После того как ты поделишься со мной ссылкой, я смогу выдать планчик на пробную неделю.

    Так же ещё предупрежу, что у нас курс расчитан на ~15 часов в неделю. Это среднее по больнице, так сказать, но именно при таком кол-ве часов в неделю шанс пройти курс выше)
    Ну и было бы круто, если у тебя с английским всё хорошо, потому что очень много материала на англ языке (документация, форумы, видосики и т.п.)

    И ещё хочу узнать немного о тебе, какой у тебя опыт в программировании, как себя оцениваешь вообще? Чем по жизни занимаешься? Как свободное время проводишь?)
    """

    for value in values:
        if 't.me' not in value:
            continue

        tg = '@' + value.split('/')[-1]

        

        await client.start()

        try:
            await client.send_message(tg, dedent(text), link_preview=False)
        finally:
            await client.disconnect()


if __name__ == '__main__':
    asyncio.run(main())
