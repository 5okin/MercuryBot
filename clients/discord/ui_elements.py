import os
import discord
import asyncio
from datetime import datetime
from utils.database import Database
from .embeds import settings_embed, settings_success, feedback_embed
from utils import environment

logger = environment.logging.getLogger("bot.discord")


# MARK: FooterButtons
class FooterButtons(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(RateUsButton())
        button_donate = discord.ui.Button(label='Donate', style=discord.ButtonStyle.url, emoji='💰',url='https://google.com')
        button_invite = discord.ui.Button(label='Invite', style=discord.ButtonStyle.url, emoji='🤖',url='https://discord.com/oauth2/authorize?client_id=827564914733350942')
        #self.add_item(button_donate)
        self.add_item(button_invite)


class RateUsButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label='Rate Us', style=discord.ButtonStyle.primary, emoji='⭐', custom_id="rate_us_button")

    async def callback(self, interaction: discord.Interaction):
        if not interaction.response.is_done():
            await interaction.response.send_message(
                embed=feedback_embed(),
                view=FeedBackView(),
                ephemeral=True
            )

# MARK: BackButton
class BackButton(discord.ui.Button):
    def __init__(self, client, settings_message):
        backBtn = discord.PartialEmoji(name="back", id=os.getenv('DISCORD_BACK_BTN'))
        super().__init__(label="Back",emoji=backBtn, style=discord.ButtonStyle.secondary)
        self.client = client
        self.settings_message = settings_message

    async def callback(self, interaction: discord.Interaction):
        await self.settings_message.edit(
            content=None,
            embed=settings_embed(self.client, interaction),
            view=Settings_buttons(self.client, settings_message=self.settings_message)
        )
        if not interaction.response.is_done():
            await interaction.response.defer()


# MARK: FeedBackButton
class FeedbackButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Submit Feedback", style=discord.ButtonStyle.primary)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(FeedbackModal())


# MARK: FeedbackModal
class FeedbackModal(discord.ui.Modal, title='Feedback'):
    feedback = discord.ui.TextInput(
        label='Tell us what you think?',
        style=discord.TextStyle.long,
        placeholder='Type your feedback here...',
        required=True,
        max_length=300,
    )

    async def on_submit(self, interaction: discord.Interaction):

        feedback_payload = {
        'server': interaction.guild_id,
        'user': interaction.user.name,
        'timestamp': datetime.now(),
        'feedback': str(self.feedback.value)
        }
        Database.add_feedback(feedback_payload)

        if interaction.client.ADMIN_USER:
            await interaction.client.ADMIN_USER.send(f"**Feedback**\n`{feedback_payload['feedback']}`")
        
        await interaction.response.send_message(f'Thanks for your feedback, {interaction.user}!', ephemeral=True)

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        await interaction.response.send_message('Oops! Something went wrong.', ephemeral=True)
        logger.error("Failed discord command /settings", extra={'_server_id': interaction.guild_id})


# MARK: FeedBackView
class FeedBackView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(discord.ui.Button(label="Vote on Top.gg", url="https://top.gg/bot/827564914733350942/vote"))
        self.add_item(discord.ui.Button(label="See on discord discoverer", url="https://discord.com/discovery/applications/827564914733350942"))
        self.add_item(discord.ui.Button(label="Join Support Server", url="https://discord.com/invite/AH8vQQJvGM"))
        self.add_item(FeedbackButton())


