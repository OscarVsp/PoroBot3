from ast import Param
import disnake
from disnake.ext import commands
from disnake import ApplicationCommandInteraction
from random import randint,choices,sample
from utils.FastEmbed import FastEmbed
from utils.data import emotes, color
from .view import *
from .classes import *
import asyncio
from typing import List





class Tournament(commands.Cog):
    
    
    def __init__(self, bot):
        """Initialize the cog
        """
        self.bot = bot
        self.bot.tournaments_name : List[str] = []
        
    @commands.slash_command(name="tournament",     
        default_member_permissions=disnake.Permissions.all())
    async def tournament(self, inter):
        pass
    

    #command to create a new tournament
    @tournament.sub_command(
        name="2v2_roll", description="Créer un tournois 2v2 roll de 4, 5 ou 8 joueurs"
    )
    async def tournament2v2Roll(self, inter: ApplicationCommandInteraction, 
                                role : disnake.Role = commands.Param(description="Role contenant les participants"),
                                name : str = commands.Param(description="Nom du tournoi", default="Tournoi"),
                                order : str = commands.Param(description="Liste des IDs des joueurs dans l'ordre à utiliser", default="Random")):
        """Create a tournament 2v2 roll of 4, 5 or 8 players
        """
        if len(role.members) not in [4,5,8]:
            await inter.response.send_message(
                embed = FastEmbed(
                    description=f"Ce type de tournois nécessite 4, 5 ou 8 joueurs, mais le role spécifié ({role.name}) ne contient que {len(role.members)} membres.",
                    color = color.rouge,
                    ), ephemeral = True)
            return 
        players : List[Player] = [Player(p) for p in role.members]
        if order == "Random":
            ordered = False 
        else:
            ids = order.split(',')
            if len(ids) != len(players):
                await inter.response.send_message(
                    embed = FastEmbed(
                        description=f"Nombre d'IDs donnés ({len(ids)}) est différent du nombre de membre ({len(role.members)}) ayant le rôle {role.name}.",
                        color = color.rouge,
                        ),  ephemeral = True)
                return  
            ordered_players = []
            for id in ids:
                player = next((p for p in players if p.id == int(id)), None)
                if player == None:
                    await inter.response.send_message(
                        embed = FastEmbed(
                            description=f"L'ID {id} ne correspond à aucun des membres dans le role {role.name}.",
                            color = color.rouge,
                            ), ephemeral = True)
                    return 
                ordered_players.append(player)
            players = ordered_players 
            ordered = True            
        await inter.response.defer()
        self.bot.tournaments_name += [name]
        await self.bot.change_presence(activity = disnake.Activity(name=", ".join(self.bot.tournaments_name), type=disnake.ActivityType.playing))       
        new_tournament = Tournament2v2RollView(inter, self.bot, role, players, ordered, name)
        await new_tournament.makeChannels()
        await inter.edit_original_message(
            embed = FastEmbed(description=f"Tournois {name} créé.")
        )
        await asyncio.sleep(5)
        await inter.delete_original_message()
        
    

def setup(bot):
    bot.add_cog(Tournament(bot))