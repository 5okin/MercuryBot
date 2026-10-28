import os
import discord
import asyncio
from datetime import datetime
from utils.database import Database
from .containers import feedback_container, missing_permissions_container, settings_container
from .helpers import build_deal_payload
from utils import environment

logger = environment.logging.getLogger("bot.discord")


# MARK: FooterButtons
class FooterButtons(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)
        self.add_item(RateUsButton())
        button_donate = discord.ui.Button(label='Support MercuryBot', style=discord.ButtonStyle.url, emoji='☕', url='https://ko-fi.com/mercurybot')
        button_invite = discord.ui.Button(label='Invite', style=discord.ButtonStyle.url, emoji='🤖', url='https://discord.com/oauth2/authorize?client_id=827564914733350942')
        self.add_item(button_donate)
        self.add_item(button_invite)


class RateUsButton(discord.ui.Button):
    def __init__(self) -> None:
        super().__init__(label='Rate Us', style=discord.ButtonStyle.primary, emoji='⭐', custom_id="rate_us_button")

    async def callback(self, interaction: discord.Interaction):
        if not interaction.response.is_done():
            await interaction.response.send_message(
                view=FeedBackView(),
                ephemeral=True
            )

# MARK: FeedBackButton
class FeedbackButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Submit Feedback", style=discord.ButtonStyle.primary)

    async def callback(self, interaction: discord.Interaction) -> None:
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

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)

        feedback_payload = {
            'server': interaction.guild_id,
            'user': interaction.user.name,
            'user_id': interaction.user.id,
            'timestamp': datetime.now(),
            'feedback': str(self.feedback.value)
        }
        Database.add_feedback(feedback_payload)

        if interaction.client.ADMIN_USER:
            await interaction.client.ADMIN_USER.send(f"**Feedback:**\n{interaction.client.ADMIN_USER.mention} `{feedback_payload['feedback']}`")

        await interaction.followup.send(f'Thanks for your feedback, {interaction.user}!', ephemeral=True)

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        await interaction.followup.send('Oops! Something went wrong.', ephemeral=True)
        logger.error("Failed discord command /settings", extra={'_server_id': interaction.guild_id})


class FeedBackView(discord.ui.LayoutView):
    def __init__(self):
        super().__init__()
        self.add_item(feedback_container(FeedbackButton()))


def missing_permissions_view(permissions) -> discord.ui.LayoutView:
    view = discord.ui.LayoutView(timeout=None)
    view.add_item(missing_permissions_container(permissions))
    return view

class SettingsBaseView(discord.ui.LayoutView):
    """Base class for settings screens sharing one original ephemeral response."""

    def __init__(self, timeout: int) -> None:
        super().__init__(timeout=timeout | 270)
        self.settings_interaction: discord.Interaction | None = None

    async def on_timeout(self) -> None:
        interaction = self.settings_interaction
        self.settings_interaction = None

        if interaction is None:
            return

        try:
            self.clear_items()
            self.add_item(discord.ui.Container(
                discord.ui.TextDisplay(
                    "# ⚙️ Settings ⚙️\n\u200b\n"
                    "## Session expired\n"
                    "Run `/settings` again to reopen it."
                ),
                accent_color=discord.Color.red()
            ))

            await interaction.edit_original_response(view=self)
            await asyncio.sleep(10)
            await interaction.delete_original_response()

        except discord.NotFound:
            logger.info("Settings response was already deleted.")
        except discord.HTTPException:
            logger.exception("Failed to clean up the settings response after timeout.")


async def replace_settings_view(interaction: discord.Interaction, old_view: discord.ui.LayoutView | None, new_view: SettingsBaseView ) -> None:
    if old_view is not None:
        new_view.settings_interaction = getattr(old_view, "settings_interaction", None)

        old_view.stop()

    await interaction.edit_original_response(view=new_view)


