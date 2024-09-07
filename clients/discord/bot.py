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

    async def on_ready(self):
        self.ADMIN_USER = self.get_user(environment.DISCORD_ADMIN_ACC) if environment.DISCORD_ADMIN_ACC is not None else None

        if self.ADMIN_USER:
            await self.ADMIN_USER.send(f"**Status** {self.user} `Started/Restarted and ready`, "
                                       f"connected to {len(self.guilds)} servers")
        else:
            logger.info("%s Started/Restarted and ready, connected to %s servers", format(self.user), len(self.guilds))

        # for guild in self.guilds:
        #     Database.insert_discord_server([{
        #         'server': guild.id,
        #         'server_name': guild.name,
        #         'population' : len([member for member in guild.members if not member.bot])
        #     }])

        # Upload animated avatar
        if os.path.exists('avatar.gif'):
            logger.info("Found animated avatar file.")
            try:
                with open('avatar.gif', 'rb') as avatar:
                    await self.user.edit(avatar=avatar.read())
                logger.info("Animated avatar upload successful")
            except Exception as e:
                logger.info("Failed animated avatar upload %s", e)


    async def on_guild_join(self, guild):
        print(guild.system_channel)
        if guild.system_channel:
            await guild.system_channel.send('Hi, if youre a mod you can setup the bot by using the **/settings** slash command')
        else:
            for channel in guild.text_channels:
                if channel.permissions_for(guild.me).send_messages:
                    await channel.send('Hey there! this is the message i send when i join a server')
                break


    async def on_guild_remove(self, guild):
        Database.remove_server(guild)

    
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

                        # await channel.send(embed = message_to_show(store.data), file=file)
                        channel = self.get_channel(channel)
                        default_txt = f'{store.service_name} has new free games'
                        await channel.send(default_txt + f' <@&{role}>' if role else default_txt, embed=message_to_show(store), view=footer_buttons(), file=file)
                    #except AttributeError:
                        #print('Image not found')




