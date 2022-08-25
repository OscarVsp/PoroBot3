import logging
import time
from typing import Dict, List, Optional, Tuple
from urllib.error import HTTPError

from .exceptions import LeagueNotFound, MasteriesNotFound, SummonerNotFound, TeamNotFound, WatcherNotInit
import modules.FastSnake as FS
import disnake
import asyncio
import requests
import json

import asyncio
from typing import List


class Watcher:

    CHAMPIONS: dict = {}
    QUEUETYPE: List[dict] = []
    QUEUES: List[dict] = []
    MAPS: List[dict] = []

    @classmethod
    def init(cls, api_key: str):
        cls.CHAMPIONS = json.loads(
            requests.get(f"https://ddragon.leagueoflegends.com/cdn/{cls.VERSION}/data/en_US/champion.json").text
        ).get("data")
        cls.QUEUETYPE = json.loads(requests.get(f"https://static.developer.riotgames.com/docs/lol/queues.json").text)
        cls.MAPS = json.loads(requests.get(f"https://static.developer.riotgames.com/docs/lol/maps.json").text)
        cls.QUEUES = json.loads(requests.get(f"https://static.developer.riotgames.com/docs/lol/queues.json").text)

    @classmethod
    def get_watcher(cls):
        if cls.WATCHER:
            return cls.WATCHER
        raise WatcherNotInit

    @classmethod
    def champion_name_from_id(cls, champion_id: int) -> str:
        for champion in cls.CHAMPIONS.values():
            if champion.get("key") == str(champion_id):
                return champion.get("name")
        return f"Unknown (id: {champion_id})"

    @classmethod
    def maps_name_from_id(cls, map_id: int) -> str:
        for map in cls.MAPS:
            if map.get("mapID") == map_id:
                return map.get("mapName")
        return f"Unknown (id: {map_id})"

    @classmethod
    def queue_dict_from_id(cls, queue_id: int) -> dict:
        for queue in cls.QUEUES:
            if queue.get("queueId") == queue_id:
                return queue
        return {"map": "UNKNOWN MAP", "description": "UNKNOWN GAME"}


class Leagues:
    class QueueType:
        RANKED_SOLO_5x5 = "RANKED_SOLO_5x5"
        RANKED_FLEX_SR = "RANKED_FLEX_SR"

    TIERS = [
        "UNRANKED",
        "IRON",
        "BRONZE",
        "SILVER",
        "GOLD",
        "PLATINUM",
        "DIAMOND",
        "MASTER",
        "GRANDMASTER",
        "CHALLENGER",
    ]
    RANKS = ["-", "IV", "III", "II", "I"]

    class League:
        def __init__(self, league: lol.league.SummonerLeagueEntryData):
            self._leagueEntryData: lol.league.SummonerLeagueEntryData = league
            self.summoner_id: str = league.summoner_id
            self.summoner_name: str = league.summoner_name
            self.league_points: int = league.league_points
            self.rank: str = league.rank
            self.wins: int = league.wins
            self.losses: int = league.losses
            self.veteran: bool = league.veteran
            self.inactive: bool = league.inactive
            self.fresh_blood: bool = league.fresh_blood
            self.hot_streak: bool = league.hot_streak
            self.mini_series: bool = league.fresh_blood
            self.fresh_blood: bool = league.fresh_blood
            self.hot_streak: bool = league.hot_streak
            self.mini_series: lol.league.MiniSeriesData = league.mini_series
            self.league_id: str = league.league_id
            self.queue: str = league.queue
            self.tier: str = league.tier

        @staticmethod
        def default(queueType: str):
            return Leagues.League(
                {"queueType": queueType, "tier": Leagues.TIERS[0], "rank": Leagues.RANKS[0], "leaguePoints": 0}
            )

        @property
        def absolut_score(self) -> int:
            return Leagues.TIERS.index(self.tier) * 10000 + Leagues.RANKS.index(self.rank) * 1000 + self.league_points

        @property
        def tier_emote(self) -> str:
            return FS.Emotes.Lol.Ranks.get(self.tier)

    def __init__(self, summonerLeague: lol.SummonerLeague):
        self._summonerLeague: lol.SummonerLeague = summonerLeague
        self.summoner_id: str = summonerLeague.summoner_id
        self.solo: Leagues.League = None
        self.flex: Leagues.League = None
        for entry in summonerLeague.entries:
            if entry.league_id == Leagues.QueueType.RANKED_SOLO_5x5:
                self.solo = Leagues.League(entry)
            elif entry.league_id == Leagues.QueueType.RANKED_FLEX_SR:
                self.flex = Leagues.League(entry)
        if self.solo == None:
            self.solo = Leagues.League.default(Leagues.QueueType.RANKED_SOLO_5x5)
        if self.flex == None:
            self.flex = Leagues.League.default(Leagues.QueueType.RANKED_FLEX_SR)

    @classmethod
    async def by_summoner_id(cls, summoner_id: str):
        try:

            listLeagueEntryDto: dict = cls.get_watcher().league.by_summoner(cls.REGION, summoner_id)
            await asyncio.sleep(0.1)
            return Leagues(listLeagueEntryDto)
        except (ApiError):
            raise LeagueNotFound

    @property
    def highest(self) -> Optional[League]:
        if self.solo.absolut_score > self.flex.absolut_score:
            return self.solo
        return self.flex

    @property
    def first(self) -> Optional[League]:
        if self.solo.absolut_score > 0:
            return self.solo
        return self.flex


