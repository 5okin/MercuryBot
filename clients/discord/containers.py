import discord
from utils.database import Database


def feedback_container(submit_button) -> discord.ui.Container:
    return discord.ui.Container(
        discord.ui.Section(
            discord.ui.TextDisplay("# We’d love your feedback! 💬"),
            accessory=discord.ui.Thumbnail(
                "https://5okin.github.io/mercurybot-web/images/mercury_avatar.gif",
                description="MercuryBot avatar"
            )
        ),
        discord.ui.Section(
            discord.ui.TextDisplay(
                "### top.gg\n"
                "Vote and leave feedback on top.gg so others can discover the bot!"
            ),
            accessory=discord.ui.Button(
                label="Vote on Top.gg",
                style=discord.ButtonStyle.url,
                url="https://top.gg/bot/827564914733350942/vote"
            )
        ),
        discord.ui.Separator(),
        discord.ui.Section(
            discord.ui.TextDisplay(
                "### Discord Discoverer\n"
                "Take a sneak peek right here on discord !"
            ),
            accessory=discord.ui.Button(
                label="See on discord discoverer",
                style=discord.ButtonStyle.url,
                url="https://discord.com/discovery/applications/827564914733350942"
            )
        ),
        discord.ui.Separator(),
        discord.ui.Section(
            discord.ui.TextDisplay(
                "### Join the Support server\n"
                "Need help setting up or have a question? Stop by and ask—we're here to help!"
            ),
            accessory=discord.ui.Button(
                label="Join Support Server",
                style=discord.ButtonStyle.url,
                url="https://discord.com/invite/AH8vQQJvGM"
            )
        ),
        discord.ui.Separator(),
        discord.ui.Section(
            discord.ui.TextDisplay(
                "### Support on github\n"
                "MercuryBot is Open-source and you can contribute to the project or report issues on github"
            ),
            accessory=discord.ui.Button(
                label="View on GitHub",
                style=discord.ButtonStyle.url,
                url="https://github.com/5okin/MercuryBot"
            )
        ),
        discord.ui.Separator(),
        discord.ui.Section(
            discord.ui.TextDisplay(
                "### Submit feedback\n"
                "Send Feedback straight to the developer without leaving discord"
            ),
            accessory=submit_button
        ),
        accent_color=discord.Color(0x00aff4)
    )


def settings_container(client, interaction, change_note=None, controls=()) -> discord.ui.Container:
    server = Database.get_discord_server(interaction.guild_id)
    assert server is not None, "Interaction guild is None"

    channel_id = server.get("channel")
    channel = f"<#{channel_id}>" if channel_id else "`None`"
    role_id = server.get("role")
    if role_id == interaction.guild.default_role.id:
        role = "@everyone"
    elif role_id:
        role = f"<@&{role_id}>"
    else:
        role = "`None`"

    skip_low_quality = "✅" if server.get("skip_low_quality") else "❌"
    skip_dlc_for_paid = "✅" if server.get("skip_dlc_for_paid") else "❌"
    selected_stores = str(server.get("notification_settings") or "")
    stores = "\n\n".join(
        f"{'✅' if store.id in selected_stores else '❌'} {store.service_name}"
        for store in client.modules
    )
    footer = (
        f"☑️ {change_note} ☑️"
        if change_note
        else "This message will automatically update when changes are made❗"
    )
    content = (
        f"# ⚙️ Settings ⚙️\n\u200b\n"
        f"**Notification channel:** {channel}\n"
        f"**Notification role:** {role}\n\n"
        f"**Skip low quality games:** {skip_low_quality}\n"
        f"**Skip DLC for paid base games:** {skip_dlc_for_paid}\n"
        f"### 🛎️ You'll receive notifications for the following stores 🛎️\n\n"
        f"{stores}\n\n-# {footer}"
    )

    return discord.ui.Container(
        discord.ui.Section(
            discord.ui.TextDisplay(content),
            accessory=discord.ui.Thumbnail(
                "https://5okin.github.io/mercurybot-web/images/mercury_avatar.gif",
                description="MercuryBot avatar"
            )
        ),
        discord.ui.Separator(),
        *controls,
        accent_color=discord.Color(0x00aff4)
    )


def missing_permissions_container(permissions, back_button=None) -> discord.ui.Container:
    permission_details = permissions["permission_details"]
    permission_status = "\n".join(
        f"{'✅' if permission_details.get(name, False) else '❌'} {name.replace('_', ' ').title()}"
        for name in ("view_channel", "send_messages", "embed_links", "attach_files")
    )

    components = [
        discord.ui.Section(
            discord.ui.TextDisplay(f"# {permissions['title']}\n{permissions['description']}"),
            accessory=discord.ui.Thumbnail(
                "https://5okin.github.io/mercurybot-web/images/mercury_avatar.gif",
                description="MercuryBot avatar"
            )
        ),
        discord.ui.Separator(),
        discord.ui.TextDisplay(
            f"### {permissions['permission_heading']}\n"
            f"{permission_status}\n\n"
            f"**{permissions['instruction_heading']}**\n"
            f"{permissions['instruction_description']}\n\n"
            f"-# {permissions['footer']}"
        )
    ]
    if back_button is not None:
        components.extend((
            discord.ui.Separator(),
            discord.ui.ActionRow(back_button)
        ))
    return discord.ui.Container(*components, accent_color=discord.Color(0xff0000))
