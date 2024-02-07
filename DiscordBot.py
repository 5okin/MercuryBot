# coding=utf-8

import traceback
import discord
from discord import app_commands
import os
import environment
import asyncio
from discord.ext import commands, tasks
import importlib
import sys
import io
import bot_messages as messages
from database import Database
import typing
from time import time


logger = environment.logging.getLogger("bot")
MY_GUILD = discord.Object(id=827564503930765312)

class MyClient(discord.Client):
    def __init__(self):
        #intents = discord.Intents.all()
        #intents = discord.Intents(members = True, presences = True)
        #intents.presences = True
        #intents = discord.Intents(members = True, presences = True)
        super().__init__(
            intents=discord.Intents.default(),
            activity = discord.Activity(type=discord.ActivityType.watching, name="out for free games")
        )
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        #Clear guild commands
        self.tree.clear_commands(guild=MY_GUILD)
        #Set global commands as guild commands for specific server
        #self.tree.copy_global_to(guild=MY_GUILD) 
        #await self.tree.sync(guild=MY_GUILD)
        await self.tree.sync()

client = MyClient()

shutdown_flag_is_set = False

# --- Change status --- #
status = ['Still', 'in', 'Development']


async def change_status():
    await client.wait_until_ready()
    '''
    msgs = cycle(status)

    while not client.is_closed():
        try:
            await client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=next(msgs)))
            await asyncio.sleep(3)
        except:
            pass
    '''
    await client.change_presence(
        activity=discord.Activity(type=discord.ActivityType.watching, name='out for free games'))

modules = []

def load_modules():
    """Imports and instances all the modules automagically."""

    for i in sorted(os.listdir("stores")):
        module_name = os.path.splitext(i)[0]
        module_extension = os.path.splitext(i)[1]
        if module_extension == ".py" and not module_name.startswith('_'):
            try:
                imported_module = importlib.import_module(f"stores.{module_name}")
                modules.append(getattr(imported_module, "Main")())
            except:
                print(f"Error while loading module {module_name} beacuse of {sys.exc_info()[0]}")
                print(f"{sys.exc_info()[1]}\n")
    logger.info(f"{len(modules)} modules loaded")
    if not modules:
        print("Program is exiting because no modules were loaded")
        exit()
    return modules

load_modules()

async def update(update_store=None):
    Database(modules)
    Database.connect(environment.DB)

    if update_store:
        logger.info(f"Updating store: {update_store.name}")
        if await update_store.get():
            Database.overwrite_deals(update_store.name, update_store.data)
            Database.add_image(update_store)
            if update_store.alert_flag:
                await send_games_reminder(update_store)
            else:
                print("Updated but didn't send reminders")
            update_store.alert_flag = True
        else:
            logger.info(f"No new games games to get for {update_store.name}")


async def initialize():
    # --- APP START / RESTART --- #
    # await client.wait_until_ready()

    # Connect to database (deals)
    Database(modules)
    Database.connect(environment.DB)

    for store in modules:
        # If there's data for this store on the db get it
        if store.name in Database.saved_stores():
            logger.debug(f'Getting Data from DB for {store.name}')
            store.data = Database.find(store.name)
            store.image = Database.get_image(store.name)

            # Then check if live data is different
            logger.debug("Checking if theres new data")
            await update(store)
        else:
            logger.debug(f'Scrapping data for {store.name}')
            try:
                await store.get()
                Database.overwrite_deals(store.name, store.data)
                Database.add_image(store)
            except Exception as e:
                print(str(e))


@client.event
async def on_ready():
    logger.info("Bot ready, logged in as {0.user}".format(client))

    print("Connected to servers:")
    for guild in client.guilds:
        print(guild.name)

    for guild in client.guilds:
        if guild.id == 827564503930765312:
            for channel in guild.text_channels:
                if channel.permissions_for(guild.me).send_messages:
                    await channel.send('Bot Started/Restarted')

@client.event
async def on_guild_join(guild):
    print(guild.system_channel)
    if guild.system_channel:
        await guild.system_channel.send('HI, if youre a mod you can setup the bot by using the slash commands')
    else:
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).send_messages:
                await channel.send('Hey there! this is the message i send when i join a server')
            break