class ChampionMastery(Watcher):
    def __init__(self, championMasteryDto: dict):
        self._championMasteryDto: dict = championMasteryDto
        self.championId: str = str(championMasteryDto.get("championId"))
        self.championLevel: int = championMasteryDto.get("championLevel")
        self.championPoints: int = championMasteryDto.get("championPoints")
        self.championPointsUntilNextLevel: int = championMasteryDto.get("championPointsUntilNextLevel")
        self.championPointsSinceLastLevel: int = championMasteryDto.get("championPointsSinceLastLevel")
        self.chestGranted: bool = championMasteryDto.get("chestGranted")
        self.lastPlayTime: int = championMasteryDto.get("lastPlayTime")
        self.currentToken: int = championMasteryDto.get("tokensEarned")

        self.name: str = Watcher.champion_name_from_id(self.championId)
        self.icon: str = FS.Emotes.Lol.Champions.get(self.championId)
        num = float("{:.3g}".format(self.championPoints))
        magnitude = 0
        while abs(num) >= 1000:
            magnitude += 1
            num /= 1000.0
        self.championPointsFormatted: str = "{}{}".format(
            "{:f}".format(num).rstrip("0").rstrip("."), ["", "K", "M", "B", "T"][magnitude]
        )

    @classmethod
    async def by_summoner_and_champion(cls, encrypted_summoner_id: str, champion_id: str):
        if cls.WATCHER:
            try:
                championMasteryDto = cls.WATCHER.champion_mastery.by_summoner_by_champion(
                    region=cls.REGION, encrypted_summoner_id=encrypted_summoner_id, champion_id=champion_id
                )
                await asyncio.sleep(0.1)
                return ChampionMastery(championMasteryDto)
            except requests.exceptions.HTTPError:
                return None
        raise WatcherNotInit

    @property
    def emote(self) -> str:
        return FS.Emotes.Lol.MASTERIES[self.championLevel]

    @property
    def line_description(self) -> str:
        return f"{self.emote} **{self.icon}** *{self.championPointsFormatted}*"


class Masteries(Watcher):
    def __init__(self, listChampionMasteryDto: dict):
        self._listChampionMasteryDto: List[dict] = listChampionMasteryDto
        self.champions: List[ChampionMastery] = []
        for championMasteryDto in listChampionMasteryDto:
            self.champions.append(ChampionMastery(championMasteryDto))
        self.champions.sort(key=lambda x: x.championPoints, reverse=True)

    @classmethod
    async def by_summoner(cls, id: str):
        try:
            listChampionMasteryDto: List[dict] = cls.get_watcher().champion_mastery.by_summoner(cls.REGION, id)
            await asyncio.sleep(0.1)
            return Masteries(listChampionMasteryDto)
        except (ApiError):
            MasteriesNotFound


