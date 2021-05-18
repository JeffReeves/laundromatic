import os
import discord

# get token from environment variable
# TODO: 
#   - prompt user for token, if not provided as env variable
token   = os.environ.get('DISCORD_TOKEN')
dm_user = os.environ.get('DISCORD_DM_USER')

# add intents to get users by id
intents         = discord.Intents.default()
intents.members = True
client          = discord.Client(intents=intents)

@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))
    user = await client.fetch_user(dm_user)
    print('[DEBUG] user:')
    print(user)
    await user.send("Ready to watch your laundry!")

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith('$hello'):
        print('[DEBUG] message:')
        print(message)
        print('[DEBUG] message.author.id:')
        print(message.author.id)
        print('[DEBUG] client:')
        print(client)
        print('[DEBUG] client.user:')
        print(client.user)
        await message.channel.send('Hello!')

        # get the user by id
        user = client.get_user(message.author.id)
        print('[DEBUG] user:')
        print(user)
        await user.send('👀 I see you')
        # alternative to send a DM to the message's author
        #print('[DEBUG] message.author:')
        #print(message.author)
        #await message.author.send('👀 I see you')

if token:
    client.run(token)
else:
    print('[ERROR] No token provided')
    print('[HELP] Set DISCORD_TOKEN variable and run again')
    print('[EXAMPLE] export DISCORD_TOKEN=\'mycooltoken\'')