class Roles_Select(discord.ui.RoleSelect):
    def __init__(self) -> None:
        super().__init__(
            placeholder="🔍 Select a role...",
            min_values=0,
            max_values=1,
            custom_id="select_roles",
            disabled=False,
        )


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
                        print("RIPERINO BROTHERINO_1")
                else:
                    await interaction.response.send_message(f"No free games on {store.name}", ephemeral=True)


    #@app_commands.is_owner()
    #@app_commands.checks.has_permissions(administrator=True)
    @app_commands.default_permissions(manage_guild=True)
    @client.tree.command(name='updates-channel', description="Channel that receives automatic deal notifications")
    @app_commands.describe(channel='Ha1')
    async def channel_select(interaction: discord.Interaction, channel: discord.TextChannel):
        await channel.send('This is the channel that the updates will be send to')
        await interaction.response.send_message(f"The update channel has been changed to {channel.name}", ephemeral=True)
        print(type(channel))
        print(f"{channel=}\n{channel.id=}")
        
        Database.insert_discord_server([{
        'server': interaction.guild_id,
        'channel': channel.id}])


    async def callback(self, interaction: discord.Interaction):

        embed = discord.Embed(
                color=0x00aff4, 
                description=f"Every time i have an update i will send a notification to:\n\nChannel: <#{interaction.guild.system_channel.id}>"
                            f"\nPinging role: {'<@&'+ str(self.values[0].id)+'>' if len(self.values) else ' None'}"
                            f"\n\nTo change the channel that receives the updates use the updates-channel slash command"
                )
            
        await interaction.response.send_message(embed=embed, ephemeral=True)

        Database.insert_discord_server([{
            'server': interaction.guild_id,
            'channel': interaction.guild.system_channel.id,
            'role': self.values[0].id if len(self.values) else None
        }])


    class select_store(discord.ui.Select):
        def __init__(self, interaction: discord.Interaction):
            options=[discord.SelectOption(label=f'{store.service_name}', value=store.name) for store in client.modules]
            super().__init__(placeholder="Select the stores you want to receive notifications for", max_values=len(client.modules), min_values=0, options=options)

        async def callback(self, interaction: discord.Interaction):

            choice = []
            for store in client.modules:
                if store.name in self.values:
                    choice.append(store.id)

            Database.insert_store_notifications([{
                'server' : interaction.guild_id,
                'notification_settings' : int("".join(str(_) for _ in choice))
            }])

            embed = settings_embed(interaction.guild_id)
            
            await interaction.response.send_message(embed=embed, view=settings_test_button(), ephemeral=True)


    class my_Roles_Select(discord.ui.Select):

        def __init__(self, interaction: discord.Interaction):
            options=[discord.SelectOption(label=f'{role.name}\t🧍{len(role.members)}') for role in interaction.guild.roles]
            super().__init__(placeholder="Select an option",max_values=1,min_values=1,options=options)

        
        async def callback(self, interaction: discord.Interaction):
            await interaction.response.send_message(content=f"Your choice is {self.values[0]}!",ephemeral=True)



    @app_commands.default_permissions(manage_guild=True)
    @client.tree.command(name='role-ping', description="Select role to ping")
    async def role_select(interaction: discord.Interaction):
        print(f'{interaction=}')
        url_view = discord.ui.View()
        url_view.add_item(Roles_Select())
        await interaction.response.send_message(view=url_view, ephemeral=True)


    @app_commands.default_permissions(manage_guild=True)
    @client.tree.command(name='store-notifications', description="Select the stores you want to receive notifications for")
    async def store_notification(interaction: discord.Interaction):
        url_view = discord.ui.View()
        url_view.add_item(select_store(interaction))
        await interaction.response.send_message(view=url_view, ephemeral=True)


    @app_commands.default_permissions(manage_guild=True)
    @client.tree.command(name='role-ping-test', description="Select role to ping")
    async def role_select2(interaction: discord.Interaction):
        url_view = discord.ui.View()
        url_view.add_item(my_Roles_Select(interaction))
        print('\n')
        for role in interaction.guild.roles:
            print(f'{role} {role.members}')
        await interaction.response.send_message(view=url_view, ephemeral=True)


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


    @client.tree.command(description="Submit feedback")
    async def feedback(interaction: discord.Interaction):
        await interaction.response.send_modal(Feedback())


    @app_commands.default_permissions(manage_guild=True)
    @client.tree.command(name='settings', description="Show bot settings like update channel and ping role")
    async def settings(interaction: discord.Interaction):
        '''
        Return bot settings
        '''
        '''
        settings_button = discord.ui.Button(label=f'Test notifications', style=discord.ButtonStyle.primary)
        server = Database.get_discord_server(interaction.guild_id)

        async def button_callback(interaction):

            server = Database.get_discord_server(interaction.guild_id)
            channel = client.get_channel(server['channel'])

            embed = discord.Embed(title="⚙️ Test notification ⚙️", description=f"Notifications for games would be send to this channel", color=0x00aff4)
        
            await channel.send(f'Pinging role <@&{server["role"]}> for test' if server["role"] else '', embed=embed)
            await interaction.response.send_message("I've send a test notification message !", ephemeral=True)

        settings_button.callback = button_callback
        view = discord.ui.View()
        view.add_item(settings_button)
        '''
        #view = discord.ui.View()
        #view.add_item(settings_test_button)
        embed = settings_embed(interaction.guild_id)

        await interaction.response.send_message(embed=embed, view=settings_test_button(), ephemeral=True)


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

        embed = discord.Embed(title="⚙️ Settings ⚙️", description=f"Channel: {channel}\nNotification role: {role}", color=0x00aff4)
        embed.add_field(name="🛎️ You'll receive notifications for the following stores 🛎️\n", value=f"{notifications}", inline=True)
        return embed


    class settings_test_button(discord.ui.View):
        def __init__(self):
            super().__init__()
            self.settings_button = discord.ui.Button(label=f'Test notifications', style=discord.ButtonStyle.primary)
            self.add_item(self.settings_button)
            self.settings_button.callback = self.settings_button_callback

        async def settings_button_callback(self, interaction: discord.Integration):
            server = Database.get_discord_server(interaction.guild_id)
            if server and server.get('channel'):
                channel = client.get_channel(server['channel'])

                embed = discord.Embed(title="⚙️ Test notification ⚙️", description=f"Notifications for games would be send to this channel", color=0x00aff4)
                
                await channel.send(f'Pinging role <@&{server.get("role")}> for test' if server.get("role") else '', embed=embed)
                await interaction.response.send_message("I've send a test notification message !", ephemeral=True)
            else:
                await interaction.response.send_message("You have to set a channel first in order to test the notification", ephemeral=True)

    return client