class CurrentGame(Watcher):
    class Perks:
        def __init__(self, perksInfo: dict):
            self._perksInfo: dict = perksInfo
            self.perkIds: List[int] = perksInfo.get("perkIds")
            self.perkStyle: int = perksInfo.get("perkStyle")
            self.perkSubStyle: int = perksInfo.get("perkSubStyle")

        @property
        def emote(self) -> str:
            return FS.Emotes.Lol.Runes.Perks.NONE

        @property
        def subEmote(self) -> str:
            return FS.Emotes.Lol.Runes.Perks.NONE

        @property
        def text(self) -> str:
            return f"""> {FS.Emotes.Lol.Runes.Perks.Get(self.perkIds[0])}{FS.Emotes.Lol.Runes.Perks.Get(self.perkIds[4])}{FS.Emotes.Lol.Runes.Perks.Get(self.perkIds[6])}
        > {FS.Emotes.Lol.Runes.Perks.Get(self.perkIds[1])}{FS.Emotes.Lol.Runes.Perks.Get(self.perkIds[5])}{FS.Emotes.Lol.Runes.Perks.Get(self.perkIds[7])}
        > {FS.Emotes.Lol.Runes.Perks.Get(self.perkIds[2])}⬛{FS.Emotes.Lol.Runes.Perks.Get(self.perkIds[8])}
        > {FS.Emotes.Lol.Runes.Perks.Get(self.perkIds[3])}"""

    class CustomizationObject:
        def __init__(self, customizationObjectInfo: dict):
            self._customizationObjectInfo: dict = customizationObjectInfo
            self.category: str = customizationObjectInfo.get("category")
            self.content: str = customizationObjectInfo.get("content")

    class Participant:
        def __init__(self, participantInfo: dict):
            self._participantInfo: dict = participantInfo
            self.championId: str = str(participantInfo.get("championId"))
            self.perks: CurrentGame.Perks = CurrentGame.Perks(participantInfo.get("perks"))
            self.profileIconId: int = participantInfo.get("profileIconId")
            self.bot: bool = participantInfo.get("bot")
            self.teamId: int = participantInfo.get("teamId")
            self.summonerName: str = participantInfo.get("summonerName")
            self.summonerId: str = participantInfo.get("summonerId")
            self.spell1Id: int = participantInfo.get("spell1Id")
            self.spell2Id: int = participantInfo.get("spell2Id")
            if self.spell2Id == 4:
                self.spell1Id, self.spell2Id = self.spell2Id, self.spell1Id
            self.gameCustomizationObjects: List[CurrentGame.CustomizationObject] = [
                CurrentGame.CustomizationObject(customizationObjectInfo)
                for customizationObjectInfo in participantInfo.get("gameCustomizationObjects")
            ]

            self.championName: str = Watcher.champion_name_from_id(self.championId)
            self.championIcon: str = FS.Emotes.Lol.Champions.get(self.championId)
            self.championImage: str = FS.Images.Lol.champion_icon(self.championId)
            self._championMastery: ChampionMastery = None

            self._summoner: Summoner = None

        @property
        def spell1Emote(self) -> str:
            return FS.Emotes.Lol.SummonerSpells.get(self.spell1Id)

        @property
        def spell2Emote(self) -> str:
            return FS.Emotes.Lol.SummonerSpells.get(self.spell2Id)

        @property
        def runes(self) -> str:
            return f"{FS.Emotes.Lol.Runes.Perks.Get(self.p)}"

        async def embeds(self) -> List[disnake.Embed]:
            embeds = [await (await self.summoner()).embed()]
            embeds.append(
                FS.Embed(
                    title=f"__**{self.championName.upper()}**__",
                    thumbnail=self.championImage,
                    color=disnake.Colour.blue(),
                    fields=[
                        {
                            "name": f"{FS.Emotes.Lol.Runes.Perks.NONE} **RUNES**",
                            "value": self.perks.text,
                            "inline": True,
                        },
                        {
                            "name": f"{FS.Emotes.FLAME} **SPELL**",
                            "value": f"> {self.spell1Emote}{self.spell2Emote}",
                            "inline": True,
                        },
                        {
                            "name": f"{FS.Emotes.Lol.MASTERIES[0]} **MASTERY**",
                            "value": "> " + (await self.championMastery()).line_description
                            if await self.championMastery()
                            else "N/A",
                            "inline": True,
                        },
                    ],
                )
            )

            return embeds

        async def championMastery(self) -> ChampionMastery:
            if self._championMastery == None:
                logging.info(f"Loading champion mastery for summoner {self.summonerName} champion {self.championName}")
                self._championMastery = await ChampionMastery.by_summoner_and_champion(self.summonerId, self.championId)
            return self._championMastery

        async def lines(self) -> Tuple[str, str]:
            league = (await (await self.summoner()).leagues()).first
            championMastery = await self.championMastery()
            return (
                f"{league.tier_emote} **{self.summonerName}**",
                f"{self.championIcon} {championMastery.emote if championMastery else FS.Emotes.Lol.MASTERIES[0]} ➖ {FS.Emotes.Lol.Runes.Perks.Get(self.perks.perkIds[0])}{FS.Emotes.Lol.Runes.Styles.Get(self.perks.perkSubStyle)} ➖ {self.spell1Emote}{self.spell2Emote}",
            )

        async def summoner(self, force_update: bool = False):
            if self._summoner == None or force_update:
                logging.info(f"Loading summoner for participant {self.summonerName}")
                self._summoner = await Summoner.by_id(self.summonerId)
            return self._summoner

    class Team:
        def __init__(self, team_id: int) -> None:
            self.bannedChampions: List[CurrentGame.BannedChampion] = []
            self.participants: List[CurrentGame.Participant] = []
            self.id: int = team_id

        @property
        def bans_block(self) -> str:
            return "\n".join([f"> `{b.name}`" for b in self.bannedChampions])

        async def embed(self) -> disnake.Embed:
            participant_tuples = [await p.lines() for p in self.participants]
            return FS.Embed(
                title=f"__**TEAM {FS.Emotes.ALPHA[self.id//100 -1]}**__",
                color=disnake.Colour.blue(),
                fields=[
                    {"name": "➖", "value": "\n".join([p[i] for p in participant_tuples]), "inline": True}
                    for i in range(len(participant_tuples[0]))
                ],
            )

        @property
        def opgg(self) -> str:
            return f"https://euw.op.gg/multi/query={''.join([p.summonerName.replace(' ','%20')+'%2C' for p in self.participants])}"

    class BannedChampion:
        def __init__(self, bannedChampionInfo: dict):
            self._bannedChampionInfo: dict = bannedChampionInfo
            self.pickTurn: int = bannedChampionInfo.get("pickTurn")
            self.championId: int = bannedChampionInfo.get("championId")
            self.teamId: int = bannedChampionInfo.get("teamId")

            self.name: str = Watcher.champion_name_from_id(self.championId) if self.championId > 0 else "-"

    def __init__(self, CurrentGameInfo: dict):
        self._currentGameInfo: dict = CurrentGameInfo
        self.gameId: int = CurrentGameInfo.get("gameId")
        self.gameType: str = CurrentGameInfo.get("gameType")
        self.gameStartTime: int = CurrentGameInfo.get("gameStartTime")
        self.mapId: int = CurrentGameInfo.get("mapId")
        self.gameLength: int = CurrentGameInfo.get("gameLength")
        self.platformId: int = CurrentGameInfo.get("platformId")
        self.gameMode: str = CurrentGameInfo.get("gameMode")
        self.bannedChampions: List[CurrentGame.BannedChampion] = [
            CurrentGame.BannedChampion(bannedChampionInfo)
            for bannedChampionInfo in CurrentGameInfo.get("bannedChampions")
        ]
        self.gameQueueConfigId: int = CurrentGameInfo.get("gameQueueConfigId")
        self.observers_key: str = (CurrentGameInfo.get("observers")).get("encryptionKey")
        self.participants: List[CurrentGame.Participant] = [
            CurrentGame.Participant(participantInfo) for participantInfo in CurrentGameInfo.get("participants")
        ]

        self.teams: List[CurrentGame.Team] = []
        for participant in self.participants:
            team = next((team for team in self.teams if team.id == participant.teamId), None)
            if team == None:
                team = CurrentGame.Team(participant.teamId)
                self.teams.append(team)
            team.participants.append(participant)

        for bannedChampion in self.bannedChampions:
            team = next((team for team in self.teams if team.id == bannedChampion.teamId), None)
            team.bannedChampions.append(bannedChampion)

        for team in self.teams:
            team.bannedChampions.sort(key=lambda b: b.pickTurn)

        self.gameLengthFormatted: str = time.strftime("%M:%S", time.gmtime(self.gameLength))

        queue: dict = self.queue_dict_from_id(self.gameQueueConfigId)
        self.mapName: str = queue.get("map")
        self.gameName: str = queue.get("description")[:-6]

        if self.mapName == "Summoner's Rift":
            self.mapImage: str = FS.Images.Lol.RIFT
            self.mapIcon: str = FS.Emotes.Lol.RIFT
        elif self.mapName == "Howling Abyss":
            self.mapImage: str = FS.Images.Lol.ARAM
            self.mapIcon: str = FS.Emotes.Lol.ARAM
        else:
            self.mapImage: str = None

    @classmethod
    async def by_summoner(cls, summoner_id: str):
        try:
            currentGameInfo = cls.get_watcher().spectator.by_summoner(cls.REGION, summoner_id)
            await asyncio.sleep(0.1)
            return CurrentGame(currentGameInfo)
        except (ApiError):
            return None

    async def embeds(self) -> List[disnake.Embed]:
        embeds = [
            FS.Embed(
                title=f"{FS.Emotes.Lol.LOGO} __**GAME EN COURS**__",
                description=f"> **Map :** `{self.mapName}`\n> **Type :** `{self.gameName}`\n> **Durée :** `{self.gameLengthFormatted}`",
                color=disnake.Colour.blue(),
                thumbnail=self.mapImage,
            )
        ]
        for team in self.teams:
            embeds.append(await team.embed())

        return embeds


