import discord


footer = ""

#MARK: epic
def epic(store, mobile=False):
    # zima = 0x16b8f3
    embed_var = discord.Embed(title="🕹️ Epic Free Games 🕹️", description="", color=0x00aff4)
    embed_var.set_image(url="attachment://img.gif")
    all_freenow = all_upnext = ''

    for deal in store.data:
        title = deal['title']
        link = deal['url']

        if deal['activeDeal']:
            now_end_date = store.get_date(deal, 'end', True)
            all_freenow += "• " + f"[**{title}**]({link})\n‎"
        else:
            start_date = store.get_date(deal, 'start')
            end_date = store.get_date(deal, 'end')

            game_details = f"Free: {start_date} - {end_date}"
            all_upnext += "• " + f"[**{title}**]({link})‎\n"

    embed_var.add_field(name=f'\u200B\n**Free Now**', value=f"Until: {now_end_date}\n\n{all_freenow}", inline=True)
    if (not mobile):
        embed_var.add_field(name=f'\u200B\n**Up Next**', value=f"‎‎‎{game_details}\n\n{all_upnext}‎", inline=True)
    embed_var.set_footer(text=footer)

    return embed_var

# MARK: gog
def gog(store, mobile=False):
    embed_var = discord.Embed(title="🕹️ GOG 🕹️", description=f'\u200B\n**Free Now**', color=0x00aff4)

    for deal in store.data:
        title = deal['title']
        link = deal['url']
        end_date = store.get_date(deal, 'end', True)
        embed_var.add_field(name=f'\u200B\n', value=f"[**{title}**]({link})\nUntil: {end_date}", inline=False)

    embed_var.set_image(url="attachment://img.gif")
    embed_var.set_footer(text=footer)
    return embed_var

# MARK: default
def default(store, mobile=False):
    embed_var = discord.Embed(title=f"🕹️ {store.service_name} 🕹️", description="\u200B\n**Free now**", color=0x00aff4)
    col1 = col2 = ""

    def add_row():
        if not col1 and not col2:
            return

        embed_var.add_field(name="\u200B\n", value=col1 or "\u200B", inline=True)
        embed_var.add_field(name="\u200B", value="\u200B", inline=True)
        embed_var.add_field(name="\u200B", value=col2 or "\u200B", inline=True)

    for i, deal in enumerate(store.data):
        title = deal['title']
        link = deal['url']
        end_date = store.get_date(deal, 'end', True)

        entry = f"• [**{title}**]({link})"
        if end_date:
            entry += f"\nUntil: {end_date}"
        entry += "\n\n"

        target = col1 if i % 2 == 0 else col2

        if len(target) + len(entry) >= 1024:
            add_row()
            col1 = col2 = ""

        if i % 2 == 0:
            col1 += entry
        else:
            col2 += entry

    add_row()
    embed_var.set_image(url="attachment://img.gif")
    embed_var.set_footer(text=footer)
    return embed_var
