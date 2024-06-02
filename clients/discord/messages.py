import discord
import os
import json
# from PIL import Image
from datetime import datetime, timedelta


def get_date(game_date, flag=False):
    month = datetime.strptime(game_date, '%y-%m-%d %H:%M:%S').strftime("%b")
    day = datetime.strptime(game_date, '%y-%m-%d %H:%M:%S').day
    return str(month) + ' ' + str(day)


footer = ""


def epic(data, mobile=False):
    # f = open('./data/epic_database.json')
    # data_json = json.load(f)
    data_json = data

    # zima = 0x16b8f3
    embed_var = discord.Embed(title="🕹️ Epic Free Games 🕹️", description="", color=0x00aff4)
    embed_var.set_image(url="attachment://img.gif")
    # embed_var.set_image(url= "https://i.imgur.com/s3GlK9a.gif")

    all_freenow = ''
    all_upnext = ''

    for data in data_json:
        start_date = datetime.strptime(data['startDate'], '%y-%m-%d %H:%M:%S')
        end_date = datetime.strptime(data['endDate'], '%y-%m-%d %H:%M:%S')

        title = data['title']
        link = data['url']

        # scrape_images.scrapeimages(title, data['image'])

        if start_date < datetime.now() < end_date:
            # startDate = get_date(data['startDate'])
            now_end_date = get_date(data['endDate'], True)

            # all_freenow += "• " + f"[**{title}**]({link})\n‎ [Launcher](com.epicgames.launcher://store/p/tomb-raider)\n"
            # all_freenow += "• " + f"[**{title}**]({link})\n‎" + "<com.epicgames.launcher://store/p/tomb-raider>\n"
            all_freenow += "• " + f"[**{title}**]({link})\n‎"

        else:
            start_date = get_date(data['startDate'])
            end_date = get_date(data['endDate'])

            game_details = f"Free: {start_date} - {end_date}"
            all_upnext += "• " + f"[**{title}**]({link})‎\n"

    embed_var.add_field(name=f'\u200B\n**Free Now**', value=f"Until: {now_end_date}\n\n{all_freenow}", inline=True)
    if (not mobile):
        embed_var.add_field(name=f'\u200B\n**Up Next**', value=f"‎‎‎{game_details}\n\n{all_upnext}‎", inline=True)
    embed_var.set_footer(text=footer)

    # embed_var.set_image(url='https://cdn.discordapp.com/attachments/827564503930765315/829040412060418078/img.jpg')
    # embed_var.set_footer(text= footer)
    # f.close()
    return embed_var


def gog(data, mobile=False):
    # f = open('./data/gog_database.json')
    # data_json = json.load(f)
    data_json = data
    # f.close()
    # zima = 0x16b8f3
    embed_var = discord.Embed(title="🕹️ GOG 🕹️", description=f'\u200B\n**Free Now**', color=0x00aff4)

    for data in data_json:
        title = data['title']
        link = data['url']
        end_date = data['endDate']
        # all_freenow += "• " + f"[**{title}**]({link})\n‎"
        embed_var.add_field(name=f'\u200B\n', value=f"[**{title}**]({link})\nUntil: {end_date}", inline=False)

    embed_var.set_image(url="attachment://img.gif")
    embed_var.set_footer(text=footer)
    return embed_var


def steam(data, mobile=False):
    data_json = data
    embed_var = discord.Embed(title="🕹️ Steam 🕹️", description="", color=0x00aff4)

    for data in data_json:
        title = data['title']
        link = data['url']
        embed_var.add_field(name='', value="• " + f"[**{title}**]({link})‎", inline=False)

    embed_var.set_image(url="attachment://img.gif")
    embed_var.set_footer(text=footer)
    return embed_var


def psplus(data, mobile=False):
    data_json = data
    embed_var = discord.Embed(title="🕹️ Play Station Plus 🕹️", description="", color=0x00aff4)

    for data in data_json:
        title = data['title']
        link = data['url']
        embed_var.add_field(name='', value="• " + f"[**{title}**]({link})‎", inline=False)

    embed_var.set_image(url="attachment://img.gif")
    embed_var.set_footer(text=footer)
    return embed_var
