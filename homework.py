import logging
import os
import time
from http import HTTPStatus

import telegram
import requests

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверяет доступность переменных окружения."""
    tokens = [PRACTICUM_TOKEN, TELEGRAM_CHAT_ID, TELEGRAM_TOKEN]
    for token in tokens:
        if token is None:
            logging.critical('Отсутвует некоторая информация.')
            raise Exception


def send_message(bot, message):
    """Отправляет сообщение в telegram-чат."""
    logging.debug('Успешно отправилось сообщение!')
    return bot.send_message(TELEGRAM_CHAT_ID, message)


def get_api_answer(timestamp):
    """Делает запрос к API-сервиса."""
    try:
        response = requests.get(
            url=ENDPOINT,
            headers=HEADERS,
            params={'from_date': timestamp},
        )
        if response.status_code != HTTPStatus.OK:
            logging.error(
                f'Сбой в работе программы. Эндпоинт:{ENDPOINT} недоступен.')
            raise Exception  
    except requests.RequestException:
        logging.error(
            f'Сбой в работе программы. Эндпоинт:{ENDPOINT} недоступен.'
        )
    return response.json()


def check_response(response):
    """Проверяет ответ API на соотвествие документации."""
    if type(response) is not dict:
        raise TypeError('Тип ответа не тот.')
    elif 'homeworks' not in response.keys():
        logging.error('Отсутствие нужных ключей.')
        raise KeyError
    elif type(response['homeworks']) is not list:
        raise TypeError('Список передан не правильно.')
    else:
        return response


def parse_status(homework):
    """Вызволяет статус домашнего задания."""
    if homework.get('homework_name') is None:
        raise ValueError('Неверное имя домашнего задания')
    if homework.get('status') is None:
        raise ValueError('Неверный статус домашнего задания.')
    if homework.get('status') not in HOMEWORK_VERDICTS:
        raise Exception
    homework_name = homework['homework_name']
    verdict = HOMEWORK_VERDICTS[homework['status']]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(timestamp=timestamp)
            response = check_response(response)
            if response:
                homework = response['homeworks'][0]
                message = parse_status(homework)
                send_message(bot, message)
            timestamp = response.get('current_date')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
            send_message(bot, message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