class Summoner(Watcher):
    def __init__(self, summonerDto: dict):
        self._summonerDto: dict = summonerDto
        self.name: str = summonerDto.get("name")
        self.revisionDate: int = summonerDto.get("revisionDate")
        self.id: str = summonerDto.get("id")
        self.puuid = str = summonerDto.get("puuid")
        self.accountid: str = summonerDto.get("accountId")
        self.summonerLevel = summonerDto.get("summonerLevel")
        self.profileIconId = summonerDto.get("profileIconId")

        self.icon = f"https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/v1/profile-icons/{self.profileIconId}.jpg"
        self.opgg = f"https://euw.op.gg/summoners/euw/{self.name.replace(' ','%20')}"

        self._leagues: Leagues = None
        self._masteries: Masteries = None
        self._currentGame: CurrentGame = None
        self._lastGame: CurrentGame = None

    @classmethod
    async def by_name(cls, summoner_name: str):
        try:
            summonerDto: dict = cls.get_watcher().summoner.by_name(cls.REGION, summoner_name)
            await asyncio.sleep(0.1)
            return Summoner(summonerDto)
        except (ApiError):
            raise SummonerNotFound

    @classmethod
    async def by_id(cls, summoner_id: str):
        try:
            summonerDto: dict = cls.get_watcher().summoner.by_id(cls.REGION, summoner_id)
            await asyncio.sleep(0.1)
            return Summoner(summonerDto)
        except (ApiError):
            return None

    async def leagues(self, force_update: bool = False) -> Leagues:
        if self._leagues == None or force_update:
            logging.info(f"Loading leagues for {self.name}")
            self._leagues = await Leagues.by_summoner_id(self.id)
        return self._leagues

    async def masteries(self, force_update: bool = False) -> Masteries:
        if self._masteries == None or force_update:
            logging.info(f"Loading masteries for {self.name}")
            self._masteries = await Masteries.by_summoner(self.id)
        return self._masteries

    async def currentGame(self, force_update: bool = True) -> Optional[CurrentGame]:
        if self._currentGame == None or force_update:
            if force_update:
                self._lastGame = self._currentGame
            self._currentGame = await CurrentGame.by_summoner(self.id)
        return self._currentGame

    def lastGame(self) -> Optional[CurrentGame]:
        return self._lastGame

    async def embed(self, force_update: bool = False) -> disnake.Embed:
        embed = FS.Embed(
            author_name=f"{self.name.upper()}",
            description=f"{FS.Emotes.Lol.XP} **LEVEL**\n> **{self.summonerLevel}**",
            color=disnake.Colour.blue(),
            author_icon_url=self.icon,
        )
        if force_update or self._leagues == None:
            await self.leagues(force_update=force_update)
        if force_update or self._masteries == None:
            await self.masteries(force_update=force_update)
        if self._masteries:
            embed.add_field(
                name=f"{FS.Emotes.Lol.MASTERIES[0]} **MASTERIES**",
                value=(
                    "\n".join(
                        [
                            f"> {self._masteries.champions[i].line_description}"
                            for i in range(min(3, len(self._masteries.champions)))
                        ]
                    )
                    if len(self._masteries.champions) > 0
                    else f"{FS.Emotes.Lol.MASTERIES[0]} *Aucune maitrise*"
                ),
            )
        if self._leagues or force_update:
            leagues = await self.leagues()
            embed.add_field(
                name=f"{FS.Emotes.Lol.Ranks.NONE} **RANKED**",
                value=f"> **Solo/Duo :** {leagues.solo.tier_emote} **{leagues.solo.rank}** *({leagues.solo.leaguePoints} LP)*\n> **Flex :** {leagues.flex.tier_emote} **{leagues.flex.rank}** *({leagues.flex.leaguePoints} LP)*",
            )
        return embed


