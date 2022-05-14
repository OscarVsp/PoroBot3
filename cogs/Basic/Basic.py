import disnake
from disnake.ext import commands
from disnake import ApplicationCommandInteraction
from random import randint,choices,sample
from utils.FastEmbed import FastEmbed
from utils import data
from .view import *
import asyncio


class Basic(commands.Cog):
    
    
    def __init__(self, bot):
        """Initialize the cog
        """
        self.bot = bot

    @commands.slash_command(
        description = "Commander un bière (test le ping du bot)"
    )
    async def beer(self, inter: ApplicationCommandInteraction):
        await inter.response.send_message(
            embed=FastEmbed(
                title="Voilà tes bières",
                description=f":beer:\n Après {round(self.bot.latency,2)} secondes d'attente seulement !",
                color = data.color.gold
            ),
            view = Beer(inter)
        )


    @commands.slash_command(
        description = "Nourrir le poro avec des porosnacks jusqu'à le faire exploser"
    )
    async def porosnack(self, inter: ApplicationCommandInteraction):
        await inter.response.send_message(
            embed = FastEmbed(
                description="Nourris le poro !",
                image=data.images.poros.growings[0],
                footer_text="0/10"
            ),
            view=PoroFeed(inter)
        )
        
        
    
    @commands.slash_command(
        description = "Supprimer les derniers messages du channel"
    )
    async def clear(self, inter : ApplicationCommandInteraction,
        nombre : int = commands.Param(
            description = "le nombre de message à supprimer",
            gt = 0
        )
    ):
        await inter.response.defer()
        await inter.channel.purge(limit=nombre)
        await inter.channel.send(
            embed = FastEmbed(
                description = f":broom: {nombre} messages supprimés ! :broom:"),
            delete_after=3)
        
        
 
    @commands.user_command(
        name = "Voir le lore"
    )
    async def lore(self, inter : disnake.UserCommandInteraction):
        lore_embed = get_lore_embed(inter.target.name)
        if lore_embed == False:
            await inter.response.send_message(
                embed = FastEmbed(
                    description = f"{inter.target.name} n'a pas encore de lore...\nDemande à Hyksos de l'écrire !",
                    thumbnail = data.images.poros.sweat
                    ),
                ephemeral = True
            )
        else:
                await inter.response.send_message(
                    embed = lore_embed,
                    delete_after = 60*5
                )
                    
    @commands.user_command(
        name = "Créer / éditer le lore",
        default_member_permissions=disnake.Permissions.all()
    )
    async def addlore(self, inter : disnake.UserCommandInteraction):
        await inter.response.send_modal(
            modal = loreModal(self.bot,inter.target)
        )
                
        
    
    
               

def setup(bot):
    bot.add_cog(Basic(bot))