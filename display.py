import time
from version import __version__ as version

DEBUG = True


def _print(message):
    timestamp = time.strftime('%H:%M:%S')
    print(f'[{timestamp}] {message}')


def error(message):
    _print(f'[ERROR] {message}')


def info(message):
    _print(f'[INFO] {message}')


def debug(message):
    if DEBUG:
        _print(f'[DEBUG] {message}')


def welcome():
    _print(f'Starting SalienBot {version}')


def player_info(player):
    level = player.level
    score = player.score
    next_level_score = player.next_level_score
    percent = float(score)/float(next_level_score)
    _print(f'Player Level: {level} - Score: {score} / {next_level_score} ({percent:5.2f}%)')


def planets(planets):
    _print('--- Potential Active Planets ---')
    for planet in planets:
        # TODO: Better constants management?
        nboss = len(planet.zones(4))
        nhigh = len(planet.zones(3))
        nmedium = len(planet.zones(2))
        nlow = len(planet.zones(1))
        _print(f'Planet {planet.id:3} - Progress: {planet.progress*100:5.2f}% - Boss: {nboss:2} - High: {nhigh:2} - Medium: {nmedium:2} - Low: {nlow:2}')