class ClashPlayer(Summoner):
    def __init__(self, playerDto: dict, summonerDto: dict):
        super().__init__(summonerDto)
        self._playerDto: dict = playerDto
        self.role: str = playerDto.get("role")
        self.position: str = playerDto.get("position")
        self.teamId: str = playerDto.get("teamId")
        self.summonerId: str = playerDto.get("summonerId")

        self.position_emote: str = FS.Emotes.Lol.Positions.get(self.position)

    @classmethod
    async def by_name(cls, summoner_name: str):
        return await cls.by_summoner(await super().by_name(summoner_name))

    @classmethod
    async def by_summoner(cls, summoner: Summoner):
        listPlayerDto: dict = cls.get_watcher().clash.by_summoner(cls.REGION, summoner.id)
        await asyncio.sleep(0.1)
        if len(listPlayerDto) > 0:
            return ClashPlayer(listPlayerDto[0], summoner._summonerDto)
        return None

    @classmethod
    async def by_summoner_id(cls, summoner_id: int):
        return await cls.by_summoner(await super().by_id(summoner_id))

    @classmethod
    async def by_Dto(cls, playerDto: dict):
        try:
            summonerDto: dict = cls.get_watcher().summoner.by_id(cls.REGION, playerDto.get("summonerId"))
            await asyncio.sleep(0.1)
            return ClashPlayer(playerDto, summonerDto)
        except (ApiError):
            raise SummonerNotFound


