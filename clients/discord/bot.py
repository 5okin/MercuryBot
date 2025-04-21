import io, os
import traceback
from datetime import datetime

import discord
from discord import app_commands

from utils.database import Database 
import clients.discord.messages as messages
from utils import environment

logger = environment.logging.getLogger("bot.discord")


class MyClient(discord.Client):
    def __init__(self, modules):
        self.modules = modules
        intents = discord.Intents.default()
        self.ADMIN_USER = None
        self.DEV_GUILD = None
        super().__init__(
            intents = intents,
            activity = discord.Activity(type=discord.ActivityType.watching, name="out for free games")
        )
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        self.DEV_GUILD = discord.Object(id=environment.DISCORD_DEV_GUILD) if environment.DISCORD_DEV_GUILD is not None and environment.DEVELOPMENT else None
        self.ADMIN_USER = await self.fetch_user(environment.DISCORD_ADMIN_ACC) if environment.DISCORD_ADMIN_ACC is not None else None
        if self.DEV_GUILD:
            logger.debug("IN DEV setting up guild commands")
            self.tree.clear_commands(guild=self.DEV_GUILD)  # Clear guild commands
            # Set global commands as guild commands for specific server
            # self.tree.copy_global_to(guild=DEV_GUILD)
            await self.tree.sync(guild=self.DEV_GUILD)
        else:
            await self.tree.sync()


    async def change_status(self):
        await self.wait_until_ready()

        await self.change_presence(
            activity=discord.Activity(type=discord.ActivityType.watching, name='out for free games'))

    # MARK: check_permissions 
    def check_channel_permissions(self, channel):
        """
        Checks if the bot has the required permissions in a given channel and returns detailed information about the permissions.

        Args:
            channel (discord.TextChannel): The Discord text channel to check.

        Returns:
            dict: A dictionary containing:
            - 'has_all_permissions' (bool): True if the bot has all required permissions, otherwise False.
            - 'permission_details' (dict): A dictionary where keys are permissions and values are booleans indicating permissions status.
            - 'embed' (discord.Embed): An embed message listing the permissions and their statuses (✅ or ❌).

        Notes:
            - The method checks the following permissions: 'view_channel', 'send_messages', 'embed_links', 'attach_files'.
            - If the bot does not have the required permissions, the embed will list each permission's status and provide instructions for updating permissions.
            - If the channel does not exist, the method will return a message indicating so.
        """

        #  It is possible for system channel not to exist on a guild.
        if channel is None:
            # object to match discords API response to channel permissions
            class PermissionDetails:
                def __init__(self):
                        self.view_channel = False
                        self.send_messages = False
                        self.embed_links = False
                        self.attach_files = False
            embed = discord.Embed(
                title="❌ Channel Not Found",
                description="The selected channel does not exist or I can't access it",
                color=0xff0000
            )
            return {"has_all_permissions": False, "permission_details": PermissionDetails(), "embed": embed}

        guild = channel.guild
        required_permissions  = ['view_channel', 'send_messages', 'embed_links', 'attach_files']
        bot_permissions = channel.permissions_for(guild.me)
        has_all_permissions = all(getattr(bot_permissions, perm, False) for perm in required_permissions)

        permissions_status = [
            f"{'✅' if getattr(bot_permissions, perm, False) else '❌'} {perm.replace('_', ' ').title()}"
            for perm in required_permissions
        ]
        permissions_message = "\n".join(permissions_status)

        msg_d = "I don't have all the required permission to send messages to the selected channel."
        msg_f = "I need at least the following permissions to work correctly"
        msg_g = "Please update and click the set channel button again!"
        embed = discord.Embed(title="🔒 Missing permissions 🔒", description=f"{msg_d}", color=0x00aff4)
        embed.add_field(name=msg_f, value=f"\n{permissions_message}\n", inline=False)
        embed.add_field(name=msg_g, value="", inline=False)

        text_message = f"**{embed.title}**\n{embed.description}\n"
        for field in embed.fields:
            text_message += f"**{field.name}**: {field.value}\n"

        permission_status = {
            "has_all_permissions": has_all_permissions,
            "permission_details": bot_permissions,
            "embed": embed,
            "text_message": text_message
        }
        return permission_status

    # MARK: on_ready
    async def on_ready(self):
        # Check if connected to all guilds stored in db, only applicable if removed while bot was offline
        servers_data = Database.get_discord_servers()
        guild_ids = [server.id for server in self.guilds]
        servers_data_ids = [server['server'] for server in servers_data]

        not_in_guilds = [server for server in servers_data_ids if server not in guild_ids]
        for guild in not_in_guilds:
            Database.remove_server(guild)

        if self.ADMIN_USER:
            await self.ADMIN_USER.send(f"**Status** {self.user} `Started/Restarted and ready`, connected to {len(self.guilds)} servers")
        else:
            logger.info("%s Started/Restarted and ready, connected to %s servers", format(self.user), len(self.guilds))
        
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
        permissions = self.check_channel_permissions(guild.system_channel)
        default_channel = None

        # Try to send on join message to system channel
        if guild.system_channel and permissions['has_all_permissions']:
            await guild.system_channel.send(msg)
            default_channel = guild.system_channel.id

        # Else try to find another text channel to post in
        else:
            channel_found = False
            for channel in guild.text_channels:
                if channel.permissions_for(guild.me).send_messages:
                    await channel.send(msg)
                    default_channel = channel.id
                    channel_found = True
                    break
            
            if not channel_found:
                owner = await self.fetch_user(guild.owner_id)
                await owner.send(
                    f"Hello {owner.name}, we noticed that the bot does not have permissions to view any channel for **{guild.name}**.\n"
                    "Please give permissions to the bot so that you can start the setup process !!\n"
                    "After adding the bot to a channel you can run the `/settings` command to set it up how you wish !")

        Database.insert_discord_server([{
            'server': guild.id,
            'channel': default_channel,
            'server_name': guild.name,
            'joined': datetime.now(),
            'notification_settings': 1
        }])


    # MARK: on_guild_remove
    async def on_guild_remove(self, guild):
        Database.remove_server(guild.id)
        try:
            if guild.owner:
                await guild.owner.send(
                    f"Hello {guild.owner.name}, we noticed that the bot has been removed from **{guild.name}**.\n"
                    "We’d love to hear why! Please use `/feedback` to share your thoughts. 😊"
                )
        except Exception as e:
            logger.info("Failed to send feedback request to guild owner")


    #MARK: dm_logs
    async def dm_logs(self, logTitle: str, logPayload: str) -> None:
        '''
        Send logs to bot owner through dm

        Parameteres:
            logTitle (str): The title you want the dm to have.
            logPayload (str): The message you want the dm to have.
        '''
        if self.ADMIN_USER:
            await self.ADMIN_USER.send(f"**{logTitle}** {logPayload}")


    # MARK: store_messages
    async def store_messages(self, command, server, channel, role):
        for store in self.modules:
            if command in store.name:
                message_to_show = getattr(messages, store.name)
                server = self.get_guild(server)
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

                        if role and role == server.default_role.id:
                            role = '@everyone'
                        elif role:
                            role = f' <@&{role}>'

                        default_txt = f'{store.service_name} has new free games'
                        permissions = self.check_channel_permissions(channel)

                        if permissions['has_all_permissions']: 
                            await channel.send(
                                default_txt + f' {role}' if role else default_txt, 
                                embed=message_to_show(store),
                                view=footer_buttons(),
                                file=file
                            )

                        # Check if you can send a permissions notification msg
                        elif permissions['permission_details'].send_messages:
                            await channel.send(content=permissions['text_message'])

                        else:
                            permissions = self.check_channel_permissions(server.system_channel)
                            # Check if you can send to system channel
                            if permissions['permission_details'].send_messages:
                                channel = server.system_channel
                                await channel.send(content=permissions['text_message'])

                            # Nothing worked send the owner a dm
                            else:
                                owner = await self.fetch_user(server.owner_id)
                                await owner.send(
                                    f"Hello {owner.name}, we noticed that the bot does not have all the required permissions for **{server.name}**.\n"
                                    "The bot is unable to send game notifications without these permissions !!\n"
                                    "Please update the bot settings from your server using the `/settings` command and removing and re-adding the desired channel 😊")


