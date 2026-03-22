import discord
from utils.database import Database


def settings_embed(client, interaction, change_note=None) -> discord.Embed:
    server = Database.get_discord_server(interaction.guild_id)
    channel = '<#'+str(server.get('channel'))+'>' if server and server.get('channel') else '`None`'
    assert server is not None, "Interaction guild is None"
    
    if (server.get('role') == interaction.guild.default_role.id):
        role = '@everyone'
    elif (server and server.get('role')):
        role = '<@&'+str(server.get('role'))+'>'
    else:
        role = '`None`'
    
    notifications_str = str(server['notification_settings'] if server and server.get('notification_settings') else '')
    notifications = ''
    for store in client.modules:
        status = '✅' if store.id in notifications_str else '❌'
        notifications += f'{status} {store.service_name}\n\n'

    embed = discord.Embed(title="⚙️ Settings ⚙️", color=0x00aff4)
    embed.set_thumbnail(url="https://5okin.github.io/mercurybot-web/images/mercury_avatar.gif")
    embed.add_field(name="\u200B", value=f"**Notification channel:** {channel}\n**Notification role:** {role}", inline=True)
    embed.add_field(name="\u200B", value="", inline=False)
    embed.add_field(name="🛎️ You'll receive notifications for the following stores 🛎️", value="\n", inline=False)
    embed.add_field(name="\u200B", value=f"{notifications}", inline=False)
    embed.add_field(name="\u200B", value="", inline=False)
    if change_note:
        embed.set_footer(text=f"☑️ {change_note} ☑️")
    else:
        embed.set_footer(text="This message will automatically update when changes are made❗")
    return embed


def settings_success(message="") -> discord.Embed:
    embed = discord.Embed(
        title=f"✅ Settings Updated ✅",
        description=message,
        color=0x009933
        )
    return embed


def feedback_embed():
    embed = discord.Embed(title="We’d love your feedback! 💬", color=0x00aff4)
    embed.set_thumbnail(url="https://5okin.github.io/mercurybot-web/images/mercury_avatar.gif")
    embed.add_field(name="top.gg", value="Vote and leave feedback on top.gg so others can discover the bot!", inline=True)
    embed.add_field(name="Discord Discoverer", value="Take a sneak peek right here on discord !", inline=False)
    embed.add_field(name="Submit feedback", value="Send Feedback straight to the developer without leaving discord", inline=False)
    embed.add_field(name="Join the Support server", value="Need help setting up or have a question? Stop by and ask—we're here to help!", inline=False)
    embed.add_field(name="Support on github", value="MercuryBot is [Open-source at github!](https://github.com/5okin/MercuryBot)", inline=False)
    return embed