@client.event
async def on_guild_remove(guild):
    Database.remove_server(guild)

async def send_games_reminder(store):
    await client.wait_until_ready()
    servers_data = Database.get_discord_servers()
    for server in servers_data:
        if server.get('channel'):
            #print(f"{server.get('channel')} has role {server.get('role')}")
            await store_messages(store.name, server.get('channel'), server.get('role'))
        else:
            #print(f"2: {server.get('channel')} has role {server.get('role')}")
            await store_messages(store.name, client.guilds.system_channel, server.get('role'))
    """
    if store:
        for guild in client.guilds:
            if guild.id == 827564503930765312:
                for channel in guild.text_channels:
                    if channel.permissions_for(guild.me).send_messages:
                        print("trying to send reminder")
                        if x.data:
                            await channel.send(f'<@&1037050135391256576> Here are the new deals on {x.name}')
                            await store_messages(store.name, channel)
                        else:
                            print("The only deal on the store was just taken down")

        channel = client.get_channel(828324732604514344)
        await store_messages(store.name, channel)

    if not store:
        for guild in client.guilds:
            if guild.id == 827564503930765312:
                for channel in guild.text_channels:
                    if channel.permissions_for(guild.me).send_messages:
                        await channel.send('Last chance to get the games')

    """
async def store_messages(command, channel, role):
    for store in modules:
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
                    channel = client.get_channel(channel)
                    default_txt = f'{store.service_name} has new free games'
                    await channel.send(default_txt + f' <@&{role}>' if role else default_txt, embed=message_to_show(store.data), view=footer_buttons(), file=file)
                #except AttributeError:
                    #print('Image not found')


@client.tree.command(name="deals", description="Choose what store you want to retrieve the current deals for.")
@app_commands.choices(store_choice=[app_commands.Choice(name=store.service_name, value=store.name) for store in modules])                     
@app_commands.describe(store_choice='Select the store you want to view')
async def store_select(interaction: discord.Interaction, store_choice: app_commands.Choice[str]):
    for store in modules:
        if store_choice.value in store.name:
            message_to_show = getattr(messages, store.name)
            if store.data:
                try:
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

                    await interaction.response.send_message(embed=message_to_show(store.data), file=file, view=footer_buttons(), ephemeral=True)
                except AttributeError:
                    print('Image not found')
                    await interaction.response.send_message(embed=message_to_show(store.data), ephemeral=True)
            else:
                await interaction.response.send_message(f"Sorry, no data at this time for {store.name}", ephemeral=True)



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


@client.tree.command(name='invite', description="Invite the bot to your server!")
async def invite(interaction: discord.Interaction):
    invite_link = 'https://discord.com/api/oauth2/authorize?client_id=827564914733350942&permissions=534723885120&scope=bot'
    url_view = discord.ui.View()
    url_view.add_item(discord.ui.Button(label=f'\u21AA', style=discord.ButtonStyle.green, disabled = True ))
    url_view.add_item(discord.ui.Button(label='🤖 Invite Link ', style=discord.ButtonStyle.blurple, url=invite_link))
    url_view.add_item(discord.ui.Button(label=f'\u21A9', style=discord.ButtonStyle.green, disabled = True ))
    await interaction.response.send_message(view=url_view)


class footer_buttons(discord.ui.View):
    def __init__(self):
        super().__init__()
        button_vote = discord.ui.Button(label='Vote', style=discord.ButtonStyle.url, emoji='🗳️', url='https://google.com')
        button_donate = discord.ui.Button(label='Donate', style=discord.ButtonStyle.url, emoji='💰',url='https://google.com')
        button_github = discord.ui.Button(label='GitHub', style=discord.ButtonStyle.url, emoji='🖥️',url='https://github.com/5okin/')
        button_invite = discord.ui.Button(label='Invite', style=discord.ButtonStyle.url, emoji='🤖',url='https://discord.com/api/oauth2/authorize?client_id=827564914733350942&permissions=534723885120&scope=bot')
        self.add_item(button_vote)
        self.add_item(button_donate)
        self.add_item(button_github)
        self.add_item(button_invite)
        

