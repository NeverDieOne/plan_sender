import argparse
import asyncio
from textwrap import dedent

from environs import Env
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from telethon import TelegramClient
from telethon.sessions import StringSession

url = 'https://mentors.dvmn.org/mentor-ui/'


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('notify', action='store_false', help='Оповестить о непроверенных')
    parser.add_argument('send_plans', action='store_false', help='Разослать планы')
    return parser.parse_args()


async def main():
    env = Env()
    env.read_env()

    args = get_args()

    if not args.notify and not args.send_plans:
        print('Не указан ни один аргумент!')
        return

    selenium_user = env.str('SELENIUM_USER')
    selenium_password = env.str('SELENIUM_PASSWORD')
    selenium_auth = f'{selenium_user}:{selenium_password}'

    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--start-maximized")
    driver = webdriver.Remote(
        command_executor=f'https://{selenium_auth}@selenium.neverdieone.ru',
        options=chrome_options,
    )
    driver.implicitly_wait(5)

    try:
        driver.get(url)

        input_login_field = driver.find_element(By.ID, 'id_username')
        input_password_field = driver.find_element(By.ID, 'id_password')

        input_login_field.send_keys(env.str('DVMN_USERNAME'))
        input_password_field.send_keys(env.str('DVMN_PASSWORD'))

        login_button = driver.find_element(By.CSS_SELECTOR, 'input[type=submit]')
        login_button.click()

        driver.get(url)

        urls = driver.find_elements(By.CSS_SELECTOR, 'div.container a')
        hrefs = [u.get_attribute('href') for u in urls]

        messages = {}
        without_report = []
        for href in hrefs:
            # так работает vue.js, в браузере нужно несколько раз нажать энтер
            driver.get(href)
            driver.get(href)
            driver.get(href)

            try:
                gist_link = driver.find_element(
                    By.XPATH, '//a[contains(text(), "Ссылка на гист")]'
                )
            except:
                # ученик в академе, пропускаем
                continue

            try:
                tg_link = driver.find_element(
                    By.XPATH, '//span[contains(text(), "Tg")]'
                )
                student_tg = tg_link.text.split('@')[-1]
                driver.find_element(
                    By.XPATH, '//span[contains(text(), "обновлено")]'
                )
            except NoSuchElementException:
                without_report.append(student_tg)
                continue
            
            gist_href = gist_link.get_attribute('href')
            messages[student_tg] = gist_href
    except Exception as err:
        print(err)
        driver.save_screenshot('error.png')
    finally:
        driver.quit()

    session = StringSession(env.str('SESSION'))
    client = TelegramClient(session, api_id=env.str('TG_API_ID'), api_hash=env.str('TG_API_HASH'))

    await client.start()

    try:
        if args.notify:
            for student in without_report:
                text = dedent(f"""\
                    Привет. Не увидел твоей отписки в плане(
                    Она нужна мне, чтобы следить за твоим прогрессом и вовремя реагировать на сложности.
                    Отпишись, плз.
                    """)
                await client.send_message(student, text, link_preview=False)

        if args.send_plans:
            for tag, plan in messages.items():
                text = dedent(f"""\
                Привет привет. Держи планчик на новую неделю:
                {plan}
                """)

                await client.send_message(tag, text, link_preview=False)
    finally:
        await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())