class ClashTeam(Watcher):
    def __init__(self, TeamDto: dict):
        self._TeamDto: dict = TeamDto
        self.id: str = TeamDto.get("id")
        self.tournamentId: int = TeamDto.get("tournamentId")
        self.name: str = TeamDto.get("name")
        self.iconId: int = TeamDto.get("iconId")
        self.tier: int = TeamDto.get("tier")
        self.captain: str = TeamDto.get("captain")
        self.abbreviation: str = TeamDto.get("abbreviation")
        self.icon = f"https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global/default/assets/clash/roster-logos/{self.iconId}/1.png"
        self.listPlayerDto: dict = TeamDto.get("players")
        self._players: List[ClashPlayer] = None

        self.tierFormatted: str = "I" * self.tier if self.tier != 4 else "IV"

    async def players(self, force_update: bool = False) -> List[ClashPlayer]:
        if self._players == None or force_update:
            temp: Dict[List[ClashPlayer]] = {
                "TOP": [],
                "JUNGLE": [],
                "MIDDLE": [],
                "BOTTOM": [],
                "UTILITY": [],
                "FILL": [],
                "UNSELECTED": [],
            }
            for playerDto in self.listPlayerDto:
                clash_player = await ClashPlayer.by_Dto(playerDto)
                temp[clash_player.position].append(clash_player)
            self._players = (
                temp["TOP"]
                + temp["JUNGLE"]
                + temp["MIDDLE"]
                + temp["BOTTOM"]
                + temp["UTILITY"]
                + temp["FILL"]
                + temp["UNSELECTED"]
            )

        return self._players

    @classmethod
    async def by_id(cls, team_id: str):
        try:
            teamDto: dict = cls.get_watcher().clash.by_team(cls.REGION, team_id)
            await asyncio.sleep(0.1)
            return ClashTeam(teamDto)
        except (ApiError):
            raise TeamNotFound

    @classmethod
    async def by_summoner_name(cls, summoner_name: str):
        player: ClashPlayer = await ClashPlayer.by_name(summoner_name)
        if player:
            return await cls.by_id(player.teamId)
        return None

    @classmethod
    async def by_summoner_id(cls, summoner_id: str):
        player: ClashPlayer = await ClashPlayer.by_summoner_id(summoner_id)
        if player:
            return await cls.by_id(player.teamId)
        return None

    @classmethod
    async def by_summoner(cls, summoner: Summoner):
        player: ClashPlayer = await ClashPlayer.by_summoner(summoner)
        if player:
            return await cls.by_id(player.teamId)
        return None

    async def embed(self) -> disnake.Embed:
        return FS.Embed(
            title=f"__**{self.name} [{self.abbreviation.upper()}]**__",
            description=f"Tier **{self.tierFormatted}**\n\n"
            + "\n".join(
                [
                    f"> {p.position_emote}{(await p.leagues()).first.tier_emote} {p.name}"
                    + (" " + FS.Emotes.Lol.CAPTAIN if p.summonerId == self.captain else "")
                    for p in (await self.players())
                ]
            ),
            thumbnail=self.icon,
            color=disnake.Colour.blue(),
        )

    async def opgg(self) -> str:
        return f"https://euw.op.gg/multi/query={''.join([p.name.replace(' ','%20')+'%2C' for p in (await self.players())])}"


