import io
import discord
from discord import app_commands
import clients.discord.messages as messages
from .ui_elements import FooterButtons, Settings_buttons, FeedBackView
from .embeds import settings_embed, feedback_embed
from utils import environment

logger = environment.logging.getLogger("bot.discord")


def define_commands(self):

    # MARK: deals command
    @self.tree.command(name="deals", description="Choose what store you want to retrieve the current deals for.")
    @app_commands.choices(store_choice=[app_commands.Choice(name=store.service_name, value=store.name) for store in self.modules])
    @app_commands.describe(store_choice='Select the store you want to view')
    async def store_select(interaction: discord.Interaction, store_choice: app_commands.Choice[str]):

        mobile = False
        # Check if the command was not send in a DM
        # if not isinstance(interaction.channel, discord.DMChannel):
        #     mobile = (interaction.guild.get_member(interaction.user.id)).is_on_mobile()

        for store in self.modules:
            if store_choice.value in store.name:
                message_to_show = getattr(messages, store.name, messages.default)
                if store.data and  any(game.get('activeDeal', False) for game in store.data):
                    image = store.image
                    if isinstance(image, io.BytesIO):
                        image.seek(0)
                        file = discord.File(image, filename='img.' + store.image_type.lower())
                        await interaction.response.send_message(embed=message_to_show(store, mobile=mobile), file=file, view=FooterButtons(), ephemeral=True)
                    else:
                        logger.error("Image isnt BytesIO", extra={'_store_data': store.data})
                else:
                    await interaction.response.send_message(f"No free games on {store.name}", ephemeral=True)


    # MARK: Feedback
    @self.tree.command(description="Submit feedback")
    async def feedback(interaction: discord.Interaction):
        await interaction.response.send_message(embed=feedback_embed(), view=FeedBackView(), ephemeral=True)

    # MARK: Settings
    @app_commands.default_permissions(manage_guild=True)
    @self.tree.command(name='settings', description="Show bot settings like update channel and ping role")
    async def settings(interaction: discord.Interaction):
        '''
        Return bot settings
        '''
        # Check if the command was send in a DM
        if isinstance(interaction.channel, discord.DMChannel):
            await interaction.response.send_message("Please use the `/settings` command from the server the bot is in.", ephemeral=True)
            return

        try:
            if not interaction.response.is_done():
                await interaction.response.defer(thinking=True, ephemeral=True)

            view = Settings_buttons(self)
            embed = settings_embed(self, interaction)
            message = await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            view.message = message
            await message.edit(view=Settings_buttons(self, settings_message=message))
        except:
            logger.warning("Failed discord command /settings", 
                extra={
                    '_server_id': interaction.guild_id
                }
            )