class footer_buttons(discord.ui.View):
    def __init__(self):
        super().__init__()
        button_vote = discord.ui.Button(label='Rate Us', style=discord.ButtonStyle.url, emoji='⭐', url='https://top.gg/bot/827564914733350942')
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

        mobile = False

        # Check if the command was not send in a DM
        # if not isinstance(interaction.channel, discord.DMChannel):
        #     mobile = (interaction.guild.get_member(interaction.user.id)).is_on_mobile()
          
        for store in client.modules:
            if store_choice.value in store.name:
                message_to_show = getattr(messages, store.name)
                if store.data:
                    image = store.image
                    if isinstance(image, io.BytesIO):
                        image.seek(0)
                        file = discord.File(image, filename='img.' + store.image_type.lower())
                        await interaction.response.send_message(embed=message_to_show(store, mobile=mobile), file=file, view=footer_buttons(), ephemeral=True)
                    else:
                        print("RIPERINO BROTHERINO")
                else:
                    await interaction.response.send_message(f"No free games on {store.name}", ephemeral=True)


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


    # MARK: Settings
    @app_commands.default_permissions(manage_guild=True)
    @client.tree.command(name='settings', description="Show bot settings like update channel and ping role")
    async def settings(interaction: discord.Interaction):
        '''
        Return bot settings
        '''
        # Check if the command was send in a DM
        if isinstance(interaction.channel, discord.DMChannel):
            await interaction.response.send_message("Please use the `/settings` command from the server the bot is in.", ephemeral=True)
            return

        try:
            embed = settings_embed(interaction)
            await interaction.response.send_message(embed=embed, view=Settings_buttons(), ephemeral=True)
        except:
            logger.error("Failed discord command /settings", 
                extra={
                    '_server_id': interaction.guild_id
                }
            )


    def settings_embed(interaction):
        server = Database.get_discord_server(interaction.guild_id)

        channel = '<#'+str(server.get('channel'))+'>' if server and server.get('channel') else 'None'
        
        if (server.get('role') == interaction.guild.default_role.id):
            role = '@everyone'
        elif (server and server.get('role')):
            role = '<@&'+str(server.get('role'))+'>'
        else:
            role = '`None`'
        
        notifications_str = str(server['notification_settings'] if server and server.get('notification_settings') else '')

        notifications = ''
        for store in client.modules:
            if store.id in notifications_str:
                notifications += f'✅ {store.name}\n'
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
                
                # has_permissions, permissions_message = client.check_channel_permissions(channel)
                permissions = client.check_channel_permissions(channel)

                if permissions['has_all_permissions']:
                    if server.get("role") and (server.get("role") == interaction.guild.default_role.id):
                        await channel.send(f'Pinging role @everyone for test', embed=embed)
                    elif server.get("role"):
                        await channel.send(f'Pinging role <@&{server.get("role")}> for test', embed=embed)
                    else:    
                        await channel.send(embed=embed)
                    await interaction.response.send_message("I've send a test notification message !", ephemeral=True)
                else:
                    await interaction.response.send_message(embed=permissions['embed'], view=Settings_buttons(), ephemeral=True)
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
                    selected_channel = interaction.guild.get_channel(self.values[0].id)
                    permissions = client.check_channel_permissions(selected_channel)

                    if not permissions['has_all_permissions']:
                        await interaction.response.send_message(embed=permissions['embed'], view=Settings_buttons(), ephemeral=True)
                        return

                    Database.insert_discord_server([{
                        'server': interaction.guild_id,
                        'channel': selected_channel.id
                    }])
                    await interaction.response.send_message(f"The update channel has been changed to {self.values[0]}", ephemeral=True)

            url_view = discord.ui.View()
            url_view.add_item(Channel_Select())
            await interaction.response.send_message(view=url_view, ephemeral=True)

        # MARK: role callback
        async def settings_role_callback(self, interaction: discord.Interaction):
            role_id = None
            guild_roles = [role for role in sorted(interaction.guild.roles, key=lambda r: r.name.lower()) if not role.managed ]

            if Database.get_discord_server(interaction.guild_id):
                role_id = Database.get_discord_server(interaction.guild_id).get('role')


            async def handle_role_selection(interaction: discord.Integration, selected_value):
                """
                Handles the role selection process and updates the database accordingly.

                Parameters:
                - interaction (discord.Interaction): The interaction object representing the user's action.
                - selected_value (str): The selected role ID as a string, or "None" if no role was selected.

                Behavior:
                - Converts the selected role ID to an integer (if valid).
                - Updates the database with the selected role for the server.
                - Sends a response indicating whether a role will be pinged.
                """
                role = int(selected_value) if selected_value and (selected_value != "None") else None
                role_msg = "Notification will be send but no role will be pinged"
                
                if role and (int(role) == interaction.guild.default_role.id):
                    role_msg = '@everyone'
                elif role:
                    role_msg = f'<@&{role}>'

                Database.insert_discord_server([{
                    'server': interaction.guild_id,
                    'role': role
                }])

                await interaction.response.send_message(f"Ping {role_msg}" if role else role_msg, ephemeral=True)

            class Custom_Roles_Select(discord.ui.Select):
                async def callback(self, interaction: discord.Integration):
                    if not self.values : self.values.append("None")
                    await handle_role_selection(interaction, self.values[0])
                
                def __init__(self) -> None:
                    options=[
                        discord.SelectOption(label="Dont ping a role", value="None"),
                        *[
                            discord.SelectOption(
                                label=f'{(role.name).replace("@", "")}', 
                                value=role.id
                            )
                            for role in sorted(interaction.guild.roles, key=lambda r: r.name.lower())
                            if not role.managed
                        ]
                    ]

                    default = role_id if role_id is not None else None

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

            class Default_Roles_Select(discord.ui.RoleSelect):
                async def callback(self, interaction: discord.Integration):
                    role = self.values[0].id if len(self.values) else "None"
                    logger.warning("Server %s has more then 25 role options used Default Roles Select", 
                                   interaction.guild_id, 
                                   extra = {'_selected_role' : role})
                    await handle_role_selection(interaction, role)

                def __init__(self) -> None:

                    default = [discord.Object(id=role_id)] if role_id is not None else []
                    super().__init__(
                        placeholder="🔍 Select a role...",
                        min_values=0,
                        max_values=1,
                        custom_id="select_roles",
                        disabled=False,
                        default_values = default
                    )


            url_view = discord.ui.View()

            if len(guild_roles)+2 < 25:
                url_view.add_item(Custom_Roles_Select())
            else:
                url_view.add_item(Default_Roles_Select())
    
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