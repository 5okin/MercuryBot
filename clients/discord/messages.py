import discord


footer = ""

def epic(store, mobile=False):
    # f = open('./data/epic_database.json')
    # data_json = json.load(f)

    # zima = 0x16b8f3
    embed_var = discord.Embed(title="🕹️ Epic Free Games 🕹️", description="", color=0x00aff4)
    embed_var.set_image(url="attachment://img.gif")
    # embed_var.set_image(url= "https://i.imgur.com/s3GlK9a.gif")

    all_freenow = ''
    all_upnext = ''

    for deal in store.data:
        title = deal['title']
        link = deal['url']

        if deal['activeDeal']:
            now_end_date = store.get_date(deal, 'end', True)
            # all_freenow += "• " + f"[**{title}**]({link})\n‎ [Launcher](com.epicgames.launcher://store/p/tomb-raider)\n"
            # all_freenow += "• " + f"[**{title}**]({link})\n‎" + "<com.epicgames.launcher://store/p/tomb-raider>\n"
            all_freenow += "• " + f"[**{title}**]({link})\n‎"

        else:
            start_date = store.get_date(deal, 'start')
            end_date = store.get_date(deal, 'end')
            # start_date = get_date(deal['startDate'])
            # end_date = get_date(deal['endDate'])

            game_details = f"Free: {start_date} - {end_date}"
            all_upnext += "• " + f"[**{title}**]({link})‎\n"

    embed_var.add_field(name=f'\u200B\n**Free Now**', value=f"Until: {now_end_date}\n\n{all_freenow}", inline=True)
    if (not mobile):
        embed_var.add_field(name=f'\u200B\n**Up Next**', value=f"‎‎‎{game_details}\n\n{all_upnext}‎", inline=True)
    embed_var.set_footer(text=footer)

    return embed_var


def gog(store, mobile=False):
    # zima = 0x16b8f3
    embed_var = discord.Embed(title="🕹️ GOG 🕹️", description=f'\u200B\n**Free Now**', color=0x00aff4)

    for deal in store.data:
        title = deal['title']
        link = deal['url']
        end_date = store.get_date(deal, 'end', True)
        embed_var.add_field(name=f'\u200B\n', value=f"[**{title}**]({link})\nUntil: {end_date}", inline=False)

    embed_var.set_image(url="attachment://img.gif")
    embed_var.set_footer(text=footer)
    return embed_var


def steam(store, mobile=False):
    embed_var = discord.Embed(title="🕹️ Steam 🕹️", description=f'\u200B\n**Free Now**', color=0x00aff4)

    for deal in store.data:
        title = deal['title']
        link = deal['url']
        end_date = store.get_date(deal, 'end', True)

        embed_var.add_field(
            name = f'\u200B\n',
            value = f"• [**{title}**]({link})\nUntil: {end_date}" if end_date else f"• [**{title}**]({link})",
            inline = False
)

    embed_var.set_image(url="attachment://img.gif")
    embed_var.set_footer(text=footer)
    return embed_var


def psplus(store, mobile=False):
    embed_var = discord.Embed(title="🕹️ Play Station Plus 🕹️", description="", color=0x00aff4)

    for deal in store.data:
        title = deal['title']
        link = deal['url']
        embed_var.add_field(name='', value="• " + f"[**{title}**]({link})‎", inline=False)

    embed_var.set_image(url="attachment://img.gif")
    embed_var.set_footer(text=footer)
    return embed_var


def primegaming(store, mobile=False):
    embed_var = discord.Embed(title="🕹️ Amazon Prime Gaming 🕹️", description=f'\u200B\n**Free Now**', color=0x00aff4)

    for deal in store.data:
        title = deal['title']
        link = deal['url']
        end_date = store.get_date(deal, 'end', True)

        embed_var.add_field(
            name=f'\u200B\n',
            value=f"• [**{title}**]({link})\nUntil: {end_date}" if end_date else f"• [**{title}**]({link})",
            inline=False
        )

    embed_var.set_image(url="attachment://img.gif")
    embed_var.set_footer(text=footer)
    return embed_var