# MARK: Settings_buttons
class Settings_buttons(discord.ui.View):
    def __init__(self, client, settings_message=None):
        super().__init__(timeout=270)
        self.client = client
        self.settings_message = settings_message
        self.message = None

        self.add_item(self.create_test_button())
        self.add_item(self.create_channel_button())
        self.add_item(self.create_role_button())
        self.add_item(self.create_store_button())

    async def on_timeout(self):
        self.client = None
        self.settings_message = None
        
        for item in self.children:
            item.disabled = True
        try:
            if self.message:
                if self.message.embeds:
                    expired_embed = self.message.embeds[0].copy()
                    expired_embed.color = discord.Color.red()
                    text = "This session has expired. Please run the `/settings` again !"
                    expired_embed.set_footer(text="")
                    expired_embed.add_field(name="🔴🔴🔴🔴", value=f"{text}", inline=False)
                    await self.message.edit(embed=expired_embed, view=self)
                await asyncio.sleep(60)
                await self.message.delete()
                self.message = None
        except:
            logger.error("Failed to cleanup after /Settings embed")


    def create_test_button(self):
        button = discord.ui.Button(
            label="Test notifications",
            emoji=discord.PartialEmoji(name="test", id=os.getenv('DISCORD_TEST_BTN')),
            style=discord.ButtonStyle.primary
        )
        button.callback = self.test_settings_callback
        return button

    def create_channel_button(self):
        button = discord.ui.Button(
            label="​ Set channel",
            emoji=discord.PartialEmoji(name="channel", id=os.getenv('DISCORD_CHNL_BTN')),
            style=discord.ButtonStyle.secondary
        )
        button.callback = self.channel_select_callback
        return button

    def create_role_button(self):
        button = discord.ui.Button(
            label="​ Set role",
            emoji=discord.PartialEmoji(name="role", id=os.getenv('DISCORD_ROLE_BTN')),
            style=discord.ButtonStyle.secondary
        )
        button.callback = self.settings_role_callback
        return button

    def create_store_button(self):
        button = discord.ui.Button(
            label="​ Set stores",
            emoji=discord.PartialEmoji(name="stores", id=os.getenv('DISCORD_STORE_BTN')),
            style=discord.ButtonStyle.secondary
        )
        button.callback = self.settings_store_callback
        return button
        
    # MARK: settings callbacks
    async def channel_select_callback(self, interaction: discord.Interaction):
        await Channel_Select.handle(interaction, self.client, self.settings_message)

    async def settings_role_callback(self, interaction: discord.Interaction):
        await Role_Select.handle(interaction, self.client, self.settings_message)

    async def settings_store_callback(self, interaction: discord.Interaction):
        await Store_Select.handle(interaction, self.client, self.settings_message)


    # MARK: test settings
    async def test_settings_callback(self, interaction: discord.Interaction):
        server = Database.get_discord_server(interaction.guild_id)
        if server and server.get('channel'):
            channel = self.client.get_channel(server['channel'])
            embed = discord.Embed(title="⚙️ Test notification ⚙️", description=f"Notifications for games will be send to this channel", color=0x00aff4)
            
            # has_permissions, permissions_message = client.check_channel_permissions(channel)
            permissions = self.client.check_channel_permissions(channel)

            if permissions['has_all_permissions']:
                if server.get("role") and (server.get("role") == interaction.guild.default_role.id):
                    await channel.send(f'Pinging role @everyone for test', embed=embed)
                elif server.get("role"):
                    await channel.send(f'Pinging role <@&{server.get("role")}> for test', embed=embed)
                else:    
                    await channel.send(embed=embed)
                await interaction.response.defer()
            else:
                if not interaction.response.is_done():
                    await interaction.response.defer()
                await self.settings_message.edit(embed=permissions['embed'], view=Settings_buttons(self.client, self.settings_message))
        else:
            await interaction.response.send_message("You have to set a channel first in order to test the notification", ephemeral=True)

# MARK: Channel select
class Channel_Select(discord.ui.ChannelSelect):
    @staticmethod
    async def handle(interaction: discord.Interaction, client, settings_message):
        await interaction.response.defer()
        
        if Database.get_discord_server(interaction.guild_id):
            channel_id = Database.get_discord_server(interaction.guild_id).get('channel', None)  

        description_embed = discord.Embed( title="Channel selection Settings",
            description=(
                "Select the channel you want alerts to be send to.\n"
            ), color=0x00aff4
        )
        view = discord.ui.View()
        view.add_item(Channel_Select(client, settings_message, channel_id))
        view.add_item(BackButton(client, settings_message))
        await settings_message.edit(content=None, embed=description_embed, view=view)

    def __init__(self, client, settings_message=None, default=None):
        default_channel = [discord.Object(id=default)] if default is not None else []
        super().__init__(
            placeholder="🔍 Select a Channel...",
            channel_types=[discord.ChannelType.text],
            min_values=1,
            max_values=1,
            custom_id="select_channel",
            disabled=False, 
            default_values=default_channel
        )
        self.client = client
        self.settings_message = settings_message

    async def callback(self, interaction: discord.Interaction):
        selected_channel = interaction.guild.get_channel(self.values[0].id)
        permissions = self.client.check_channel_permissions(selected_channel)

        if not permissions['has_all_permissions']:
            view = discord.ui.View()
            view.add_item(Channel_Select(self.client, settings_message=self.settings_message))
            view.add_item(BackButton(self.client, self.settings_message))

            await interaction.response.edit_message(
                embed=permissions['embed'],
                view=view
            )
            return
        
        if not interaction.response.is_done():
            await interaction.response.defer()

        Database.insert_discord_server([{
            'server': interaction.guild.id,
            'channel': selected_channel.id
        }])

        embed = settings_success(message=f"Channel set to: <#{str(selected_channel.id)}>")
        await self.settings_message.edit(content=None, embed=embed, view=None)
        await asyncio.sleep(1)

        await self.settings_message.edit(
            content=None,
            embed=settings_embed(self.client, interaction, change_note="Channel updated!"),
            view=Settings_buttons(self.client, settings_message=self.settings_message)
        )


