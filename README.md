# MercuryBot

MercuryBot is a Discord bot *(so far...)* that monitors various platforms and finds new free game promotions. Stay updated on the latest giveaways from Epic Games, Steam, GOG, and PS Plus, and never miss out on the opportunity to grab exciting titles for free.

<p align='center'>
    <a href= "https://discord.com/api/oauth2/authorize?client_id=827564914733350942&permissions=534723885120&scope=bot"> 
    <img src="https://github.com/5okin/MercuryBot/assets/70406237/34d1a800-4dd5-4915-a02d-9c884848fcb3"></a>
<p>


Mercury bot sends you notifications like the one bellow every time theres a new free game available so you never miss out again. For epic, it also sends you next weeks free game, if available, all in one notification !

<p align='center'>
    <image src="https://github.com/5okin/MercuryBot/assets/70406237/a40c122b-369f-48f1-9f31-a9e383044da0">
<p>


## Features

- **Multi-Platform Support:** MercuryBot keeps an eye on free game promotions on Epic Games, Steam, GOG, and PS Plus.

- **Online 24/7:** Bot doesn't go offline ensuring you dont miss out on any deal!

- **Automated Reminders:** Receive timely reminders in your Discord server when new free games become available.

- **Customizable Settings:** Configure MercuryBot to tailor notifications to your preferences.

- **Ephemeral Messages:** Commands you send to the bot won't spam and clutter you channels, they stay invisible to everyone but you.

- **Privacy focused:** Using slash commands the bot never has access to you messages.


## How to Use

1. Invite MercuryBot to your Discord server. [<img src="https://github.com/5okin/MercuryBot/assets/70406237/9fbf5218-d5bc-476a-8892-2496a1bbe1ba">](https://discord.com/api/oauth2/authorize?client_id=827564914733350942&permissions=534723885120&scope=bot)

2. Set up your notification preferences using the following slash commands:

    - `/role-ping`: Set the role that is pinged when a notification is send.
    - `/store-notifications`: Set the store you wish to receive notifications for.
    - `/updates-channel`: The channel that will receive the notifications.
    - `/settings`: Review and test your settings.

<p align='center'>
    <image src="https://github.com/5okin/MercuryBot/assets/70406237/2e88a09f-53c3-4ff0-aa1e-2f111db0bde9">
<p>

3. Enjoy automatic alerts for new free games on various platforms.


## Slash Commands

- `/deals`: Display a list of available stores and get the current available games (Ephemeral Message).
- `/invite`: Get the invite link for MercuryBot.
- `/feedback`: Send feedback or bug reports. 


## Running it on your own.

- Download or clone the repository.
- Make sure you have python 3.10 or higher installed. `python -V`
- Install the required dependencies by running. `pip install -r requirements.txt`
- Make sure you have a working discord [bot TOKEN](#get-a-discord-token) and [mongoDB server](#mongodb-connection-string) running.
- Add your credentials to the [.env](#env-file) file.
- Run it using: `python3 main.py`

### Get a discord TOKEN
Log in to https://discord.com/developers/applications/ and click on the New Application button. Go to the bot tab and click the Add Bot button to get a TOKEN. 


### MongoDB connection string
The database used is MongoDB, you can use mongodb atlas which offers a shared $0/month plan, if you don't want to host your own database. Go to DEPLOYMENT / Database / Connect / Drivers. You should get a string like this:

`mongodb+srv://...`


### `.env` file

To set up the token you will have to either make use of the [`.env.example`](.env.example) file, either copy or rename it to `.env` and edit it with your data.

Here is an explanation of what everything is:
| Variable                  | What it is                                                                                                |
| ------------------------- | ----------------------------------------------                                                            |
| DEBUG                     | Can be true or false. Changes the log output and TOKEN used to run the bot & slash command sync           |
| DB_CONNECTION_STRING      | Your mongoDB connection string                                                                            |
| DISCORD_TOKEN_LIVE        | Live discord TOKEN, used when DEBUG=False                                                                 |
| DISCORD_TOKEN_TEST        | Test/Dev discord TOKEN, used when DEBUG=True                                                              |


## Contributions

Contributions are welcome! If you have any ideas for improvements or new features, feel free to submit a pull request.
