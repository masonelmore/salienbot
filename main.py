# -*- coding: utf-8 -*-

import logging
import os
import sys

from api import Client
from bot import Bot

DEBUG = 'SALIENBOT_DEBUG' in os.environ

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('usage: python main.py token steamid')
        sys.exit(-1)

    token = sys.argv[1]
    steamid64 = int(sys.argv[2])
    steamid32 = steamid64 & 0xFFFFFFFF

    logger = logging.getLogger('')
    if DEBUG:
        file_handler = logging.FileHandler('debug.log', encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s %(name)-8s %(levelname)-8s %(message)s',
            datefmt='%d-%m-%y %H:%M:%S',
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        '%(asctime)s %(levelname)-7s %(message)s',
        datefmt='%H:%M:%S',
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    client = Client(token)
    bot = Bot(client, steamid32)

    try:
        bot.run()
    except KeyboardInterrupt:
        print('exiting...')
        sys.exit(0)
