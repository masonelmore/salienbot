# -*- coding: utf-8 -*-

# TODO: use logging for debug messages
# TODO: move temporary display stuff from here to display.  e.g. showing boss info

import logging
import time
from datetime import datetime, timedelta

import display

# TODO: shouldn't these be a part of the Zone class?
ZONE_LOW = 1
ZONE_MEDIUM = 2
ZONE_HIGH = 3
ZONE_BOSS = 4


class Bot():
    def __init__(self, api_client, account_id):
        self.api = api_client
        self.account_id = account_id

        # These will get populated when run is called
        self.planet = None
        self.zone = None
        self.player = None

        self.logger = logging.getLogger(__name__)

    def run(self):
        display.welcome()

        while True:
            player_json = self._call_api(self.api.get_player_info)
            self.logger.debug(player_json)
            self.player = Player.from_json(player_json)
            display.player_info(self.player)

            planets = self.potential_planets()
            display.planets(planets)
            self.planet = self.best_planet(planets)
            self.zone = self.planet.best_zone()

            # Join the best planet if we need to.
            if self.player.active_planet != self.planet.id:
                # Leave the current Zone if we've already joined one.
                if self.player.active_zone_game is not None:
                    self.logger.debug(f'Leaving Zone {self.player.active_zone} ({self.player.active_zone_game}) before leaving Planet {self.player.active_planet}')
                    self._call_api(self.api.leave_game, self.player.active_zone_game)
                # Leave the current Planet if we've already joined one.
                if self.player.active_planet is not None:
                    self.logger.debug(f'Leaving Planet {self.player.active_planet} before joining Planet {self.planet.id}')
                    self._call_api(self.api.leave_game, self.player.active_planet)
                self.logger.debug(f'Joining planet {self.planet.id}')
                self._call_api(self.api.join_planet, self.planet.id)

            # Join the best zone if we aren't already there.
            if self.player.active_zone_game != self.zone.game_id:
                # Leave the current Zone if we've already joined one.
                if self.player.active_zone_game is not None:
                    self.logger.debug(f'Leaving Zone {self.player.active_zone} ({self.player.active_zone_game}) on Planet {self.player.active_planet}')
                    self._call_api(self.api.leave_game, self.player.active_zone_game)
                if self.zone.boss_active:
                    self.logger.debug(f'Joining boss Zone {self.zone.id} on Planet {self.planet.id}')
                    self._call_api(self.api.join_boss_zone, self.zone.id)
                else:
                    self.logger.debug(f'Joining Zone {self.zone.id} on Planet {self.planet.id}')
                    self._call_api(self.api.join_zone, self.zone.id)

            display.join_zone_status(self.player, self.planet, self.zone)

            if self.zone.boss_active:
                self.play_boss_zone()
            else:
                self.play_zone()

    def _call_api(self, func, *args, **kwargs):
        # TODO: what about not throwing an exception when it fails?  what if the
        # caller wants to handle the error better than this?
        attempts = 0
        max_attempts = 5
        fail_wait = 1
        while attempts < max_attempts:
            json, eresult = func(*args, **kwargs)
            if eresult != '1':
                self.logger.debug(f'Calling {func.__name__}() gave eresult: {eresult} - {json}')
                self.logger.debug(f'Retrying API call in {fail_wait} seconds...')
                attempts += 1
                time.sleep(fail_wait)
                fail_wait *= 2
            else:
                break

        if attempts == max_attempts:
            raise Exception('Unable to recover from failed API call attempts')

        return json

    def potential_planets(self):
        # GetPlanets only returns basic information about each planet.  We must
        # call GetPlanet to get the zones for the planet.
        planets_simple = self._call_api(self.api.get_planets)
        planets = []
        for planet in planets_simple:
            # I'm not sure this is neccessary.  There might be a small chance
            # that a planet is captured and still active.
            if planet.get('state').get('captured'):
                continue

            planet_id = planet.get('id')
            planet_detail = self._call_api(self.api.get_planet, planet_id)
            planets.append(Planet.from_json(planet_detail))
        return planets

    @staticmethod
    def best_planet(planets):
        # Choose the planet with the most boss, high, medium, and low zones in
        # that order of priority.
        planets.sort(key=lambda p: len(p.zones(ZONE_LOW)), reverse=True)
        planets.sort(key=lambda p: len(p.zones(ZONE_MEDIUM)), reverse=True)
        planets.sort(key=lambda p: len(p.zones(ZONE_HIGH)), reverse=True)
        planets.sort(key=lambda p: len(p.zones(ZONE_BOSS)), reverse=True)

        best_planet = planets[0]
        return best_planet

    def play_zone(self):
        score = self.zone.score()
        report_damage_wait = 110
        self.logger.debug(f'Waiting {report_damage_wait} seconds to report a score of {score}')
        time.sleep(report_damage_wait)
        resp = self._call_api(self.api.report_score, score)
        display.zone_finished(resp)

    def play_boss_zone(self):
        display.message('Starting boss battle!')
        use_heal = 0
        damage_to_boss = 0
        damage_taken = 0

        report_damage_wait = 5
        healing_cooldown = timedelta(seconds=120)
        time_heal_used = datetime.now() - healing_cooldown

        while True:
            self.logger.debug(f'Reporting damage_to_boss {damage_to_boss} - use_heal {use_heal} - damage_taken {damage_taken}')
            resp = self._call_api(self.api.report_boss_damage, use_heal, damage_to_boss, damage_taken)

            if resp.get('game_over', False):
                display.message('Game Over! Leaving boss game...')
                break

            if use_heal == 1:
                use_heal = 0
                time_heal_used = datetime.now()

            waiting_for_players = resp.get('waiting_for_players')
            if waiting_for_players:
                self.logger.debug(f'Waiting for players, sleeping for {report_damage_wait} seconds...')
                time.sleep(report_damage_wait)
                continue

            boss_status = resp.get('boss_status', None)
            if boss_status is None:
                self.logger.debug(f'Boss status empty, sleeping for {report_damage_wait} seconds...')
                time.sleep(report_damage_wait)
                continue

            # Boss is ready to fight.  Start doing damage.
            damage_to_boss = 1

            display.boss_progress(boss_status, self.account_id)

            team = boss_status.get('boss_players')
            total_hp_percent = 0.0
            for player in team:
                hp = player.get('hp')
                max_hp = player.get('max_hp')
                total_hp_percent += hp / max_hp

                if player.get('accountid') == self.account_id:
                    if hp <= 0:
                        display.message('!!! Game Over. You are dead! :( !!!')
                        return

            avg_hp_percent = total_hp_percent / len(team)
            display.message(f'Average player health: {avg_hp_percent*100:.2f}%')

            # Cast heal if it's off cooldown and the players need healing.
            if time_heal_used + healing_cooldown < datetime.now():
                use_heal = 1
                display.message('>>> Using Heal <<<')

            time.sleep(report_damage_wait)


