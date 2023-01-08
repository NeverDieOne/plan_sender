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

MENTORS_URL = 'https://mentors.dvmn.org/mentor-ui/'


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


def parse_user_page(driver: webdriver.Remote, href: str) -> dict[str, str]:
    # так работает vue.js, в браузере нужно несколько раз нажать энтер
    driver.get(href)
    driver.get(href)
    driver.get(href)

    gist_link = driver.find_element(
        By.XPATH, '//a[contains(text(), "Ссылка на гист")]'
    )
    tg_link = driver.find_element(
        By.XPATH, '//span[contains(text(), "Tg")]'
    )
    student_tg = tg_link.text.split('@')[-1]
    dvmn_link = driver.find_element(
        By.XPATH, '//*[contains(@title, "Профиль")]'
    )
    comments = driver.find_elements(By.XPATH, "//p[contains(text(), 'Комментарий')]")
    comment = None
    if comments:
        comment = comments[0].text.split('Комментарий: ')[-1]
    
    return {
        student_tg: {
            'gist': gist_link.get_attribute('href'),
            'dvmn_link': dvmn_link.get_attribute('href'),
            'comment': comment
        }
    }


def login(driver: webdriver.Remote, login: str, password: str) -> None:
    input_login_field = driver.find_element(By.ID, 'id_username')
    input_password_field = driver.find_element(By.ID, 'id_password')

    input_login_field.send_keys(login)
    input_password_field.send_keys(password)

    login_button = driver.find_element(By.CSS_SELECTOR, 'input[type=submit]')
    login_button.click()


async def main():
    env = Env()
    env.read_env()

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
        driver.get(MENTORS_URL)
        login(driver, env.str('DVMN_USERNAME'), env.str('DVMN_PASSWORD'))
        driver.get(MENTORS_URL)

        student_urls = driver.find_elements(By.CSS_SELECTOR, 'div.container a')
        hrefs = [u.get_attribute('href') for u in student_urls]

        messages = {}
        for href in hrefs[:4]:
            try:
                messages.update(parse_user_page(driver, href))
            except NoSuchElementException:
                # Ученик в академе - пропускаем
                continue
    except Exception as err:
        print(err)
        driver.save_screenshot('error.png')
    finally:
        driver.quit()

    session = StringSession(env.str('SESSION'))
    client = TelegramClient(session, api_id=env.str('TG_API_ID'), api_hash=env.str('TG_API_HASH'))

    await client.start()

    try:
        for tag, info in messages.items():
            study_days = get_study_days(f'{info["dvmn_link"]}/history/')

            text = dedent(f"""\
            Привет привет :3
            Держи планчик на новую неделю:
            {info['gist']}

            Статистика:
            На этой неделе ты учился(ась): {study_days} дня(ей), в этот раз хорошо это или нет решай сам(а) :D.
            """)

            if comment := info['comment']:
                text += dedent(f"""\
                {'-' * 5}
                
                {comment}
                """)
            
            await client.send_message(tag, text, link_preview=False)
    finally:
        await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())