# MARK: Role select
class Role_Select(discord.ui.Select):
    @staticmethod
    async def handle(interaction: discord.Interaction, client, settings_message):
        await interaction.response.defer()
        role_id = None
        if Database.get_discord_server(interaction.guild_id):
            role_id = Database.get_discord_server(interaction.guild_id).get('role')
        default_role = role_id if role_id is not None else None

        description_embed = discord.Embed( title="Role Notification Settings",
            description=(
                "Select a role to ping when sending alerts.\n"
                "• **Don't ping a role** – no one will be mentioned.\n"
                "• **everyone** – will bing @everyone.\n"
            ), color=0x00aff4
        )
        view = discord.ui.View()
        view.add_item(Role_Select(client, interaction, settings_message, default_role))
        view.add_item(BackButton(client, settings_message))
        await settings_message.edit(content=None, embed=description_embed, view=view)

    def __init__(self, client, interaction, settings_message, default):
        rolesNoneEmoji = discord.PartialEmoji(name="rolesNone", id=os.getenv('DISCORD_ROLES_NONE'))
        rolesAtEmoji = discord.PartialEmoji(name="roles", id=os.getenv('DISCORD_ROLES_AT'))
        rolesAllEmoji = discord.PartialEmoji(name="rolesAll", id=os.getenv('DISCORD_ROLES_ALL'))

        options=[
            discord.SelectOption(label="Dont ping a role", value="None", emoji=rolesNoneEmoji),
            *[
                discord.SelectOption(
                    label = f'{(role.name).replace("@", "")}', 
                    value = role.id,
                    emoji = rolesAllEmoji if role.name == '@everyone' else rolesAtEmoji
                )
                for role in sorted(interaction.guild.roles, key=lambda r: r.name.lower())
                if not role.managed
            ]
        ]
        
        if default:
            for option in options:
                if option.value == default:
                    option.default = True

        super().__init__(
            placeholder="🔍 Select a role...",
            min_values=0,
            max_values=1,
            custom_id="select_roles",
            options=options[:25],
            disabled=False,
        )
        self.client = client
        self.interaction = interaction
        self.settings_message = settings_message

    async def callback(self, interaction: discord.Interaction):
        if not interaction.response.is_done():
            await interaction.response.defer()

        selected_value = self.values[0]
        role = int(selected_value) if selected_value and (selected_value != "None") else None
        
        role_msg = "I wont ping anyone"
        if role and (int(role) == interaction.guild.default_role.id):
            role_msg = '@everyone'
        elif role:
            role_msg = f'<@&{role}>'

        Database.insert_discord_server([{
            'server': interaction.guild_id,
            'role': role
        }])

        embed = settings_success(message=f"Role set to: {role_msg}")
        await self.settings_message.edit(content=None, embed=embed, view=None)
        await asyncio.sleep(1)

        await self.settings_message.edit(
            content=None,
            embed=settings_embed(self.client, interaction, change_note="Role updated !"),
            view=Settings_buttons(self.client, settings_message=self.settings_message)
        )


# MARK: Store select
class Store_Select(discord.ui.Select):
    @staticmethod
    async def handle(interaction: discord.Interaction, client, settings_message):
        await interaction.response.defer()

        description_embed = discord.Embed( title="Store notification Settings",
            description=(
                "Select the one or more stores you want to receive alerts for.\n"
            ), color=0x00aff4
        )
        view = discord.ui.View()
        view.add_item(Store_Select(client, interaction, settings_message))
        view.add_item(BackButton(client, settings_message))
        await settings_message.edit(content=None, embed=description_embed, view=view)

    def __init__(self, client, interaction, settings_message):
        server = Database.get_discord_server(interaction.guild_id)
        notifications_str = str(server['notification_settings'] if server and server.get('notification_settings') else '')

        options = []
        for store in client.modules:
            kwargs = {
                "default": store.id in notifications_str,
                "label": f"{store.service_name}",
                "value": store.name,
            }
            if store.discord_emoji:
                kwargs["emoji"] = discord.PartialEmoji(name=store.name, id=store.discord_emoji)

            options.append(discord.SelectOption(**kwargs))

        super().__init__(
            placeholder="Select the stores you want to receive notifications for", 
            max_values=len(client.modules), 
            min_values=0, 
            options=options
        )
        self.client = client
        self.settings_message = settings_message

    async def callback(self, interaction: discord.Interaction):
        if not interaction.response.is_done():
            await interaction.response.defer()

        selected_stores = self.values
        store_ids = [store.id for store in self.client.modules if store.name in selected_stores]

        if store_ids:
            notification_settings = int("".join(str(store_id) for store_id in store_ids))
        else:
            notification_settings = None     

        Database.insert_store_notifications([{
            'server' : interaction.guild_id,
            'notification_settings' : notification_settings
        }])
        
        # updated_selector = Store_Select(self.client, interaction, settings_message=self.settings_message)
        # view = discord.ui.View()
        # view.add_item(updated_selector)

        embed = settings_success()
        await self.settings_message.edit(content=None, embed=embed, view=None)
        
        await asyncio.sleep(1)
        await self.settings_message.edit(
            content=None,
            embed=settings_embed(self.client, interaction, change_note="Stores updated!"),
            view=Settings_buttons(self.client, settings_message=self.settings_message)
        )
