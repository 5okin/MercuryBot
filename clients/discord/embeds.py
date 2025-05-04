import discord
from utils.database import Database


def settings_embed(client, interaction, change_note=None):
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

    embed = discord.Embed(title="⚙️ Settings ⚙️", color=0x00aff4)
    embed.set_thumbnail(url="https://5okin.github.io/mercurybot-web/images/mercury_avatar.gif")
    embed.add_field(name="", value=f"Notification channel: {channel}\nNotification role: {role}", inline=True)
    embed.add_field(name="​", value="", inline=False)
    embed.add_field(name="🛎️ You'll receive notifications for the following stores 🛎️", value="\n", inline=False)
    embed.add_field(name="", value=f"{notifications}", inline=False)
    embed.add_field(name="​", value="", inline=False)
    if change_note:
        embed.set_footer(text=f"☑️ {change_note} ☑️")
    else:
        embed.set_footer(text="❗This message will automatically update when changes are made❗")
    return embed

    #   embed = settings_success(message=f"Role set to: {role_msg}")
def settings_success(message):
    embed = discord.Embed(
        title=f"✅ Settings Updated ✅",
        description=message,
        color=0x009933
        )
    return embed