class Champion(Watcher):
    class Image:
        def __init__(self, imageData: dict):
            self._imageData: dict = imageData
            self.full: str = (
                f"https://ddragon.leagueoflegends.com/cdn/{Watcher.VERSION}/img/champion/{imageData.get('full')}"
            )
            self.sprites: str = imageData.get("sprites")
            self.group: str = imageData.get("group")
            self.x: int = imageData.get("x")
            self.y: int = imageData.get("y")
            self.w: int = imageData.get("w")
            self.n: int = imageData.get("n")

    class Infos:
        def __init__(self, infoData: dict):
            self._infoData: dict = infoData
            self.attack: int = infoData.get("attack")
            self.defense: int = infoData.get("defense")
            self.magic: int = infoData.get("magic")
            self.difficulty: int = infoData.get("difficulty")

    class Stats:
        def __init__(self, statsData: dict):
            self._statsData: dict = statsData
            self.hp: int = statsData.get("hp")
            self.hpperlevel: int = statsData.get("hpperlevel")
            self.mp: int = statsData.get("mp")
            self.mpperlevel: int = statsData.get("mpperlevel")
            self.movespeed: int = statsData.get("movespeed")
            self.armor: int = statsData.get("armor")
            self.armorperlevel: int = statsData.get("armorperlevel")
            self.magicresistance: int = statsData.get("spellblock")
            self.magicresistanceperlevel: int = statsData.get("spellblockperlevel")
            self.attackrange: int = statsData.get("attackrange")
            self.hpregen: int = statsData.get("hpregen")
            self.hpregenperlevel: int = statsData.get("hpregenperlevel")
            self.mpregen: int = statsData.get("mpregen")
            self.mpregenperlevel: int = statsData.get("mpregenperlevel")
            self.crit: int = statsData.get("crit")
            self.critperlevel: int = statsData.get("critperlevel")
            self.attackdamage: int = statsData.get("attackdamage")
            self.attackdamageperlevel: int = statsData.get("attackdamageperlevel")
            self.attackspeedperlevel: int = statsData.get("attackspeedperlevel")
            self.attackspeed: int = statsData.get("attackspeed")

        @property
        def fields(self) -> List[dict]:
            return [
                {
                    "name": "➖",
                    "value": f"""{FS.Emotes.Lol.Stats.HEALT} ➖ **{self.hp}** + *{self.hpperlevel}/{FS.Emotes.Lol.XP}* ({round(self.hp+self.hpperlevel*18)})
                                {FS.Emotes.Lol.Stats.MANA} ➖ **{self.mp}** + *{self.mpperlevel}/{FS.Emotes.Lol.XP}* ({round(self.mp+self.mpperlevel*18)})
                                {FS.Emotes.Lol.Stats.ARMOR} ➖ **{self.armor}** + *{self.armorperlevel}/{FS.Emotes.Lol.XP}* ({round(self.armor+self.armorperlevel*18)})
                                {FS.Emotes.Lol.Stats.ATTACKSPEED} ➖ **{self.attackspeed}** + *{self.attackspeedperlevel}/{FS.Emotes.Lol.XP}* ({round(self.attackspeed+self.attackspeedperlevel*18)})
                                {FS.Emotes.Lol.Stats.CRIT} ➖ **{self.crit}** + *{self.critperlevel}/{FS.Emotes.Lol.XP}* ({round(self.crit+self.critperlevel*18)})
                                {FS.Emotes.Lol.Stats.MOVESPEED} ➖ **{self.movespeed}**""",
                    "inline": True,
                },
                {
                    "name": "➖",
                    "value": f"""{FS.Emotes.Lol.Stats.HEALTREGEN} ➖ **{self.hpregen}** + *{self.hpregenperlevel}/{FS.Emotes.Lol.XP}* ({round(self.hpregen+self.hpregenperlevel*18)})
                                {FS.Emotes.Lol.Stats.MANAREGEN} ➖ **{self.mpregen}** + *{self.mpregenperlevel}/{FS.Emotes.Lol.XP}* ({round(self.mpregen+self.mpregenperlevel*18)})
                                {FS.Emotes.Lol.Stats.MAGICRESISTE} ➖ **{self.magicresistance}** + *{self.magicresistanceperlevel}/{FS.Emotes.Lol.XP}* ({round(self.magicresistance+self.magicresistanceperlevel*18)})
                                {FS.Emotes.Lol.Stats.ATTACKDAMAGE} ➖ **{self.attackdamage}** + *{self.attackdamageperlevel}/{FS.Emotes.Lol.XP}* ({round(self.attackdamage+self.attackdamageperlevel*18)})
                                {FS.Emotes.Lol.Stats.RANGE} ➖ **{self.attackrange}**""",
                    "inline": True,
                },
            ]

    class Passive:
        class Image:
            def __init__(self, imageData: dict):
                self._imageData: dict = imageData
                self.full: str = (
                    f"https://ddragon.leagueoflegends.com/cdn/{Watcher.VERSION}/img/passive/{imageData.get('full')}"
                )
                self.sprites: str = imageData.get("sprites")
                self.group: str = imageData.get("group")
                self.x: int = imageData.get("x")
                self.y: int = imageData.get("y")
                self.w: int = imageData.get("w")
                self.n: int = imageData.get("n")

        def __init__(self, spellData: dict):
            self._spellData: dict = spellData
            self.name: str = spellData.get("name")
            self.description: str = spellData.get("description")
            self.image: Champion.Passive.Image = Champion.Passive.Image(spellData.get("image"))

        @property
        def embed(self) -> disnake.Embed:
            return FS.Embed(
                author_name=f"P - {self.name}", author_icon_url=self.image.full, description=f">  {self.description}"
            )

    class Spell:
        class Image:
            def __init__(self, imageData: dict):
                self._imageData: dict = imageData
                self.full: str = (
                    f"https://ddragon.leagueoflegends.com/cdn/{Watcher.VERSION}/img/spell/{imageData.get('full')}"
                )
                self.sprites: str = imageData.get("sprites")
                self.group: str = imageData.get("group")
                self.x: int = imageData.get("x")
                self.y: int = imageData.get("y")
                self.w: int = imageData.get("w")
                self.n: int = imageData.get("n")

        def __init__(self, spellData: dict):
            self._spellData: dict = spellData
            self.name: str = spellData.get("name")
            self.description: str = spellData.get("description")
            self.image: Champion.Spell.Image = Champion.Spell.Image(spellData.get("image"))
            self.id: str = spellData.get("id")
            self.indicator: str = self.id[-1].upper()
            self.tooltip: str = spellData.get("tooltip")
            self.leveltiplabel: List[str] = spellData.get("leveltip").get("label")
            self.maxrank: int = spellData.get("maxrank")
            self.cooldown: List[int] = spellData.get("cooldown")
            self.cooldownBurn: str = spellData.get("cooldownBurn")
            self.cost: List[int] = spellData.get("cost")
            self.costBrun: str = spellData.get("costBurn")
            self.datavalues: dict = spellData.get("datavalues")
            self.effect: List[List[int]] = spellData.get("effect")
            self.effectBurn: List[str] = spellData.get("effectBurn")
            self.vars: List[str] = spellData.get("vars")
            self.costType: str = spellData.get("costType")
            self.maxammo: str = spellData.get("maxammo")
            self.range: List[int] = spellData.get("range")
            self.rangeBrun: str = spellData.get("rangeBurn")
            self.ressource: str = spellData.get("ressource")

        @property
        def embed(self) -> disnake.Embed:
            return FS.Embed(
                author_name=f"{self.indicator} - {self.name}",
                author_icon_url=self.image.full,
                description=f"{FS.Emotes.Lol.Stats.ABILITYHASTE} **{self.cooldownBurn}** ➖ {FS.Emotes.Lol.Stats.MANA} **{self.costBrun}** ➖ {FS.Emotes.TARGET_BLUE} **{self.rangeBrun}**\n\n> {self.description}",
            )

    def __init__(self, championData: dict):
        self._championData: dict = championData
        self.id: str = championData.get("id")
        self.key: str = championData.get("key")
        self.name: str = championData.get("name")
        self.title: str = championData.get("title")
        self.image: Champion.Image = Champion.Image(championData.get("image"))
        self.lore: str = championData.get("lore")
        self.blurb: str = championData.get("blurb")
        self.ally_tips: List[str] = championData.get("allyTips")
        self.enemy_tips: List[str] = championData.get("enemyTips")
        self.tags: List[str] = championData.get("tags")
        self.partype: str = championData.get("partype")
        self.info: Champion.Infos = Champion.Infos(championData.get("info"))
        self.stats: Champion.Stats = Champion.Stats(championData.get("stats"))
        self.spells: List[Champion.Spell] = [Champion.Spell(data) for data in championData.get("spells")]
        self.passive: Champion.Passive = Champion.Passive(championData.get("passive"))
        self.recommended: list = championData.get("recommended")

    @property
    def tagsEmotes(self) -> str:
        return " ".join([FS.Emotes.Lol.Roles.get(tag) for tag in self.tags])

    @property
    def embeds(self) -> List[disnake.Embed]:
        embeds = [
            FS.Embed(
                title=f"__**{self.name.upper()}**__ ➖ {self.tagsEmotes}",
                description=f"> *{self.blurb}*",
                thumbnail=self.image.full,
                fields=self.stats.fields,
            )
        ]
        embeds.append(self.passive.embed)
        for spell in self.spells:
            embeds.append(spell.embed)
        return embeds

    @classmethod
    async def by_id(cls, id: str):
        try:
            link = f"https://ddragon.leagueoflegends.com/cdn/{cls.VERSION}/data/en_US/champion/{id}.json"
            championData: dict = (json.loads(requests.get(link).text).get("data")).get(id)
            await asyncio.sleep(0.1)
            return Champion(championData)
        except HTTPError:
            return None
