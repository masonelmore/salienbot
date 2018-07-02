# TODO: use logging for debug messages
# TODO: move temporary display stuff from here to display.  e.g. showing boss info

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

    def run(self):
        display.welcome()

        while True:
            player_json = self._call_api(self.api.get_player_info)
            self.player = Player.from_json(player_json)
            display.player_info(self.player)

            planets = self.potential_planets()
            display.planets(planets)
            self.planet = self.best_planet(planets)
            self.zone = self.planet.best_zone()

            # Join the best planet if we aren't already there.
            if self.player.active_planet != self.planet.id:
                # Leave our current zone if we've already joined another before
                # leaving the planet.
                if self.player.active_zone_game is not None:
                    display.debug(f'Leaving zone {self.player.active_zone_game} to join another planet')
                    self._call_api(self.api.leave_game, self.player.active_zone_game)
                # Leave our current planet if we've already joined another.
                if self.player.active_planet is not None:
                    display.debug(f'Leaving planet {self.player.active_planet} to join another planet')
                    self._call_api(self.api.leave_game, self.player.active_planet)
                display.debug(f'Joining planet {self.planet.id}')
                self._call_api(self.api.join_planet, self.planet.id)

            # Join the best zone if we aren't already there.  Need to check if
            # we changed planets with the second half of the `if` just in case
            # we want to join the same zone position on another planet.
            if self.player.active_zone_game != self.zone.game_id:
                # Leave our current zone if we've already joined another.
                if self.player.active_zone_game is not None:
                    display.debug(f'Leaving zone {self.player.active_zone} to join another on the same planet')
                    self._call_api(self.api.leave_game, self.player.active_zone_game)
                if self.zone.boss_active:
                    display.debug(f'Joining boss zone {self.zone.id} on planet {self.planet.id}')
                    resp = self._call_api(self.api.join_boss_zone, self.zone.id)
                    display.debug(resp)
                else:
                    display.debug(f'Joining zone {self.zone.id} on planet {self.planet.id}')
                    self._call_api(self.api.join_zone, self.zone.id)

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
                display.error(f'Calling {func.__name__}() gave eresult: {eresult} - {json}')
                display.info(f'Retrying API call in {fail_wait} seconds...')
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
        display.info(f'Fighting on planet {self.planet.id} in zone {self.zone.id} - difficulty: {self.zone.difficulty_name()}')
        score = self.zone.score()
        report_damage_wait = 110
        display.debug(f'Waiting {report_damage_wait} seconds to report a score of {score}')
        time.sleep(report_damage_wait)
        self._call_api(self.api.report_score, score)

    def play_boss_zone(self):
        use_heal = 0
        damage_to_boss = 0
        damage_taken = 0

        report_damage_wait = 5
        healing_cooldown = timedelta(seconds=120)
        time_heal_used = datetime.now() - healing_cooldown

        while True:
            resp = self._call_api(self.api.report_boss_damage, use_heal, damage_to_boss, damage_taken)

            if resp.get('game_over', False):
                display.debug('[BOSS] game over.  leaving game...')
                break

            if use_heal == 1:
                use_heal = 0
                time_heal_used = datetime.now()

            waiting_for_players = resp.get('waiting_for_players')
            if waiting_for_players:
                display.debug('[BOSS] waiting for players...')
                time.sleep(report_damage_wait)
                continue

            boss_status = resp.get('boss_status', None)
            if boss_status is None:
                display.debug('[BOSS] no boss_status, waiting...')
                time.sleep(report_damage_wait)
                continue

            # Boss is ready to fight.  Start doing damage.
            damage_to_boss = 1

            # Cast heal if it's off cooldown and the players need healing.
            if time_heal_used + healing_cooldown > datetime.now():
                display.debug('[BOSS] healing off cooldown.  checking is players need heals.')
                boss_players = boss_status.get('boss_players')
                total_hp = 0
                total_max_hp = 0
                for player in boss_players:
                    hp = player.get('hp')
                    max_hp = player.get('max_hp')
                    total_hp += hp
                    total_max_hp += max_hp

                hp_percent = float(total_hp)/total_max_hp
                display.debug(f'[BOSS] player health: {hp_percent:5.2f}%')
                if hp_percent < 0.75:
                    use_heal = 1

            # Show player stats if they provided their accountid
            if self.account_id > -1:
                player = None
                # TODO: possibly looping over the players again if we checked for heals above
                for p in boss_status.get('boss_players'):
                    if p.get('accountid') == self.account_id:
                        player = p
                        break
                name = player.get('name')
                hp = player.get('hp')
                max_hp = player.get('max_hp')
                starting_score = int(player.get('score_on_join', 0))
                starting_level = player.get('level_on_join')
                xp_earned = player.get('xp_earned')
                new_level = player.get('new_level')
                display.info(f'{name} Starting score: {starting_score} ({starting_level}) - Current score: {starting_score+xp_earned} +{xp_earned} ({new_level})')

            boss_hp = boss_status.get('boss_hp')
            boss_max_hp = boss_status.get('boss_max_hp')
            display.info(f'Boss HP: {boss_hp} / {boss_max_hp}')
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
    def __init__(self, level, score, next_level_score, active_planet, active_zone, active_zone_game):
        self.level = level
        self.score = score
        self.next_level_score = next_level_score
        self.active_planet = active_planet
        self.active_zone = active_zone
        self.active_zone_game = active_zone_game

    @classmethod
    def from_json(cls, player_json):
        level = player_json.get('level')
        score = player_json.get('score')
        # TODO: next_level_score is sometimes not there?  needs proper fix
        next_level_score = player_json.get('next_level_score', 1000000000)
        active_planet = player_json.get('active_planet', None)
        active_zone = player_json.get('active_zone_position', None)
        active_zone_game = player_json.get('active_zone_game', None)
        # active_boss_game replaces active_zone_game, so we must check for that
        # after.
        if active_zone_game is None:
            active_zone_game = player_json.get('active_boss_game', None)

        player = cls(level, score, next_level_score, active_planet, active_zone, active_zone_game)
        return player