class Roles_Select(discord.ui.RoleSelect):
    def __init__(self) -> None:
        super().__init__(
            placeholder="🔍 Select a role...",
            min_values=0,
            max_values=1,
            custom_id="select_roles",
            disabled=False,
        )


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
        options=[discord.SelectOption(label=f'{store.service_name}', value=store.name) for store in modules]
        super().__init__(placeholder="Select the stores you want to receive notifications for", max_values=len(modules), min_values=0, options=options)

    async def callback(self, interaction: discord.Interaction):

        choice = []
        for store in modules:
            if store.name in self.values:
                choice.append(store.id)

        Database.insert_store_notifications([{
            'server' : interaction.guild_id,
            'notification_settings' : int("".join(str(_) for _ in choice))
        }])

        server = Database.get_discord_server(interaction.guild_id)
        embed = settings_embed(server)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


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
async def store_select(interaction: discord.Interaction):
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

        Database.add_feedback({
        'server': interaction.guild_id,
        'user': interaction.user.name,
        'timestamp': time.ctime(),
        'feedback': str(self.feedback.value)
        })

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
    #print(f'{interaction.user.desktop_status=}')
    #print(f"SERVER: {interaction.guild_id} WANTS THE UPDATE CHANNEL TO BE {role} WITH ID: {role.id}")

    settings_button = discord.ui.Button(label=f'Test notifications', style=discord.ButtonStyle.primary)
    server = Database.get_discord_server(interaction.guild_id)

    async def button_callback(interaction):

        #server = Database.get_discord_server(interaction.guild_id)
        channel = client.get_channel(server['channel'])

        embed = discord.Embed(title="⚙️ Test notification ⚙️", description=f"Notifications for games would be send to this channel", color=0x00aff4)
    
        await channel.send(f'Pinging role <@&{server["role"]}> for test' if server["role"] else '', embed=embed)
        await interaction.response.send_message("I've send a test notification message !", ephemeral=True)

    settings_button.callback = button_callback
    view = discord.ui.View()
    view.add_item(settings_button)

    embed = settings_embed(server)

    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


def settings_embed(server):
    channel = '<#'+str(server.get('channel'))+'>' if server.get('channel') else 'None'
    role = '<@&'+str(server.get('role'))+'>' if server.get('role') else 'None'

    notifications = ''
    for store in modules:
        if store.id in str(server['notification_settings']):
            notifications += f'✔️ {store.name}\n'
        else:
            notifications += f'❌ {store.name}\n'

    embed = discord.Embed(title="⚙️ Settings ⚙️", description=f"Channel: {channel}\nNotification role: {role}", color=0x00aff4)
    embed.add_field(name="🛎️ You'll receive notifications for the following stores 🛎️", value=f"{notifications}", inline=True)
    return embed


async def scrape_scheduler() -> None:
    # await client.wait_until_ready()
    tasks = set()

    for store in modules:
        tasks.add(asyncio.create_task(store.scheduler(), name=store.name))

    finished = set()
    pending = set()

    while tasks:
        logger.debug(f"{finished=} {pending=} {tasks=}")
        finished, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        # print(f"{finished=}\n{pending=}\n{tasks=}")

        for task in finished:
            store = task.result()
            logger.info("Updating:", task.result())

            try:
                await update(store)
            except Exception:
                logger.error(f'{task.result} --- FAILED ---')
                logger.error(traceback.format_exc())

            pending.add(asyncio.create_task(store.scheduler(), name=store.name))
            logger.debug(f'adding back in {task.get_name()}')

        finished.clear()
        tasks = pending.copy()
        pending.clear()

        if shutdown_flag_is_set:
            print("Braking scrape_scheduler()")
            tasks.cancel()
            break



if __name__ == "__main__":
    #load_dotenv(override=True)

    try:
        logger.info(f'Modules: ' + ', '.join([f'{store.name}' for store in modules]))

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        #loop.create_task(test_commands())
        loop.create_task(client.start(environment.DISCORD_BOT_TOKEN))
        loop.create_task(initialize())
        loop.create_task(scrape_scheduler())
        loop.run_forever()

    except KeyboardInterrupt as e:
        print("Caught keyboard interrupt. Canceling tasks...")
        shutdown_flag_is_set = True

    finally:
        print("Exiting program.")
        loop.close()