class Planet():
    def __init__(self, planet_id, active, captured, progress, boss_position, zones):
        self.id = planet_id
        self.active = active
        self.captured = captured
        self.progress = progress
        self.boss_position = boss_position
        self._zones = self._group_zones(zones)

    @classmethod
    def from_json(cls, planet_json):
        planet_id = planet_json.get('id')
        state = planet_json.get('state')
        active = state.get('active')
        captured = state.get('captured')
        boss_position = state.get('boss_zone_position', -1)

        zones = []
        total_progress = 0
        for zone_json in planet_json.get('zones'):
            zone = Zone.from_json(zone_json)
            total_progress += zone.progress
            zones.append(zone)
        max_progress = len(zones)
        progress = total_progress / max_progress

        planet = cls(planet_id, active, captured, progress, boss_position, zones)
        return planet

    @staticmethod
    def _group_zones(zones):
        grouped = {
            ZONE_LOW: [],
            ZONE_MEDIUM: [],
            ZONE_HIGH: [],
            ZONE_BOSS: [],
        }
        for zone in zones:
            if zone.captured:
                continue
            if zone.type == ZONE_BOSS:
                grouped[ZONE_BOSS].append(zone)
            grouped[zone.difficulty].append(zone)
        return grouped

    def zones(self, difficulty):
        return self._zones[difficulty]

    def boss_active(self):
        return self.boss_position > -1

    def best_zone(self):
        # Choose the highest difficulty zone with the least progress captured.
        for difficulty in [ZONE_BOSS, ZONE_HIGH, ZONE_MEDIUM, ZONE_LOW]:
            zones = self.zones(difficulty)
            if len(zones) == 0:
                continue
            zone = self._least_progress(zones)
            return zone

    @staticmethod
    def _least_progress(zones):
        zone = zones[0]
        least_progress = zone.progress
        for z in zones[1:]:
            if z.progress < least_progress:
                zone = z
                least_progress = z.progress
        return zone


class Zone():
    _SCORES = {
        ZONE_LOW: 600,
        ZONE_MEDIUM: 1200,
        ZONE_HIGH: 2400,
    }

    _DIFFICULTY_NAMES = {
        ZONE_LOW: "Low",
        ZONE_MEDIUM: "Medium",
        ZONE_HIGH: "High",
    }

    def __init__(self, zone_id, game_id, zone_type, difficulty, captured, progress, boss_active):
        self.id = zone_id
        self.game_id = game_id
        self.type = zone_type
        self.difficulty = difficulty
        self.captured = captured
        self.progress = progress
        self.boss_active = boss_active

    @classmethod
    def from_json(cls, zone_json):
        zone_id = zone_json.get('zone_position')
        game_id = zone_json.get('gameid')
        zone_type = zone_json.get('type')
        difficulty = zone_json.get('difficulty')
        captured = zone_json.get('captured')
        progress = zone_json.get('capture_progress', 0)
        boss_active = zone_json.get('boss_active', False)

        zone = cls(zone_id, game_id, zone_type, difficulty,
                   captured, progress, boss_active)
        return zone

    def score(self):
        return self._SCORES.get(self.difficulty, -1)

    def difficulty_name(self):
        return self._DIFFICULTY_NAMES.get(self.difficulty, -1)


class Player():
    def __init__(self, level, score, next_level_score, active_planet, time_on_planet, active_zone, active_zone_game):
        self.level = level
        self.score = score
        self.next_level_score = next_level_score
        self.active_planet = active_planet
        self.time_on_planet = time_on_planet
        self.active_zone = active_zone
        self.active_zone_game = active_zone_game

    @classmethod
    def from_json(cls, player_json):
        level = player_json.get('level')
        score = int(player_json.get('score', 0))
        # next_level_score disappears at max level.  Setting it to the current
        # score should be fine.
        next_level_score = int(player_json.get('next_level_score', score))
        active_planet = player_json.get('active_planet', None)
        time_on_planet = player_json.get('time_on_planet', 0)
        active_zone = player_json.get('active_zone_position', None)
        active_zone_game = player_json.get('active_zone_game', None)
        # active_boss_game replaces active_zone_game
        if active_zone_game is None:
            active_zone_game = player_json.get('active_boss_game', None)

        player = cls(level, score, next_level_score, active_planet, time_on_planet, active_zone, active_zone_game)
        return player
