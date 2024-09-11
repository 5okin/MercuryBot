# MercuryBot

MercuryBot is a Discord and X, formerly known as twitter, bot that monitors various platforms and finds new free game promotions. Stay updated on the latest giveaways from Epic Games, Steam, GOG, and PS Plus, and never miss out on the opportunity to grab titles for free.

<br>

<div align="center">
    <div>
        <a href="https://discord.com/api/oauth2/authorize?client_id=827564914733350942&permissions=534723885120&scope=bot">
        <img src="https://github.com/user-attachments/assets/0998cdf8-1797-4b92-bf8e-674c9063c470" width="200" />
    </div>
    <div>
        <img src="data:image/gif;base64,R0lGODlhAQABAAD/ACwAAAAAAQABAAACADs=" width="150" height="0" alt="" />
    </div>
    <div>
         <a href="https://x.com/_MercuryBot_">
        <img src="https://github.com/user-attachments/assets/9532f375-b187-4cfc-a06e-2f067200b0f6" width="180" /> 
    </div>
</div>

<br>

<p align='center'>
    <a href= "https://discord.com/api/oauth2/authorize?client_id=827564914733350942&permissions=534723885120&scope=bot"> 
    <img src="https://github.com/5okin/MercuryBot/assets/70406237/34d1a800-4dd5-4915-a02d-9c884848fcb3"></a>
<p>


Mercury bot sends you notifications like the ones bellow every time theres a new free game available so you never miss out again. For epic notifications on discord, it also sends you next weeks free game, if available, all in one notification !

<p align="center">
  <img alt="Light" src="https://github.com/5okin/MercuryBot/assets/70406237/a40c122b-369f-48f1-9f31-a9e383044da0" width="40%">
&nbsp; &nbsp; &nbsp; &nbsp;
  <img alt="Dark" src="https://github.com/user-attachments/assets/2aa7d6b4-d88a-44f4-a8c7-9871e760f18d" width="40%">
</p>


## Features

- **Multi-Platform Support:** MercuryBot keeps an eye on free game promotions on Epic Games, Steam, GOG, and PS Plus.

- **Online 24/7:** Bot doesn't go offline ensuring you dont miss out on any deal!

- **Automated Reminders:** Receive timely reminders in your Discord server or twitter feed when new free games become available.

- **Customizable Settings:** Configure MercuryBot to tailor notifications to your preferences on discord.

- **Ephemeral Messages:** Commands you send to the bot won't spam and clutter you channels, they stay invisible to everyone but you.

- **Privacy focused:** Using slash commands the bot never has access to you messages.


## Discord

### Slash Commands
- `/settings`: Setup and review your notification preferences using the `/settings` slash command.
- `/deals`: Display a list of available stores and get the current available games (Ephemeral Message).
- `/feedback`: Send feedback or bug reports. 

### How to Use on Discord

1. Invite MercuryBot to your Discord server. [<img src="https://github.com/5okin/MercuryBot/assets/70406237/9fbf5218-d5bc-476a-8892-2496a1bbe1ba">](https://discord.com/api/oauth2/authorize?client_id=827564914733350942&permissions=534723885120&scope=bot)

2. Run the `/settings` slash command and configure the bot:

    - `Test notifications`: Test your settings.
    - `Set channel`: The channel that will receive the notifications.
    - `Set role`: Set the role that is pinged when a notification is send, if you'd like.
    - `Set stores`: Set the store you wish to receive notifications for.

<p align='center'>
    <image src="https://github.com/user-attachments/assets/d90ebcab-0676-4a47-a15a-c99368281d8b">
<p>

3. Enjoy automatic alerts for new free games on various platforms.


### Command breakdown

- The `Test notifications` button sends a notification to the set channel, pinging the set role so as to test that everything is working as expected.
<p align='center'>
 <image src="https://github.com/user-attachments/assets/0806c7b4-5ddd-402a-90e1-c4ba4e6e9584">
<p>

- The `Set channel` button allowes you to set the channel the channel you want the bot to send the notifications to. If its a locked channel make sure to give the bot permissions. A channel must be set.
<p align='center'>
 <image src="https://github.com/user-attachments/assets/000b9130-5e67-4864-a070-45f2c42184b6">
<p>

- The `Set role` button allowes you set the role that will be pinged when a notification is send, you can choose not to ping any roles.
<p align='center'>
 <image src="https://github.com/user-attachments/assets/36d13c17-d472-497c-bb91-f2211891cd14">
<p>

- The `Set stores` button allows you change the stores for which you receive notifications.
<p align='center'>
 <image src="https://github.com/user-attachments/assets/4a468df7-1ae5-4b7a-9457-15b8b90f6cf1">
<p>



## Running it on your own

- Download or clone the repository.
- Make sure you have python 3.10 or higher installed. `python -V`
- Install the required dependencies by running. `pip install -r requirements.txt`
- Make sure you have a working discord [bot TOKEN](#get-a-discord-token), a [twitter keys](#get-twitter-keys)  and [mongoDB server](#mongodb-connection-string) running.
- Add your credentials to the [.env](#env-file) file.
- Run it using: `python3 main.py`

### Get a discord TOKEN
Log in to https://discord.com/developers/applications/ and click on the New Application button. Go to the bot tab and click the Add Bot button to get a TOKEN.

### Get twitter Keys
You can follow twitters documentation https://developer.x.com/en/docs/twitter-api/getting-started/getting-access-to-the-twitter-api to get started.


### MongoDB connection string
The database used is MongoDB, you can use mongodb atlas which offers a shared $0/month plan, if you don't want to host your own database. Go to DEPLOYMENT / Database / Connect / Drivers. You should get a string like this:

`mongodb+srv://...`


### `.env` file

To set up the token you will have to either make use of the [`.env.example`](.env.example) file, either copy or rename it to `.env` and edit it with your data.

Here is an explanation of what everything is:
| Variable               | What it is                                                                                        |
| ---------------------- | ----------------------------------------------                                                    |
| DEBUG                  | Can be true or false. Changes the log output and TOKEN used to run the bot & slash command sync   |
| DB_CONNECTION_STRING   | Your mongoDB connection string                                                                    |
| DISCORD_TOKEN_LIVE     | Live discord TOKEN, used when DEBUG=False                                                         |
| DISCORD_TOKEN_TEST     | Test/Dev discord TOKEN, used when DEBUG=True                                                      |
| X_ACCESS_TOKEN         | Twitter/X access token                                                                            |
| X_ACCESS_TOKEN_SECRET  | Twitter/X access token secret                                                                     | 
| X_API_KEY              | Twitter/X api key                                                                                 |
| X_API_SECRET           | Twitter/X api secret                                                                              |
| DISCORD_DEV_GUILD      | Test Guild Id (not necessary)                                                                     |
| DISCORD_ADMIN_ACC      | Your account Id (not necessary)                                                                   |


- When `DEBUG` variable is set to True, the log output is changed, the bot uses DISCORD_TOKEN_TEST instead of DISCORD_TOKEN_LIVE and the twitter client isnt run at all.

- When in `DEBUG` mode the bot can use `DISCORD_DEV_GUILD` to sync commands to that specific guild to cut down on wait times.

- If you wish to receive discord direct messages from the bot for things like bot restart, feedback send, etc you can set `DISCORD_ADMIN_ACC`.

## Contributions

Contributions are welcome! If you have any ideas for improvements or new features, feel free to submit a pull request.
