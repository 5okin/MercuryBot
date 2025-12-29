import io
import discord
from discord import app_commands
import clients.discord.messages as messages
from .ui_elements import FooterButtons, Settings_buttons, FeedBackView
from .embeds import settings_embed, feedback_embed
from utils import environment
from utils.database import Database

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
                message_to_show = getattr(messages, store.name)
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

    # MARK: Roles
    @app_commands.default_permissions(manage_guild=True)
    @self.tree.command(name='roles', description="Set up reaction roles for platform notifications")
    async def roles(interaction: discord.Interaction):
        '''
        Create a reaction-role message for platform selection
        '''
        # Check if the command was send in a DM
        if isinstance(interaction.channel, discord.DMChannel):
            await interaction.response.send_message("Please use the `/roles` command from the server the bot is in.", ephemeral=True)
            return

        try:
            await interaction.response.defer(thinking=True, ephemeral=True)

            # Create embed for role selection
            embed = discord.Embed(
                title="🎮 Platform Role Selection 🎮",
                description="React to this message to get notified about free games from your favorite platforms!\n\n",
                color=0x00aff4
            )

            # Build role mappings and embed description
            role_mappings = {}
            emoji_list = []

            for store in self.modules:
                # Try to find existing role or suggest role name
                role_name = f"{store.service_name} Games"
                role = discord.utils.get(interaction.guild.roles, name=role_name)

                # Create role if it doesn't exist
                if not role:
                    try:
                        role = await interaction.guild.create_role(
                            name=role_name,
                            mentionable=True,
                            reason="Auto-created for platform notifications"
                        )
                    except Exception as e:
                        logger.error(f"Failed to create role {role_name}: {e}")
                        continue

                # Get emoji for this store
                if store.discord_emoji:
                    emoji = self.get_emoji(store.discord_emoji)
                    if emoji:
                        emoji_str = str(emoji.id) if hasattr(emoji, 'id') else str(emoji)
                        role_mappings[emoji_str] = role.id
                        emoji_list.append(emoji)
                        embed.description += f"{emoji} - {role.mention}\n"

            # Send the message
            message = await interaction.channel.send(embed=embed)

            # Add reactions
            for emoji in emoji_list:
                try:
                    await message.add_reaction(emoji)
                except Exception as e:
                    logger.error(f"Failed to add reaction: {e}")

            # Store in database
            Database.set_role_message(
                server_id=interaction.guild_id,
                message_id=message.id,
                channel_id=interaction.channel.id,
                role_mappings=role_mappings
            )

            await interaction.followup.send(
                "✅ Reaction roles have been set up! Users can now react to the message to get platform roles.",
                ephemeral=True
            )

        except Exception as e:
            logger.error(f"Failed to set up roles: {e}")
            await interaction.followup.send(
                "❌ Failed to set up reaction roles. Please try again.",
                ephemeral=True
            )

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
