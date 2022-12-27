import argparse
import asyncio
import datetime
import locale
import re
from textwrap import dedent

import requests
from bs4 import BeautifulSoup
from environs import Env
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from telethon import TelegramClient
from telethon.sessions import StringSession

url = 'https://mentors.dvmn.org/mentor-ui/'


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--notify', action='store_true', help='Оповестить о непроверенных')
    parser.add_argument('--send_plans', action='store_true', help='Разослать планы')
    return parser.parse_args()


def get_study_days(url: str) -> int:
    study_days = 0
    response = requests.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'lxml')
    logtable = soup.select_one('.logtable')
    blocks = logtable.select('.mt-4 .mb-4')

    today = datetime.date.today()

    locale.setlocale(
        category=locale.LC_ALL,
        locale=""
    )

    study_days = 0
    for block in blocks:
        raw = block.select_one('.align-items-center').text
        pattern = re.compile(r'\s+')
        day_info = re.sub(pattern, ' ', raw).strip()

        date = ' '.join(day_info.split(' ')[:4])
        date = datetime.datetime.strptime(date, r'%d %B %Y г.').date()

        if (today - date).days >= 7:
            break

        is_study = '+' in day_info.split(' ')[-1].strip()
        if is_study:
            study_days += 1
    
    return study_days


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
                dvmn_link = driver.find_element(
                    By.XPATH, '//*[contains(@title, "Профиль")]'
                )
                driver.find_element(
                    By.XPATH, '//span[contains(text(), "обновлено")]'
                )
            except NoSuchElementException:
                without_report.append(student_tg)
                continue
            
            messages[student_tg] = {
                'gist': gist_link.get_attribute('href'),
                'dvmn_link': dvmn_link.get_attribute('href')
            }
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
                    Привет. Не увидел отписку в плане( Мне грустно(
                    """)
                await client.send_message(student, text, link_preview=False)

        if args.send_plans:
            for tag, links in messages.items():
                study_days = get_study_days(f'{links["dvmn_link"]}/history/')

                result = 'Это очень круто! Ты молодец!'
                if study_days < 4:
                    result = dedent(f"""\
                    Маловато(
                    Подскажи, есть какой-то затык? Могу как-то помочь?
                    """)

                text = dedent(f"""\
                Привет привет.
                Держи планчик на новую неделю:
                {links['gist']}

                На этой неделе ты учился(ась): {study_days} дня(ей).
                {result}
                """)
                await client.send_message(tag, text, link_preview=False)
    finally:
        await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())
