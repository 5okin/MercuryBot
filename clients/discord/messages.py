import discord


footer = ""
ZWSP = "\u200B" # Zero Width Space

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
            all_freenow += "• " + f"[**{title}**]({link})\n{ZWSP}"
        else:
            start_date = store.get_date(deal, 'start')
            end_date = store.get_date(deal, 'end')

            game_details = f"Free: {start_date} - {end_date}"
            all_upnext += "• " + f"[**{title}**]({link}){ZWSP}\n"

    embed_var.add_field(name=f'{ZWSP}\n**Free Now**', value=f"Until: {now_end_date}\n\n{all_freenow}", inline=True)
    if (not mobile):
        embed_var.add_field(name=f'{ZWSP}\n**Up Next**', value=f"{ZWSP}{ZWSP}{ZWSP}{game_details}\n\n{all_upnext}{ZWSP}", inline=True)
    embed_var.set_footer(text=footer)

    return embed_var

# MARK: gog
def gog(store, mobile=False):
    embed_var = discord.Embed(title="🕹️ GOG 🕹️", description=f'{ZWSP}\n**Free Now**', color=0x00aff4)

    for deal in store.data:
        title = deal['title']
        link = deal['url']
        end_date = store.get_date(deal, 'end', True)
        embed_var.add_field(name=f'{ZWSP}\n', value=f"[**{title}**]({link})\nUntil: {end_date}", inline=False)

    embed_var.set_image(url="attachment://img.gif")
    embed_var.set_footer(text=footer)
    return embed_var

# MARK: default
def default(store, mobile=False):
    DISCORD_MAX_FIELD_VALUE_CHARS = 1024
    NUM_OF_DEALS_USE_SINGLE_COLUMN = 5
    USE_SINGLE_COLUMN = len(store.data) <= NUM_OF_DEALS_USE_SINGLE_COLUMN
    col1 = []
    col2 = []

    embed_var = discord.Embed(title=f"🕹️ {store.service_name} 🕹️", description=f"{ZWSP}\n**Free now**", color=0x00aff4)

    def save_row():
        nonlocal col1, col2

        if not col1 and not col2:
            return

        embed_var.add_field(name=f"{ZWSP}\n", value="".join(col1) or ZWSP, inline=True)
        embed_var.add_field(name=ZWSP, value=f"{ZWSP}", inline=True)
        embed_var.add_field(name=ZWSP, value="".join(col2) or ZWSP, inline=True)

        col1.clear()
        col2.clear()

    for i, deal in enumerate(store.data):
        entry = f"• [**{deal['title']}**]({deal['url']})"
        end_date = store.get_date(deal, 'end', True)
        if end_date:
            entry += f"\nUntil: {end_date}"
        entry += "\n\n"

        target = col1 if USE_SINGLE_COLUMN or i % 2 == 0 else col2

        # Check if adding this entry would exceed Discord's field character limit
        if sum(len(e) for e in target) + len(entry) >= DISCORD_MAX_FIELD_VALUE_CHARS:
            save_row()

        target.append(entry)

    save_row()
    embed_var.set_image(url="attachment://img.gif")
    embed_var.set_footer(text=footer)
    return embed_var
