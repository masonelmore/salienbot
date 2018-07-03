# -*- coding: utf-8 -*-

import json
import logging
import time
from requests import Request, Session
from requests.exceptions import ConnectionError, HTTPError

from version import __version__ as version


_USER_AGENT = f'SalienBot-{version} (http://github.com/masonelmore/salienbot/)'

_HOST = 'https://community.steam-api.com'
_VERSION = 'v0001'
_METHOD_GETPLANETS = 'ITerritoryControlMinigameService/GetPlanets'
_METHOD_GETPLANET = 'ITerritoryControlMinigameService/GetPlanet'
_METHOD_GETPLAYERINFO = 'ITerritoryControlMinigameService/GetPlayerInfo'
_METHOD_JOINPLANET = 'ITerritoryControlMinigameService/JoinPlanet'
_METHOD_JOINZONE = 'ITerritoryControlMinigameService/JoinZone'
_METHOD_JOINBOSSZONE = 'ITerritoryControlMinigameService/JoinBossZone'
_METHOD_REPRESENTCLAN = 'ITerritoryControlMinigameService/RepresentClan'
_METHOD_REPORTSCORE = 'ITerritoryControlMinigameService/ReportScore'
_METHOD_REPORTBOSSDAMAGE = 'ITerritoryControlMinigameService/ReportBossDamage'
_METHOD_LEAVEGAME = 'IMiniGameService/LeaveGame'


class Client():
    def __init__(self, token):
        self.token = token
        self.session = Session()
        self.session.headers.update({'User-Agent': _USER_AGENT})

        self.logger = logging.getLogger(__name__)

    @staticmethod
    def _build_url(path):
        url = f'{_HOST}/{path}/{_VERSION}/'
        return url

    def _get(self, url, params=None):
        req = Request('GET', url, params=params)
        resp = self._execute_request(req)
        return resp

    def _post(self, url, data=None):
        req = Request('POST', url, data=data)
        resp = self._execute_request(req)
        return resp

    def _execute_request(self, request):
        prepped = self.session.prepare_request(request)

        attempts = 0
        max_attempts = 10
        fail_wait = 5

        while attempts < max_attempts:
            try:
                resp = self.session.send(prepped)
                resp.raise_for_status()
                break
            except HTTPError:
                self.logger.debug(f'HTTPError - Retrying request in {fail_wait} seconds...')
            except ConnectionError:
                self.logger.debug(f'ConnectionError - Retrying request in {fail_wait} seconds...')

            attempts += 1
            time.sleep(fail_wait)
            fail_wait += 5

        if attempts == max_attempts:
            raise Exception('Unable to recover from failed request attempts')

        json = {}
        if resp.headers.get('Content-Type', '').find('application/json') > -1:
            json = resp.json().get('response')

        eresult = resp.headers.get('X-eresult', -1)
        if eresult != '1':
            json = resp.headers.get('X-error_message', 'unknown error')

        return json, eresult

    def get_planets(self, active_only=1):
        url = Client._build_url(_METHOD_GETPLANETS)
        params = {
            'active_only': active_only,
        }
        json, eresult = self._get(url, params)
        planets = json.get('planets', [])
        return planets, eresult

    def get_planet(self, planet_id):
        url = Client._build_url(_METHOD_GETPLANET)
        params = {
            'id': planet_id,
        }
        json, eresult = self._get(url, params)
        planet = json.get('planets')[0]
        return planet, eresult

    def get_player_info(self):
        url = Client._build_url(_METHOD_GETPLAYERINFO)
        params = {
            'access_token': self.token
        }
        json, eresult = self._post(url, params)
        return json, eresult

    def join_planet(self, planet_id):
        url = Client._build_url(_METHOD_JOINPLANET)
        params = {
            'access_token': self.token,
            'id': planet_id,
        }
        json, eresult = self._post(url, params)
        return json, eresult

    def join_zone(self, zoneid):
        url = Client._build_url(_METHOD_JOINZONE)
        params = {
            'access_token': self.token,
            'zone_position': zoneid,
        }
        json, eresult = self._post(url, params)
        return json, eresult

    def join_boss_zone(self, zoneid):
        url = Client._build_url(_METHOD_JOINBOSSZONE)
        params = {
            'access_token': self.token,
            'zone_position': zoneid,
        }
        json, eresult = self._post(url, params)
        return json, eresult

    def represent_clan(self, clan_id):
        url = Client._build_url(_METHOD_REPRESENTCLAN)
        params = {
            'access_token': self.token,
            'clad_id': clan_id,
        }
        json, eresult = self._post(url, params)
        return json, eresult

    def report_score(self, score):
        url = Client._build_url(_METHOD_REPORTSCORE)
        params = {
            'access_token': self.token,
            'score': score,
        }
        json, eresult = self._post(url, params)
        return json, eresult

    def report_boss_damage(self, use_heal_ability, damage_to_boss, damage_taken):
        url = Client._build_url(_METHOD_REPORTBOSSDAMAGE)
        params = {
            'access_token': self.token,
            'use_heal_ability': use_heal_ability,
            'damage_to_boss': damage_to_boss,
            'damage_taken': damage_taken,
        }
        json, eresult = self._post(url, params)
        return json, eresult

    def leave_game(self, game_id):
        url = Client._build_url(_METHOD_LEAVEGAME)
        params = {
            'access_token': self.token,
            'gameid': game_id
        }
        json, eresult = self._post(url, params)
        return json, eresult
