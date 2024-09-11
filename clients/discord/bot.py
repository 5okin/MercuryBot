import io, os
import traceback
from datetime import datetime

import discord
from discord import app_commands

from utils.database import Database 
import clients.discord.messages as messages
from utils import environment

logger = environment.logging.getLogger(f"bot.discord")


class MyClient(discord.Client):
    def __init__(self, modules):
        self.modules = modules
        intents = discord.Intents.default()
        intents.members = True
        intents.presences = True
        self.ADMIN_USER = None
        super().__init__(
            intents = intents,
            activity = discord.Activity(type=discord.ActivityType.watching, name="out for free games")
        )
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        DEV_GUILD = discord.Object(id=environment.DISCORD_DEV_GUILD) if environment.DISCORD_DEV_GUILD is not None else None
        if environment.DEVELOPMENT and DEV_GUILD:
            logger.debug("IN DEV setting up guild commands")
            self.tree.clear_commands(guild=DEV_GUILD)  # Clear guild commands
            # Set global commands as guild commands for specific server
            # self.tree.copy_global_to(guild=DEV_GUILD)
            await self.tree.sync(guild=DEV_GUILD)
        else:
            await self.tree.sync()


    async def change_status(self):
        await self.wait_until_ready()

        await self.change_presence(
            activity=discord.Activity(type=discord.ActivityType.watching, name='out for free games'))

    # MARK: on_ready
    async def on_ready(self):
        # setup dm or logger
        self.ADMIN_USER = self.get_user(environment.DISCORD_ADMIN_ACC) if environment.DISCORD_ADMIN_ACC is not None else None

        if self.ADMIN_USER:
            await self.ADMIN_USER.send(f"**Status** {self.user} `Started/Restarted and ready`, "
                                       f"connected to {len(self.guilds)} servers")
        else:
            logger.info("%s Started/Restarted and ready, connected to %s servers", format(self.user), len(self.guilds))

        # Update server population
        for guild in self.guilds:
            Database.insert_discord_server([{
                'server': guild.id,
                # 'channel': guild.system_channel.id if guild.system_channel else None,
                # 'server_name': guild.name,
                'population' : len([member for member in guild.members if not member.bot])
            }])


        # Check if connected to all guilds stored in db, only applicable if removed while bot was offline
        servers_data = Database.get_discord_servers()
        guild_ids = [server.id for server in self.guilds]
        servers_data_ids = [server['server'] for server in servers_data]

        not_in_guilds = [server for server in servers_data_ids if server not in guild_ids]
        for guild in not_in_guilds:
            Database.remove_server(guild)

        
        # Upload animated avatar (only needs to be run once)
        if os.path.exists('avatar.gif'):
            logger.info("Found animated avatar file.")
            try:
                with open('avatar.gif', 'rb') as avatar:
                    await self.user.edit(avatar=avatar.read())
                logger.info("Animated avatar upload successful")
            except Exception as e:
                logger.info("Failed animated avatar upload %s", e)


    # MARK: on_guild_join
    async def on_guild_join(self, guild):
        msg = 'Hi, if youre a mod you can setup the bot by using the **/settings** slash command'
        if guild.system_channel:
            await guild.system_channel.send(msg)
        else:
            for channel in guild.text_channels:
                if channel.permissions_for(guild.me).send_messages:
                    await channel.send(msg)
                break

        Database.insert_discord_server([{
            'server': guild.id,
            'channel': guild.system_channel.id if guild.system_channel else None,
            'server_name': guild.name,
            'population' : len([member for member in guild.members if not member.bot])
        }])

    async def on_guild_remove(self, guild):
        Database.remove_server(guild.id)

    # MARK: store_messages
    async def store_messages(self, command, channel, role):
        for store in self.modules:
            if command in store.name:
                message_to_show = getattr(messages, store.name)
                if store.data:
                    #try:
                        if isinstance(store.image, io.BytesIO):
                            store.image.seek(0)
                            file = discord.File(store.image, filename='img.' + store.image_type.lower())
                        else:
                            img = io.BytesIO()
                            store.image.save(img, format=store.image_type)
                            img.seek(0)
                            if store.image_type == 'JPEG':
                                filetype = 'jpg'
                            else:
                                filetype = store.image_type.lower()
                            file = discord.File(img, filename='img.' + filetype)

                        channel = self.get_channel(channel)
                        default_txt = f'{store.service_name} has new free games'
                        await channel.send(default_txt + f' <@&{role}>' if role else default_txt, embed=message_to_show(store), view=footer_buttons(), file=file)
                    #except AttributeError:
                        #print('Image not found')


class footer_buttons(discord.ui.View):
    def __init__(self):
        super().__init__()
        button_vote = discord.ui.Button(label='Rate Us', style=discord.ButtonStyle.url, emoji='⭐', url='https://google.com')
        button_donate = discord.ui.Button(label='Donate', style=discord.ButtonStyle.url, emoji='💰',url='https://google.com')
        button_invite = discord.ui.Button(label='Invite', style=discord.ButtonStyle.url, emoji='🤖',url='https://discord.com/api/oauth2/authorize?client_id=827564914733350942&permissions=534723885120&scope=bot')
        self.add_item(button_vote)
        #self.add_item(button_donate)
        self.add_item(button_invite)


