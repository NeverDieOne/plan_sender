import asyncio
from textwrap import dedent

from environs import Env
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from telethon import TelegramClient
from telethon.sessions import StringSession

url = 'https://mentors.dvmn.org/mentor-ui/'


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
        for href in hrefs:
            # так работает vue.js, в браузере нужно несколько раз нажать энтер
            driver.get(href)
            driver.get(href)
            driver.get(href)

            try:
                gist_link = driver.find_element(
                    By.XPATH, '//a[contains(text(), "Ссылка на гист")]'
                )
                tg_link = driver.find_element(
                    By.XPATH, '//p[contains(text(), "Tg")]'
                )
                days_left_elem = driver.find_element(
                    By.XPATH, '//span[contains(text(), "Остаток")]'
                )
            except NoSuchElementException:
                continue
            
            possible_days = ['6 дней', '7 дней']
            is_new = any([d in days_left_elem.text for d in possible_days])
            if not is_new:
                continue
            
            gist_href = gist_link.get_attribute('href')
            student_tg = tg_link.text.split('@')[-1]

            messages[student_tg] = gist_href
    except:
        driver.save_screenshot('error.png')
    finally:
        driver.quit()


    session = StringSession(env.str('SESSION'))
    client = TelegramClient(session, api_id=env.str('TG_API_ID'), api_hash=env.str('TG_API_HASH'))

    await client.start()

    try:
        for tag, plan in messages.items():
            text = dedent(f"""\
            [Сообщение создано ботом, твой ментор обленился в край]

            Привет! Держи планчик на новую неделю:
            {plan}
            """)

            await client.send_message(tag, text)
    finally:
        await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())
