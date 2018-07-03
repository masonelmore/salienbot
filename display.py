import logging
import time
from datetime import timedelta

from version import __version__ as version

logger = logging.getLogger(__name__)


def welcome():
    logger.info(f'Starting SalienBot {version}')


def message(msg):
    logger.info(msg)


def player_info(player):
    logger.info('--- Player Information ---')
    level = player.level
    score = player.score
    next_level_score = player.next_level_score
    percent = float(score)/float(next_level_score)
    logger.info(f'Level: {level} - Score: {score:,d} - Next Level: {next_level_score:,d} - Progress: {percent*100:.2f}%')

    planet_message = ''
    if player.active_planet is not None:
        time_on_planet = timedelta(seconds=player.time_on_planet)
        planet_message = f'On Planet: {player.active_planet} for {time_on_planet}'
    if player.active_zone is not None:
        planet_message += f' - Zone: {player.active_zone} ({player.active_zone_game})'
    if planet_message != '':
        logger.info(planet_message)


def planets(planets):
    logger.info('--- Active Planets ---')
    logger.info('Planet  Progress  Boss  High  Medium  Low')
    for planet in planets:
        # TODO: Better constants management?
        nboss = len(planet.zones(4))
        nhigh = len(planet.zones(3))
        nmedium = len(planet.zones(2))
        nlow = len(planet.zones(1))
        logger.info(f'{planet.id:5}  {planet.progress*100:8.2f}%  {nboss:4}  {nhigh:4}  {nmedium:6}  {nlow:3}')


def join_zone_status(player, planet, zone):
    logger.info(f'Playing on Planet: {planet.id} - Zone: {zone.id} - Difficulty: {zone.difficulty_name()} - Progress: {zone.progress*100:.2f}%')


def zone_finished(score_json):
    old_score = int(score_json.get('old_score', 0))
    old_level = int(score_json.get('old_level', 0))
    new_score = int(score_json.get('new_score', 0))
    new_level = int(score_json.get('new_level', 0))

    logger.info('>>> Round finished! <<<')
    msg = ''
    if new_level > old_level:
        msg += 'You\'ve gained a new level! '

    xp_earned = new_score - old_score
    msg += f'XP Earned: {xp_earned}'

    logger.info(msg)


def boss_progress(status, account_id):
    players = status.get('boss_players')

    # Put our player at the bottom of the list.
    players.sort(key=lambda p: p.get('accountid') == account_id)

    logger.info('Player Name           HP               XP Earned')
    for player in players:
        name = player.get('name')
        hp = player.get('hp')
        max_hp = player.get('max_hp')
        xp_earned = player.get('xp_earned')
        logger.info(f'{name:20}  {hp:6} / {max_hp:6}  {xp_earned:10,d}')

    boss_hp = status.get('boss_hp')
    boss_max_hp = status.get('boss_max_hp')
    logger.info(f'Boss HP: {boss_hp:,d} / {boss_max_hp:,d}')