def setup(modules):
    client = MyClient(modules)

    # MARK: deals command
    @client.tree.command(name="deals", description="Choose what store you want to retrieve the current deals for.")
    @app_commands.choices(store_choice=[app_commands.Choice(name=store.service_name, value=store.name) for store in client.modules])                     
    @app_commands.describe(store_choice='Select the store you want to view')
    async def store_select(interaction: discord.Interaction, store_choice: app_commands.Choice[str]):

        mobile = (interaction.guild.get_member(interaction.user.id)).is_on_mobile()

        for store in client.modules:
            if store_choice.value in store.name:
                message_to_show = getattr(messages, store.name)
                if store.data:
                    image = store.image_mobile if mobile and bool(store.image_mobile) else store.image
                    if isinstance(image, io.BytesIO):
                        image.seek(0)
                        file = discord.File(image, filename='img.' + store.image_type.lower())
                        await interaction.response.send_message(embed=message_to_show(store, mobile=mobile), file=file, view=footer_buttons(), ephemeral=True)
                    else:
                        print("RIPERINO BROTHERINO")
                else:
                    await interaction.response.send_message(f"No free games on {store.name}", ephemeral=True)


    # MARK: my roles select
    class my_Roles_Select(discord.ui.Select):

        def __init__(self, interaction: discord.Interaction):
            options=[discord.SelectOption(label=f'{role.name}\t🧍{len(role.members)}') for role in interaction.guild.roles]
            super().__init__(placeholder="Select an option",max_values=1,min_values=1,options=options)

        
        async def callback(self, interaction: discord.Interaction):
            await interaction.response.send_message(content=f"Your choice is {self.values[0]}!",ephemeral=True)


    # MARK: Feedback
    @client.tree.command(description="Submit feedback")
    async def feedback(interaction: discord.Interaction):
        await interaction.response.send_modal(Feedback())


    class Feedback(discord.ui.Modal, title='Feedback'):
        feedback = discord.ui.TextInput(
            label='Tell us what you think?',
            style=discord.TextStyle.long,
            placeholder='Type your feedback here...',
            required=True,
            max_length=300,
        )

        async def on_submit(self, interaction: discord.Interaction):
            await interaction.response.send_message(f'Thanks for your feedback, {interaction.user}!', ephemeral=True)

            feedback_payload = {
            'server': interaction.guild_id,
            'user': interaction.user.name,
            'timestamp': datetime.now(),
            'feedback': str(self.feedback.value)
            }

            Database.add_feedback(feedback_payload)

            await client.get_user(362361984026542083)\
                .send(f"**Feedback**\n`{feedback_payload['feedback']}`")

        async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
            await interaction.response.send_message('Oops! Something went wrong.', ephemeral=True)
            traceback.print_exception(type(error), error, error.__traceback__)


    # MARK: Settings
    @app_commands.default_permissions(manage_guild=True)
    @client.tree.command(name='settings', description="Show bot settings like update channel and ping role")
    async def settings(interaction: discord.Interaction):
        '''
        Return bot settings
        '''
        embed = settings_embed(interaction.guild_id)
        await interaction.response.send_message(embed=embed, view=Settings_buttons(), ephemeral=True)


    def settings_embed(server):
        server = Database.get_discord_server(server)

        channel = '<#'+str(server.get('channel'))+'>' if server and server.get('channel') else 'None'
        role = '<@&'+str(server.get('role'))+'>' if server and server.get('role') else 'None'
        notifications_str = str(server['notification_settings'] if server and server.get('notification_settings') else '')

        notifications = ''
        for store in client.modules:
            if store.id in notifications_str:
                notifications += f'✔️ {store.name}\n'
            else:
                notifications += f'❌ {store.name}\n'

        embed = discord.Embed(title="⚙️ Settings ⚙️", description=f"Notification channel: {channel}\nNotification role: {role}", color=0x00aff4)
        embed.add_field(name="🛎️ You'll receive notifications for the following stores 🛎️\n", value=f"{notifications}", inline=True)
        return embed


    class Settings_buttons(discord.ui.View):
        def __init__(self):
            super().__init__()

            # Settings test notification button 
            settings_test_button = discord.ui.Button(
                label=f'Test notifications', 
                style=discord.ButtonStyle.primary
            )

            # Settings add notification channel
            settings_channel_button = discord.ui.Button(
                label=f'Set channel',
                style=discord.ButtonStyle.secondary
            )

            settings_role_button = discord.ui.Button(
                label=f'Set role',
                style=discord.ButtonStyle.secondary
            )

            settings_store_button = discord.ui.Button(
                label=f'Set stores',
                style=discord.ButtonStyle.secondary
            )   
                        
            settings_test_button.callback = self.test_settings_callback
            self.add_item(settings_test_button)


            settings_channel_button.callback = self.channel_select_callback
            self.add_item(settings_channel_button)


            settings_role_button.callback = self.settings_role_callback
            self.add_item(settings_role_button)

            settings_store_button.callback = self.settings_store_callback
            self.add_item(settings_store_button)


        # MARK: test settings callback
        async def test_settings_callback(self, interaction: discord.Integration):
            server = Database.get_discord_server(interaction.guild_id)
            if server and server.get('channel'):
                channel = client.get_channel(server['channel'])

                embed = discord.Embed(title="⚙️ Test notification ⚙️", description=f"Notifications for games will be send to this channel", color=0x00aff4)
                
                await channel.send(f'Pinging role <@&{server.get("role")}> for test' if server.get("role") else '', embed=embed)
                await interaction.response.send_message("I've send a test notification message !", ephemeral=True)
            else:
                await interaction.response.send_message("You have to set a channel first in order to test the notification", ephemeral=True)

        # MARK: channel callback
        async def channel_select_callback(self, interaction: discord.Interaction):
            class Channel_Select(discord.ui.ChannelSelect):
                def __init__(self) -> None:
                    channel_id = None
                    if Database.get_discord_server(interaction.guild_id):
                        channel_id = Database.get_discord_server(interaction.guild_id).get('channel', None)
                    
                    default = [discord.Object(id=channel_id)] if channel_id is not None else []

                    super().__init__(
                        placeholder="🔍 Select a Channel...",
                        channel_types=[discord.ChannelType.text],
                        min_values=1,
                        max_values=1,
                        custom_id="select_channel",
                        disabled=False,
                        default_values = default
                    )
                    
                async def callback(self, interaction: discord.Integration):
                    # await client.get_channel(self.values[0].id).send('This is the channel that the updates will be send to')
                    Database.insert_discord_server([{
                        'server': interaction.guild_id,
                        'channel': self.values[0].id
                        }])
                    await interaction.response.send_message(f"The update channel has been changed to {self.values[0]}", ephemeral=True)

            url_view = discord.ui.View()
            url_view.add_item(Channel_Select())
            await interaction.response.send_message(view=url_view, ephemeral=True)

        # MARK: role callback
        async def settings_role_callback(self, interaction: discord.Interaction):
            class Roles_Select(discord.ui.RoleSelect):
                def __init__(self) -> None:
                    role_id = None
                    if Database.get_discord_server(interaction.guild_id):
                        role_id = Database.get_discord_server(interaction.guild_id).get('role')
    
                    default = [discord.Object(id=role_id)] if role_id is not None else []

                    super().__init__(
                        placeholder="🔍 Select a role...",
                        min_values=0,
                        max_values=1,
                        custom_id="select_roles",
                        disabled=False,
                        default_values = default
                    )

                async def callback(self, interaction: discord.Integration):
                    role = self.values[0] if len(self.values) else None
                    Database.insert_discord_server([{
                        'server': interaction.guild_id,
                        'role': role.id if role else role
                        }])
                    if role:
                        await interaction.response.send_message(f"Ping {role.name}", ephemeral=True)
                    else:
                        await interaction.response.send_message(f"Notification will be send but no role will be pinged", 
                                                                ephemeral=True)

            url_view = discord.ui.View()
            url_view.add_item(Roles_Select())
            await interaction.response.send_message(view=url_view, ephemeral=True)

        # MARK: store callback
        async def settings_store_callback(self, interaction: discord.Interaction):   
            class Store_select(discord.ui.Select):
                def __init__(self) -> None:
                    server = Database.get_discord_server(interaction.guild_id)
                    notifications_str = str(server['notification_settings'] if server and server.get('notification_settings') else '')

                    options= [
                        discord.SelectOption(
                            default=store.id in notifications_str, 
                            label=f'{store.service_name}',
                            # description=f'Receive notifications for {store.service_name}',
                            value=store.name
                        )
                        for store in client.modules
                    ]

                    super().__init__(
                        placeholder="Select the stores you want to receive notifications for", 
                        max_values=len(client.modules), 
                        min_values=0, 
                        options=options
                    )

                async def callback(self, interaction: discord.Interaction):

                    choice = []
                    for store in client.modules:
                        if store.name in self.values:
                            choice.append(store.id)

                    if self.values:
                        stores = ' '.join(str(_+',') for _ in self.values)[:-1]
                        notification_settings = int("".join(str(_) for _ in choice))
                        await interaction.response.send_message(f"Gonna send notifications for: {stores}", ephemeral=True)
                    else:
                        await interaction.response.send_message(f"You aren't going to receive **any** notifications", ephemeral=True)
                        notification_settings = None

                    Database.insert_store_notifications([{
                        'server' : interaction.guild_id,
                        'notification_settings' : notification_settings
                    }])


            url_view = discord.ui.View()
            url_view.add_item(Store_select())
            await interaction.response.send_message(view=url_view, ephemeral=True)

    return client