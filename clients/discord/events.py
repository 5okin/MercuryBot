import os
from utils.database import Database
from datetime import datetime
from utils import environment
from .ui_elements import FooterButtons

logger = environment.logging.getLogger("bot.discord")


def setup_events(client):

    # MARK: on_ready
    @client.event
    async def on_ready():
        client.add_view(FooterButtons())
        # Check if connected to all guilds stored in db, only applicable if removed while bot was offline
        servers_data = Database.get_discord_servers()
        guild_ids = [server.id for server in client.guilds]
        servers_data_ids = [server['server'] for server in servers_data]

        not_in_guilds = [server for server in servers_data_ids if server not in guild_ids]
        for guild in not_in_guilds:
            Database.remove_server(guild)

        if client.ADMIN_USER:
            await client.ADMIN_USER.send(f"**Status** {client.user} `Started/Restarted and ready`, connected to {len(client.guilds)} servers")
        else:
            logger.info("%s Started/Restarted and ready, connected to %s servers", format(client.user), len(client.guilds))
        
        # Upload animated avatar (only needs to be run once)
        if os.path.exists('avatar.gif'):
            logger.info("Found animated avatar file.")
            try:
                with open('avatar.gif', 'rb') as avatar:
                    await client.user.edit(avatar=avatar.read())
                logger.info("Animated avatar upload successful")
            except Exception as e:
                logger.info("Failed animated avatar upload %s", e)


    # MARK: on_guild_join
    @client.event
    async def on_guild_join(guild):
        msg = 'Hi, if youre a mod you can setup the bot by using the **/settings** slash command'
        permissions = client.check_channel_permissions(guild.system_channel)
        default_channel = None

        # Try to send on join message to system channel
        if guild.system_channel and permissions['has_all_permissions']:
            await guild.system_channel.send(msg)
            default_channel = guild.system_channel.id

        # Else try to find another text channel to post in
        else:
            for channel in guild.text_channels:
                if channel.permissions_for(guild.me).send_messages:
                    await channel.send(msg)
                    default_channel = channel.id
                    break
            
        if not default_channel:
            try:
                owner = await client.fetch_user(guild.owner_id)
                await owner.send(
                    f"Hello {owner.name}, we noticed that the bot does not have permissions to view any channel for **{guild.name}**.\n"
                    "Please give permissions to the bot so that you can start the setup process !!\n"
                    "Click on the 3 dots next to a channel name / Edit channel / Permissions"
                    "After adding the bot to a channel you can run the `/settings` command to set it up how you wish !")
            except Exception as e:
                logger.warning("Could not send welcome message using any method for %s", guild.id,
                            extra={'_error:': e})
        
        Database.insert_discord_server([{
            'server': guild.id,
            'channel': default_channel,
            'server_name': guild.name,
            'joined': datetime.now(),
            'notification_settings': 1
        }])


    # MARK: on_guild_remove
    @client.event
    async def on_guild_remove(guild):
        Database.remove_server(guild.id)
        try:
            if guild.owner:
                await guild.owner.send(
                    f"Hello {guild.owner.name}, we noticed that the bot has been removed from **{guild.name}**.\n"
                    "We'd love to hear why! Please use `/feedback` to share your thoughts. 😊"
                )
        except Exception as e:
            logger.info("Failed to send feedback request to guild owner")