# MARK: Settings_buttons
class Settings_buttons(SettingsBaseView):
    def __init__(self, client, interaction, change_note=None) -> None:
        super().__init__(timeout=270)
        self.client = client
        self.settings_interaction = interaction

        self.add_item(settings_container(client, interaction, change_note, (
            discord.ui.ActionRow(
                self.create_channel_button(),
                self.create_role_button(),
                self.create_store_button()
            ),
            discord.ui.ActionRow(
                self.create_test_button(),
                self.create_send_all_notifications_button()
            )
        )))

    def create_test_button(self):
        button = discord.ui.Button(
            label="Test notifications",
            emoji=discord.PartialEmoji(name="test", id=os.getenv('DISCORD_TEST_BTN')),
            style=discord.ButtonStyle.primary
        )
        button.callback = self.test_settings_callback
        return button
    
    def create_send_all_notifications_button(self):
        button = discord.ui.Button(
            label="Post Selected Store Deals",
            emoji=discord.PartialEmoji(name="test", id=os.getenv('DISCORD_TEST_BTN')),
            style=discord.ButtonStyle.danger
        )
        button.callback = self.post_all_games
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
    async def channel_select_callback(self, interaction: discord.Interaction) -> None:
        await Channel_Select.handle(interaction, self.client, self)

    async def settings_role_callback(self, interaction: discord.Interaction) -> None:
        await Role_Select.handle(interaction, self.client, self)

    async def settings_store_callback(self, interaction: discord.Interaction) -> None:
        await Store_Select.handle(interaction, self.client, self)

    # MARK: test settings
    async def test_settings_callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        server = Database.get_discord_server(interaction.guild_id)
        if server and server.get('channel'):
            channel = self.client.get_channel(server['channel'])
            embed = discord.Embed(title="⚙️ Test notification ⚙️", description="Notifications for games will be send to this channel", color=0x00aff4)
            permissions = self.client.check_channel_permissions(channel)

            if permissions['has_all_permissions']:
                if server.get("role") and server.get("role") == interaction.guild_id:
                    await channel.send('Pinging role @everyone for test', embed=embed)
                elif server.get("role"):
                    await channel.send(f'Pinging role <@&{server["role"]}> for test', embed=embed)
                else:
                    await channel.send(embed=embed)
            else:
                await replace_settings_view(interaction, self, MissingPermissionsView(
                    self.client, interaction, permissions
                ))
        else:
            await interaction.followup.send("You have to set a channel first in order to test the notification", ephemeral=True)


    # MARK: Post all games
    async def post_all_games(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        server = Database.get_discord_server(interaction.guild_id)
        if server and server.get('channel'):
            channel = self.client.get_channel(server['channel'])
            permissions = self.client.check_channel_permissions(channel)

            if permissions['has_all_permissions']:
                notifications_str = str(server['notification_settings'] if server and server.get('notification_settings') else '')
                msg_send = False
                for store in self.client.modules:
                    if store.id in notifications_str:
                        payload = build_deal_payload(store, mobile=False)
                        if payload:
                            msg_send = True
                            await channel.send(embed=payload["embed"], file=payload["file"])
                if msg_send:
                    await channel.send(view=FooterButtons())

                await replace_settings_view(interaction, self, Settings_buttons(
                    self.client, interaction,
                    change_note="Selected store deals posted!"
                ))
            else:
                await replace_settings_view(interaction, self, MissingPermissionsView(
                    self.client, interaction, permissions
                ))
        else:
            await interaction.followup.send("You have to set a channel first in order to test the notification", ephemeral=True)


class MissingPermissionsView(SettingsBaseView):
    def __init__(self, client, interaction: discord.Interaction, permissions: dict) -> None:
        super().__init__(timeout=270)
        self.client = client
        self.settings_interaction = interaction
        self.add_item(missing_permissions_container(
            permissions,
            SettingsPickerBackButton(client)
        ))


class Channel_Select(discord.ui.ChannelSelect):
    @staticmethod
    async def handle(interaction: discord.Interaction, client, old_view: discord.ui.LayoutView) -> None:
        await interaction.response.defer()
        server = Database.get_discord_server(interaction.guild_id)
        channel_id = server.get('channel') if server else None
        await replace_settings_view(interaction, old_view, SettingsSelectView(
            title="Channel selection",
            description="Select the channel you want alerts to be sent to.",
            selector=Channel_Select(client, channel_id),
            client=client,
            interaction=getattr(old_view, "settings_interaction", None)
        ))

    def __init__(self, client, default=None) -> None:
        default_channel = [discord.Object(id=default)] if default is not None else []
        super().__init__(placeholder="🔍 Select a Channel...", channel_types=[discord.ChannelType.text], min_values=1, max_values=1, custom_id="select_channel", disabled=False, default_values=default_channel)
        self.client = client

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        selected_channel = interaction.guild.get_channel(self.values[0].id)
        permissions = self.client.check_channel_permissions(selected_channel)
        if not permissions['has_all_permissions']:
            await replace_settings_view(interaction, self.view, MissingPermissionsView(self.client, interaction, permissions))
            return

        Database.insert_discord_server([{
            'server': interaction.guild.id,
            'channel': selected_channel.id
        }])
        await replace_settings_view(interaction, self.view, Settings_buttons(self.client, interaction, change_note=f"Channel updated to <#{selected_channel.id}>"))


class SettingsSelectView(SettingsBaseView):
    def __init__(self, title, description, selector, client, interaction, extra_rows=(), before_selector=()) -> None:
        super().__init__(timeout=270)
        self.client = client
        self.settings_interaction = interaction
        components = [discord.ui.TextDisplay(f"## {title}\n{description}"), discord.ui.Separator()]
        components.extend(before_selector)
        components.append(discord.ui.ActionRow(selector))
        components.extend(discord.ui.ActionRow(*row) for row in extra_rows)
        components.append(discord.ui.ActionRow(SettingsPickerBackButton(client)))
        self.add_item(discord.ui.Container(*components, accent_color=discord.Color(0x00aff4)))


class SettingsPickerBackButton(discord.ui.Button):
    def __init__(self, client) -> None:
        back_button = discord.PartialEmoji(name="back", id=os.getenv('DISCORD_BACK_BTN'))
        super().__init__(label="Back", emoji=back_button, style=discord.ButtonStyle.secondary)
        self.client = client

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        await replace_settings_view(interaction, self.view, Settings_buttons(self.client, interaction))


# MARK: Role select
class Role_Select(discord.ui.Select):
    @staticmethod
    async def handle(interaction: discord.Interaction, client, old_view: discord.ui.LayoutView) -> None:
        await interaction.response.defer()
        server = Database.get_discord_server(interaction.guild_id)
        role_id = server.get('role') if server else None
        default_role = role_id if role_id is not None else None
        await replace_settings_view(interaction, old_view, SettingsSelectView(
            title="Role Notification Settings",
            description="Select a role to ping when sending alerts.\n• **Don't ping a role** – no one will be mentioned.\n• **everyone** – will bing @everyone.",
            selector=Role_Select(client, interaction, default_role),
            client=client,
            interaction=getattr(old_view, "settings_interaction", None)
        ))

    def __init__(self, client, interaction, default) -> None:
        roles_none_emoji = discord.PartialEmoji(name="rolesNone", id=os.getenv('DISCORD_ROLES_NONE'))
        roles_at_emoji = discord.PartialEmoji(name="roles", id=os.getenv('DISCORD_ROLES_AT'))
        roles_all_emoji = discord.PartialEmoji(name="rolesAll", id=os.getenv('DISCORD_ROLES_ALL'))
        options = [discord.SelectOption(label="Dont ping a role", value="None", emoji=roles_none_emoji)]
        options.extend(
            discord.SelectOption(label=role.name.replace("@", ""), value=str(role.id), emoji=roles_all_emoji if role.name == '@everyone' else roles_at_emoji)
            for role in sorted(interaction.guild.roles, key=lambda role: role.name.lower())
            if not role.managed
        )
        if default:
            for option in options:
                if option.value == str(default):
                    option.default = True
        super().__init__(placeholder="🔍 Select a role...", min_values=0, max_values=1, custom_id="select_roles", options=options[:25], disabled=False)
        self.client = client

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        selected_value = self.values[0] if len(self.values) else "None"
        role = int(selected_value) if selected_value and selected_value != "None" else None
        role_message = "I wont ping anyone"
        if role and role == interaction.guild_id:
            role_message = '@everyone'
        elif role:
            role_message = f'<@&{role}>'
        Database.insert_discord_server([{'server': interaction.guild_id, 'role': role}])
        await replace_settings_view(interaction, self.view, Settings_buttons(self.client, interaction, change_note=f"Role updated: {role_message}"))


# MARK: Store select
class Store_Select(discord.ui.Select):
    @staticmethod
    async def handle(interaction: discord.Interaction, client, old_view: discord.ui.LayoutView) -> None:
        await interaction.response.defer()
        server = Database.get_discord_server(interaction.guild_id)
        await replace_settings_view(interaction, old_view, SettingsSelectView(
            title="Store notification Settings",
            description="Select the one or more stores you want to receive alerts for.",
            selector=Store_Select(client, server),
            client=client,
            interaction=getattr(old_view, "settings_interaction", None),
            before_selector=[
                discord.ui.TextDisplay("### Notification filters\n**Skip low quality games** excludes offers flagged as low quality.\n**Skip DLC for paid games** excludes DLC when its base game is paid."),
                discord.ui.ActionRow(LowQualityToggleButton(server), PaidDlcToggleButton(server)),
                discord.ui.Separator(),
                discord.ui.TextDisplay("### Stores")
            ]
        ))

    def __init__(self, client, server) -> None:
        notifications = str(server['notification_settings'] if server and server.get('notification_settings') else '')
        options = []
        for store in client.modules:
            kwargs = {"default": store.id in notifications, "label": store.service_name, "value": store.name}
            if store.discord_emoji:
                kwargs["emoji"] = discord.PartialEmoji(name=store.name, id=store.discord_emoji)
            options.append(discord.SelectOption(**kwargs))
        super().__init__(placeholder="Select the stores you want to receive notifications for", max_values=len(client.modules), min_values=0, options=options)
        self.client = client

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        selected_stores = self.values
        store_ids = [store.id for store in self.client.modules if store.name in selected_stores]
        notification_settings = int("".join(str(store_id) for store_id in store_ids)) if store_ids else None
        Database.insert_store_notifications([{'server': interaction.guild_id, 'notification_settings': notification_settings}])
        await replace_settings_view(interaction, self.view, Settings_buttons(self.client, interaction, change_note="Stores updated!"))


# MARK: LowQualityButton
class LowQualityToggleButton(discord.ui.Button):
    def __init__(self, server):
        skip_low_quality = server['skip_low_quality'] if server and server.get('skip_low_quality') else False
        super().__init__(label=f"Skip low quality games: {'ON' if skip_low_quality else 'OFF'}", style=discord.ButtonStyle.green if skip_low_quality else discord.ButtonStyle.gray)
        self.skip_low_quality = skip_low_quality

    async def callback(self, interaction: discord.Interaction):
        self.skip_low_quality = not self.skip_low_quality
        await interaction.response.defer()
        Database.insert_store_notifications([{'server': interaction.guild_id, 'skip_low_quality': self.skip_low_quality}])
        self.label = f"Skip low quality games: {'ON' if self.skip_low_quality else 'OFF'}"
        self.style = discord.ButtonStyle.green if self.skip_low_quality else discord.ButtonStyle.gray
        await interaction.edit_original_response(view=self.view)


# MARK: PaidDlcToggleButton
class PaidDlcToggleButton(discord.ui.Button):
    def __init__(self, server):
        skip_dlc_for_paid = server['skip_dlc_for_paid'] if server and server.get('skip_dlc_for_paid') else False
        super().__init__(label=f"Skip DLC for paid games: {'ON' if skip_dlc_for_paid else 'OFF'}", style=discord.ButtonStyle.green if skip_dlc_for_paid else discord.ButtonStyle.gray)
        self.skip_dlc_for_paid = skip_dlc_for_paid

    async def callback(self, interaction: discord.Interaction):
        self.skip_dlc_for_paid = not self.skip_dlc_for_paid
        await interaction.response.defer()
        Database.insert_store_notifications([{'server': interaction.guild_id, 'skip_dlc_for_paid': self.skip_dlc_for_paid}])
        self.label = f"Skip DLC for paid base games: {'ON' if self.skip_dlc_for_paid else 'OFF'}"
        self.style = discord.ButtonStyle.green if self.skip_dlc_for_paid else discord.ButtonStyle.gray
        await interaction.edit_original_response(view=self.view)
