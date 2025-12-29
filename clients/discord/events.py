import os
import asyncio
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

        # Update server populations
        BATCH_SIZE = 500
        for i in range(0, len(client.guilds), BATCH_SIZE):
            batch = client.guilds[i:i + BATCH_SIZE]
            payloads = [{
                'server': guild.id,
                'population': guild.member_count
            } for guild in batch]
            await asyncio.to_thread(Database.insert_discord_server, payloads)
        


        # for guild in client.guilds:
        #     payload = ([{
        #         'server': guild.id,
        #         'population' : guild.member_count
        #     }])
        #     await asyncio.to_thread(Database.insert_discord_server, payload)

        # payloads =  [{
        #     'server':guild.id,
        #     'population': guild.member_count
        # } for guild in client.guilds]
        # await asyncio.to_thread(Database.insert_discord_server, payloads)

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
        msg = "Hi, if you are a mod you can setup the bot by using the slash command: **/settings** "
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
            'population': guild.member_count,
            'notification_settings': 1
        }])


    # MARK: on_guild_remove
    @client.event
    async def on_guild_remove(guild):
        if getattr(guild, "unavailable", False):
            return
        Database.remove_server(guild.id)
        try:
            if guild.owner:
                await guild.owner.send(
                    f"Hello {guild.owner.name}, we noticed that the bot has been removed from **{guild.name}**.\n"
                    "We'd love to hear why! Please use `/feedback` to share your thoughts. 😊"
                )
        except Exception as e:
            logger.info("Failed to send feedback request to guild owner")

    # MARK: on_raw_reaction_add
    @client.event
    async def on_raw_reaction_add(payload):
        # Ignore bot reactions
        if payload.user_id == client.user.id:
            return

        # Get guild and member
        guild = client.get_guild(payload.guild_id)
        if not guild:
            return

        member = guild.get_member(payload.user_id)
        if not member:
            return

        # Get the emoji string
        emoji_str = str(payload.emoji.id) if payload.emoji.id else str(payload.emoji)

        # Check if this emoji belongs to any of our platforms
        platform_role = None
        for store in client.modules:
            if store.discord_emoji:
                store_emoji_str = str(store.discord_emoji)
                if emoji_str == store_emoji_str:
                    # Find the corresponding role
                    role_name = f"{store.service_name} Games"
                    platform_role = discord.utils.get(guild.roles, name=role_name)

                    # Create role if it doesn't exist
                    if not platform_role:
                        try:
                            platform_role = await guild.create_role(
                                name=role_name,
                                mentionable=True,
                                reason="Auto-created for platform notifications"
                            )
                            logger.info(f"Created role {role_name} for {guild.name}")
                        except Exception as e:
                            logger.error(f"Failed to create role {role_name}: {e}")
                            return
                    break

        # Assign the role if we found a matching platform
        if platform_role:
            try:
                await member.add_roles(platform_role, reason="Reaction role")
                logger.info(f"Added role {platform_role.name} to {member.name}")
            except Exception as e:
                logger.error(f"Failed to add role: {e}")

    # MARK: on_raw_reaction_remove
    @client.event
    async def on_raw_reaction_remove(payload):
        # Get guild and member
        guild = client.get_guild(payload.guild_id)
        if not guild:
            return

        member = guild.get_member(payload.user_id)
        if not member:
            return

        # Get the emoji string
        emoji_str = str(payload.emoji.id) if payload.emoji.id else str(payload.emoji)

        # Check if this emoji belongs to any of our platforms
        platform_role = None
        for store in client.modules:
            if store.discord_emoji:
                store_emoji_str = str(store.discord_emoji)
                if emoji_str == store_emoji_str:
                    # Find the corresponding role
                    role_name = f"{store.service_name} Games"
                    platform_role = discord.utils.get(guild.roles, name=role_name)
                    break

        # Remove the role if we found a matching platform
        if platform_role:
            try:
                await member.remove_roles(platform_role, reason="Reaction role removed")
                logger.info(f"Removed role {platform_role.name} from {member.name}")
            except Exception as e:
                logger.error(f"Failed to remove role: {e}")
