import os
import pprint
import discord

# get token from environment variable
# TODO: 
#   - prompt user for token, if not provided as env variable
token  = os.environ.get('DISCORD_TOKEN')
client = discord.Client()

@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith('$hello'):
        print('[DEBUG] message:')
        pprint(message)
        print('[DEBUG] client:')
        pprint(client)
        print('[DEBUG] client.user:')
        pprint(client.user)
        await message.channel.send('Hello!')

if token:
    client.run(token)
else:
    print('[ERROR] No token provided')
    print('[HELP] Set DISCORD_TOKEN variable and run again')
    print('[EXAMPLE] export DISCORD_TOKEN=\'mycooltoken\'')