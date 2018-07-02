import sys

from api import Client
from bot import Bot

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('usage: python main.py <token> [accountid]')
        print('You can get your token from https://steamcommunity.com/saliengame/gettoken')
        print('The optional accountid (steamid32) is used to show your stats during a boss battle.')
        sys.exit(-1)

    if len(sys.argv) == 2:
        token = sys.argv[1]
        account_id = -1

    if len(sys.argv) == 3:
        token = sys.argv[1]
        account_id = int(sys.argv[2])

    client = Client(token)
    bot = Bot(client, account_id)
    try:
        bot.run()
    except KeyboardInterrupt:
        print('exiting...')
        sys.exit(0)
