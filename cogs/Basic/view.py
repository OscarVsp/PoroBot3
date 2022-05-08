import disnake 
from disnake import ApplicationCommandInteraction
from random import choices
from utils.embed import new_embed
from utils import data
import asyncio

class Beer(disnake.ui.View):
        
    def __init__(self, inter : ApplicationCommandInteraction):
        super().__init__(timeout=10)
        self.inter = inter
        self.counter = 1

    @disnake.ui.button(emoji = "🍺", style=disnake.ButtonStyle.primary)
    async def beer(self, button: disnake.ui.Button, interaction: disnake.MessageInteraction):
        self.counter += 1
        await interaction.response.edit_message(
            embed=new_embed(
                title="Voilà tes bières",
                description=f"{':beer:'*self.counter} \n Après {round(interaction.bot.latency,2)} secondes d'attente seulement !",
                color = data.color.gold
            ),
            view = self
        )
        
    async def on_timeout(self) -> None:
        await self.inter.delete_original_message()
        
class DiceView(disnake.ui.View):
    
    def __init__(self, inter : ApplicationCommandInteraction, nombre_de_faces : int, nombre_de_des : int):
        super().__init__(timeout=600)
        self.nbr_faces = nombre_de_faces
        self.nbr_des = nombre_de_des
        self.inter = inter       
        self.counter = 0
        self.total = 0


    @disnake.ui.button(label = "Roll", emoji = "🎲", style=disnake.ButtonStyle.primary)
    async def roll(self, button: disnake.ui.Button, interaction: disnake.MessageInteraction):
        self.counter += 1
        sortie = choices([i+1 for i in range(self.nbr_faces)],k=self.nbr_des)
        resultats = "\n".join(["".join(data.emotes.number_to_emotes(nombre,len(str(self.nbr_faces)))) for nombre in sortie])
        self.total += sum(sortie)
        await interaction.response.edit_message(
            embed = new_embed(
                title = f"🎲 Lancé de {self.nbr_des} dé(s) à {self.nbr_faces} face(s)",
                fields = {
                    'Résultats du dernier lancé :' : f"{resultats}",
                    'Total du dernier lancé :' : f"{''.join(data.emotes.number_to_emotes(sum(sortie)))}",
                    f'Total des {self.counter} lancés :' : f"{''.join(data.emotes.number_to_emotes(self.total))}"
                }
            ),
            view=self
        )
        
    @disnake.ui.button(label = "Stop", style=disnake.ButtonStyle.danger)
    async def stop_button(self, button: disnake.ui.Button, interaction: disnake.MessageInteraction):
        self.stop()
        await self.inter.delete_original_message()
        
    async def on_timeout(self) -> None:
        await self.inter.delete_original_message()