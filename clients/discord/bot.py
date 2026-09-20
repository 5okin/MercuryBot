import asyncio, time, tempfile
import discord
from discord import app_commands
from dataclasses import dataclass
from utils import environment
import psutil, tracemalloc
from io import BytesIO
from utils.database import Database
import clients.discord.messages as messages
from .commands import define_commands
from .ui_elements import FooterButtons
from .events import setup_events

logger = environment.logging.getLogger("bot.discord")


@dataclass
class NotificationResult:
    server_id: int
    sent: bool
    permission_problems: dict | None = None


class MyClient(discord.Client):
    def __init__(self, modules) -> None:
        self.modules = modules
        intents = discord.Intents.none()
        intents.guilds = True
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

    async def setup_hook(self) -> None:
        self.DEV_GUILD = discord.Object(id=environment.DISCORD_DEV_GUILD) if environment.DISCORD_DEV_GUILD is not None and environment.DEVELOPMENT else None
        try:
            env_value = environment.DISCORD_ADMIN_ACC
            self.ADMIN_USER = await self.fetch_user(int(env_value)) if env_value is not None else None
        except discord.NotFound:
            self.ADMIN_USER = None
            logger.warning("Admin user ID not found.")

        setup_events(self)
        define_commands(self)

        if self.DEV_GUILD:
            logger.debug("IN DEV setting up guild commands")
            self.tree.clear_commands(guild=self.DEV_GUILD)  # wipe old commands
            self.tree.copy_global_to(guild=self.DEV_GUILD)  # copy commands to specified server
            await self.tree.sync(guild=self.DEV_GUILD)      # sync commands instantly
        else:
            await self.tree.sync()


    # MARK: check_permissions 
    def check_channel_permissions(self, channel) -> dict:
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
        assert self.user is not None, "Bot user is None"
        #  It is possible for system channel not to exist on a guild.
        if channel is None:
            # object to match discords API response to channel permissions
            class PermissionDetails:
                def __init__(self) -> None:
                    self.view_channel = False
                    self.send_messages = False
                    self.embed_links = False
                    self.attach_files = False

            msg = (f"The selected channel does not exist, or {self.user.mention} can't access it. "
                    "To fix this, update your settings using the `/settings` command with a valid channel, "
                    "and ensure the bot has access to it.")

            embed = discord.Embed(
                title="❌ Channel Not Found",
                description= msg,
                color=0xff0000
            )
            embed.set_thumbnail(url="https://5okin.github.io/mercurybot-web/images/mercury_avatar.gif")
            msg = f"**❌ Channel Not Found**\n{msg}\n"
            return {"has_all_permissions": False, "permission_details": PermissionDetails(), "embed": embed, "text_message": msg}

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
        msg_e_t = "To change channel permissions:"
        msg_e_d = "Click on the 3 dots next to the channel name / Edit channel / Permissions"
        msg_g = "Please update channel permissions and try again"
        embed = discord.Embed(title="🔒 Missing permissions 🔒", description=f"{msg_d}", color=0xff0000)
        embed.add_field(name="​", value="", inline=False)
        embed.add_field(name=msg_f, value=f"\n{permissions_message}\n", inline=False)
        embed.add_field(name="​", value="", inline=False)
        embed.add_field(name=msg_e_t, value=msg_e_d, inline=False)
        embed.set_footer(text=msg_g)
        embed.set_thumbnail(url="https://5okin.github.io/mercurybot-web/images/mercury_avatar.gif")

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
    
    #MARK: upload_image_to_cdn
    async def upload_image_to_cdn(self, store) -> str | None:
        buffer = BytesIO(store.image.getvalue())
        file = discord.File(fp=buffer, filename=f'img.{store.image_type.lower()}')

        if not self.ADMIN_USER:
            return None

        message = await self.ADMIN_USER.send(file=file)
        return message.attachments[0].url

    # MARK: send notifications
    async def send_notifications(self, store) -> None:
        await self.wait_until_ready()
        start_time = time.time()
        logger.info("Started sending Discord notifications...")
        servers_data = Database.get_discord_servers()
        servers_notified = 0
        notification_limit = int(environment.NOTIFICATION_BATCH_SIZE or 1)
        semaphore = asyncio.Semaphore(notification_limit)
    
        image_bytes = store.image.getvalue()
        image_type = store.image_type

        def all_new_deals_are_low_quality(games: list[dict])-> bool:
            new_deals = [
                game for game in store.data
                if game.get('newDeal')
            ]
            return (
                bool(new_deals)
                and all(game.get('type') == 'low_quality' for game in new_deals)
            )

        async def send_message(server) -> NotificationResult:
            file, buffer = None, None
            server_id = server.get('server')
            async with semaphore:
                try:
                    if store.image_cdn:
                        file = store.image_cdn
                    else:
                        buffer = BytesIO(image_bytes)
                        file = discord.File(fp=buffer, filename=f'img.{image_type.lower()}')

                    permission_problems = await self.store_messages(store.name, server_id, server.get('channel'), server.get('role'), file)
                    return NotificationResult(
                        server_id=server_id,
                        sent=permission_problems is None,
                        permission_problems=permission_problems,
                    )
                except Exception:
                    logger.error("Failed to send notification", 
                        extra={
                        '_store_name': getattr(store, 'name', 'unknown'),
                        '_server_name':server.get('server_name', 'unknown'),
                        '_server_id': server.get('server', 'unknown'),
                        '_server_channel': server.get('channel', 'unknown'),
                        }
                    )
                    return NotificationResult(server_id=server_id, sent=False)
                finally:
                    if buffer:
                        buffer.close()

        only_low_quality = all_new_deals_are_low_quality(store.data)

        servers_eligible = [
            server for server in servers_data
            if (
                store.id in str(server.get('notification_settings')) 
                and server.get('channel')
                and not (
                    server.get('skip_low_quality', False)
                    and only_low_quality
                )
            )
        ]
        if not servers_eligible:
            logger.info("No eligible servers found for notifications", extra={
                '_store_name': store.name,
                '_only_low_quality': only_low_quality,
            })
            return

        start_time_notifications = time.time()
        results = await asyncio.gather(*(send_message(server) for server in servers_eligible))
        end_time_notifications = time.time()

        successful_servers = {}
        failed_servers = {}

        for result in results:
            if result.sent:
                successful_servers[result.server_id] = result
            elif result.permission_problems is not None:
                failed_servers[result.server_id] = result.permission_problems

        notification_results = {
            "successful_servers": successful_servers,
            "failed_servers": failed_servers,
        }
        servers_notified = len(notification_results["successful_servers"])
        deferred_results = await self.send_deferred_permission_notifications(notification_results["failed_servers"])
        end_time = time.time()

        logger.info("Finished sending Discord notifications", 
            extra={
                "_store_name": store.name,
                "_total_servers": len(servers_data),
                "_total_notified": f"{servers_notified}/{len(servers_eligible)}",
                "_total_deferred": f"{len(deferred_results['successful_servers'])}/{len(notification_results['failed_servers'])}",
                "_notification_time": f"{end_time_notifications - start_time_notifications:.2f}s",
                "_total_time": f"{end_time - start_time:.2f}s",
                "_deferred_failed_server_ids": deferred_results["failed_servers"]
            }
        )


    # MARK: store_messages
    async def store_messages(self, command, server_id: int, channel_id: int, role_id: int | None, file: discord.File | None) -> dict | None:
        """Send a store notification or return permission problems.

        Parameters
        ----------
        command
            Store name used to select the notification formatter and message builder.
        server_id : int
            Discord guild ID that should receive the notification.
        channel_id : int
            Configured Discord channel ID for the notification.
        role_id : int | None
            Optional role ID to mention in the notification.
        file : discord.File | None
            Optional image file attached to the notification. It may be reused
            by the caller for multiple server sends.

        Returns
        -------
        dict | None
            Returns ``None`` when the notification is sent successfully, or
            the permission result when the configured channel lacks permissions.

        Raises
        ------
        discord.HTTPException
            If Discord rejects the notification send.
        """
        for store in self.modules:
            if command == store.name:
                message_to_show = getattr(messages, store.name, messages.default)
                server = self.get_guild(server_id)
                if store.data and server:
                    channel = self.get_channel(channel_id)

                    role = None
                    if role_id and role_id == server.default_role.id:
                        role = '@everyone'
                    elif role_id:
                        role = f' <@&{role_id}>'

                    default_txt = f'{store.service_name} has new free games'
                    permissions = self.check_channel_permissions(channel)

                    if permissions['has_all_permissions']:

                        if isinstance(file, discord.File):
                            embed = message_to_show(store)
                        else:
                            embed = message_to_show(store, file)
                            file = None

                        if isinstance(channel, discord.TextChannel):
                            await channel.send(
                                default_txt + f' {role}' if role else default_txt, 
                                embed=embed,
                                view=FooterButtons(),
                                file=file # type: ignore
                            )

                    else:
                        return permissions

    # MARK: send_deferred_permission_notifications
    async def send_deferred_permission_notifications(self, deferred_servers: dict[int, dict]) -> dict[str, list[int]]:
        """Send one permission warning for each failed notification server.

        Parameters
        ----------
        deferred_servers : dict[int, dict]
            Mapping of Discord guild IDs to permission failure details from ``store_messages``.

        Returns
        -------
        dict[str, list[int]]
            Server IDs grouped into ``successful_servers`` and
            ``failed_servers``. A server is successful when one warning route
            sends a message, and failed when no route can notify it.

        Raises
        ------
        discord.HTTPException
            If Discord rejects a warning message. A forbidden owner DM is
            handled by trying another public channel.
        """
        notified_servers = []
        failed_servers = []

        for server_id, permissions in deferred_servers.items():
            server = self.get_guild(server_id)
            if server is None:
                failed_servers.append(server_id)
                continue

            server_settings = Database.get_discord_server(server_id)
            channel = self.get_channel(server_settings.get('channel')) if server_settings else None

            if permissions['permission_details'].send_messages and isinstance(channel, discord.TextChannel):
                await channel.send(content=permissions['text_message'])
                notified_servers.append(server_id)
                continue

            if server.system_channel and server.system_channel.permissions_for(server.me).embed_links:
                await server.system_channel.send(embed=permissions['embed'])
                notified_servers.append(server_id)
                continue
            if server.system_channel and server.system_channel.permissions_for(server.me).send_messages:
                await server.system_channel.send(content=permissions['text_message'])
                notified_servers.append(server_id)
                continue

            server.owner_id = None

            if server.owner_id is None:
                logger.warning("Server owner ID is None for server %s", server.id)
                failed_servers.append(server_id)
                continue
            
            try:
                owner = await self.fetch_user(server.owner_id)
                await owner.send(
                    f"Hello {owner.name}, we noticed that the bot does not have all the required permissions for **{server.name}**.\n"
                    "The bot is unable to send game notifications without these permissions !!\n"
                    "Please update the bot settings from your server using the `/settings` command and removing and re-adding the desired channel 😊")
                notified_servers.append(server_id)
            except discord.Forbidden:
                logger.info("Could not DM the owner for server %s.", server.owner_id, extra={
                    '_channel': channel,
                    '_server_name': server.name,
                    '_server_id': server.id,
                })
                # Try sending permissions notification msg to any server channel:
                for public_channel in server.text_channels:
                    if public_channel.permissions_for(server.me).send_messages:
                        await public_channel.send(content=permissions['text_message'])
                        notified_servers.append(server_id)
                        logger.info("Send permission notification for %s to public channel", server.id)
                        break
                else:
                    failed_servers.append(server_id)
                    logger.warning("Failed to notify server %s for permission problems", server.id)
        return {
            "successful_servers": notified_servers,
            "failed_servers": failed_servers,
        }
