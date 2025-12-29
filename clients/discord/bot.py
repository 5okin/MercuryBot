import os, time, tempfile
import discord
from discord import app_commands
from utils import environment
import psutil, tracemalloc
from io import BytesIO
from utils.database import Database
import clients.discord.messages as messages
from .commands import define_commands
from .ui_elements import FooterButtons
from .events import setup_events

logger = environment.logging.getLogger("bot.discord")


class MyClient(discord.Client):
    def __init__(self, modules):
        self.modules = modules
        intents = discord.Intents.none()
        intents.guilds = True
        intents.guild_reactions = True
        self.ADMIN_USER = None
        self.DEV_GUILD = None
        super().__init__(
            intents = intents,
            max_messages=None,
            member_cache_flags=discord.MemberCacheFlags.none(),
            chunk_guilds_at_startup=False,
            activity = discord.Activity(type=discord.ActivityType.watching, name="Looking out for free games")
        )
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        self.DEV_GUILD = discord.Object(id=environment.DISCORD_DEV_GUILD) if environment.DISCORD_DEV_GUILD is not None and environment.DEVELOPMENT else None
        self.ADMIN_USER = await self.fetch_user(environment.DISCORD_ADMIN_ACC) if environment.DISCORD_ADMIN_ACC is not None else None
        setup_events(self)
        if self.DEV_GUILD:
            logger.debug("IN DEV setting up guild commands")
            self.tree.clear_commands(guild=self.DEV_GUILD)  # Clear guild commands
            # Set global commands as guild commands for specific server
            # self.tree.copy_global_to(guild=DEV_GUILD)
            define_commands(self)  # register after clearing
            await self.tree.sync(guild=self.DEV_GUILD)
        else:
            define_commands(self)  # register after clearing
            await self.tree.sync()


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
            msg = "**❌ Channel Not Found**\nThe selected channel does not exist or I can't access it\n"
            return {"has_all_permissions": False, "permission_details": PermissionDetails(), "embed": embed, "text_message": msg}

        guild = channel.guild
        required_permissions  = ['view_channel', 'send_messages', 'embed_links', 'attach_files', 'add_reactions']
        bot_permissions = channel.permissions_for(guild.me)
        has_all_permissions = all(getattr(bot_permissions, perm, False) for perm in required_permissions)

        permissions_status = [
            f"{'✅' if getattr(bot_permissions, perm, False) else '❌'} {perm.replace('_', ' ').title()}"
            for perm in required_permissions
        ]
        permissions_message = "\n".join(permissions_status)

        msg_d = "I don't have all the required permission to send messages to the selected channel."
        msg_f = "I need at least the following permissions to work correctly"
        msg_e_t = "To change channel permissions:"
        msg_e_d = "Click on the 3 dots next to the channel name / Edit channel / Permissions"
        msg_g = "Please update channel permissions and try again"
        embed = discord.Embed(title="🔒 Missing permissions 🔒", description=f"{msg_d}", color=0xff0000)
        embed.add_field(name="​", value="", inline=False)
        embed.add_field(name=msg_f, value=f"\n{permissions_message}\n", inline=False)
        embed.add_field(name="​", value="", inline=False)
        embed.add_field(name=msg_e_t, value=msg_e_d, inline=False)
        embed.set_footer(text=msg_g)

        text_message = f"**{embed.title}**\n{embed.description}\n"
        for field in embed.fields:
            text_message += f"**{field.name}** {field.value}\n"

        permission_status = {
            "has_all_permissions": has_all_permissions,
            "permission_details": bot_permissions,
            "embed": embed,
            "text_message": text_message
        }
        return permission_status


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


    def create_discord_file_from_bytesio(self, image: BytesIO, image_type: str) -> discord.File:
        """
        Writes a BytesIO image to a temporary file and returns a discord.File for sending discord notifications.

        :param image: BytesIO object containing image data
        :param image_type: Image format/extension (e.g., 'PNG', 'JPEG', 'GIF')
        :return: discord.File ready to be sent
        """
        image.seek(0)
        ext = 'jpg' if image_type.upper() == 'JPEG' else image_type.lower()

        tmp_file = tempfile.NamedTemporaryFile(suffix='.' + ext, delete=False)
        tmp_file.write(image.read())
        tmp_file.flush()
        tmp_file.seek(0)

        return discord.File(tmp_file.name, filename=f'img.{ext}')


    # MARK: send notifications
    async def send_notifications(self, store):
        await self.wait_until_ready()
        start_time = time.time()
        logger.info("Started sending Discord notifications...")
        servers_data = Database.get_discord_servers()
        servers_notified = 0
    
        image_bytes = store.image
        image_type = store.image_type

        for server in servers_data:
            file = None
            try:
                # Check server notification settings
                if str(store.id) in str(server.get('notification_settings')):
                    if server.get('channel'):
                        buffer = BytesIO(image_bytes.getvalue())
                        file = discord.File(fp=buffer, filename=f'img.{image_type.lower()}')
                        await self.store_messages(store.name, server.get('server'), server.get('channel'), server.get('role'), file)
                        servers_notified+=1
            except:
                logger.error("Failed to send notification", 
                    extra={
                    '_store_name': getattr(store, 'name', 'unknown'),
                    '_server_name':server.get('server_name', 'unknown'),
                    '_server_id': server.get('server', 'unknown'),
                    '_server_channel': server.get('channel', 'unknown'),
                    }
                )
            finally:
                if file:
                    try:
                        if file.fp:
                            file.fp.close()
                        file.close()
                    except Exception:
                        pass
                    file = None
        end_time = time.time()
        elapsed_time = end_time - start_time
        logger.info(f"Finished sending Discord notifications to {servers_notified}/{len(servers_data)} servers. Time taken: {elapsed_time:.2f} seconds")


    # MARK: store_messages
    async def store_messages(self, command, server, channel, role, file):
        for store in self.modules:
            if command in store.name:
                message_to_show = getattr(messages, store.name)
                server = self.get_guild(server)
                if store.data:

                    channel = self.get_channel(channel)

                    if role and role == server.default_role.id:
                        role = '@everyone'
                    elif role:
                        role = f' <@&{role}>'

                    default_txt = f'{store.service_name} has new free games'
                    permissions = self.check_channel_permissions(channel)

                    if permissions['has_all_permissions']:
                        # Create embed and add platform footer
                        embed = message_to_show(store)

                        # Build platform list with emojis
                        platform_text = "React to get notified for:\n"
                        emoji_list = []
                        role_mappings = {}

                        for platform in self.modules:
                            if platform.discord_emoji:
                                emoji = self.get_emoji(platform.discord_emoji)
                                if emoji:
                                    platform_text += f"{emoji} {platform.service_name}  "
                                    emoji_list.append(emoji)
                                    emoji_str = str(emoji.id) if hasattr(emoji, 'id') else str(emoji)

                                    # Find or create role for this platform
                                    role_name = f"{platform.service_name} Games"
                                    platform_role = discord.utils.get(server.roles, name=role_name)
                                    if platform_role:
                                        role_mappings[emoji_str] = platform_role.id

                        embed.add_field(name="\u200B", value=platform_text, inline=False)

                        # Send the message
                        sent_message = await channel.send(
                            default_txt + f' {role}' if role else default_txt,
                            embed=embed,
                            view=FooterButtons(),
                            file=file
                        )

                        # Add reactions
                        for emoji in emoji_list:
                            try:
                                await sent_message.add_reaction(emoji)
                            except Exception as e:
                                logger.error(f"Failed to add reaction {emoji}: {e}")

                        # Store message info in database if we have role mappings
                        if role_mappings:
                            Database.set_role_message(
                                server_id=server.id,
                                message_id=sent_message.id,
                                channel_id=channel.id,
                                role_mappings=role_mappings
                            )

                    # Check if you can send a permissions notification msg to selected channel
                    elif permissions['permission_details'].send_messages:
                        await channel.send(content=permissions['text_message'])

                    else:
                        # Check if you can send permissions notification embed or msg to system channel
                        if server.system_channel and server.system_channel.permissions_for(server.me).embed_links:
                            await server.system_channel.send(embed=permissions['embed'])
                        elif server.system_channel and server.system_channel.permissions_for(server.me).send_messages:
                            await server.system_channel.send(content=permissions['text_message'])

                        # Try sending permissions notification msg to server owner as dm
                        else:
                            owner = await self.fetch_user(server.owner_id)
                            try:
                                await owner.send(
                                    f"Hello {owner.name}, we noticed that the bot does not have all the required permissions for **{server.name}**.\n"
                                    "The bot is unable to send game notifications without these permissions !!\n"
                                    "Please update the bot settings from your server using the `/settings` command and removing and re-adding the desired channel 😊")
                            except discord.Forbidden:
                                # Try sending permissions notification msg to any server channel:
                                logger.info("Could not DM the server owner %s: %s.", owner.name, server.owner_id, extra={
                                    '_channel': channel,
                                    '_store_name': getattr(store, 'name', 'unkown'),
                                    '_server_name':server.name,
                                    '_server_id': server.id,
                                })
                                for public_channel in server.text_channels:
                                    if public_channel.permissions_for(server.me).send_messages:
                                        await public_channel.send(content=permissions['text_message'])
                                        logger.info("Send permission notification for %s to public channel", server.id)
                                        return
                                logger.warning("Failed to notify server %s for permission problems", server.id)
