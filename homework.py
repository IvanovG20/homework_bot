import sys
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
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
formater = logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s'
)
handler.setFormatter(formater)
logger.addHandler(handler)


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
    if all(tokens) is False:
        logging.critical('Отсутвует некоторая информация.')
        raise Exception


def send_message(bot, message):
    """Отправляет сообщение в telegram-чат."""
    logging.debug('Отправляется сообщение в telegram.')
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except telegram.TelegramError as error:
        logging.error(f'Ошибка отправки сообщения: {error}')


def get_api_answer(timestamp):
    """Делает запрос к API-сервиса."""
    logging.debug('Делаем запрос к API.')
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
    if isinstance(response, dict) is False:
        raise TypeError('Тип ответа не тот.')
    elif 'homeworks' not in response:
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
    last_message = {
        'message': None
    }
    while True:
        try:
            response = get_api_answer(timestamp=timestamp)
            logging.debug('API-сервиса доступен.')
            response = check_response(response)
            if response:
                homework = response['homeworks'][0]
                message = parse_status(homework)
                if last_message['message'] != message:
                    send_message(bot, message)
                    logging.debug('Сообщение успешно отправленно.')
                    last_message['message'] = message
            timestamp = response.get('current_date')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
            if last_message['message'] != message:
                send_message(bot, message)
                last_message['message'] = message
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
