import os
import traceback
import getpass
import discord

prefix = '!'

# use environment variable or user input
token   = os.environ.get('DISCORD_TOKEN')   or getpass.getpass('Token: ')
dm_user = os.environ.get('DISCORD_DM_USER') or input('User ID: ')

# create client 
# NOTE: intents needed to get users by id
intents         = discord.Intents.default()
intents.members = True
client          = discord.Client(intents=intents)

# get user by ID
async def get_user_by_id(dm_user):
    user = await client.fetch_user(dm_user)
    print('[DEBUG] user:')
    print(user)
    return user

# send DM
async def send_dm(user, message = 'Sending you a message'):
    await user.send(message)

# READY
@client.event
async def on_ready():
    print('[INFO] Bot {0.user} is ready'.format(client))
    # fetch the user ID for the user to DM
    # TODO:
    #   - create array of users to DM
    user = await get_user_by_id(dm_user)
    await send_dm(user)

# DISCONNECT
@client.event
async def on_disconnect():
    print('[WARN] Disconnected from Discord')

# ERROR
@client.event
async def on_error(event, *args, **kwargs):
    message = args[0] #Gets the message object
    print('[DEBUG] message:')
    print(message)
    print(traceback.format_exc())
    #logging.warning(traceback.format_exc()) #logs the error
    user = await client.fetch_user(dm_user)
    print('[DEBUG] user:')
    print(user)
    await user.send('Encountered an error...')

# MESSAGE
@client.event
async def on_message(message):

    # return if the message is from the bot
    if message.author == client.user:
        return

    # check for command prefix
    if message.content.startswith(prefix):

        # debugging
        print('[DEBUG] message:')
        print(message)
        print('[DEBUG] message.author.id:')
        print(message.author.id)
        print('[DEBUG] client:')
        print(client)
        print('[DEBUG] client.user:')
        print(client.user)
        print('[DEBUG] message.channel:')
        print(message.channel)
        print('[DEBUG] message.channel.type:')
        print(message.channel.type)

        # send a message back to the channel
        await message.channel.send('Hello!')

        # check if private message
        if message.channel.type == 'private':
            # send PM to the author
            #await message.author.send('👀 I see you 👍')
            user = await get_user_by_id(message.author.id)
            await send_dm(user, message = '👀 I see you 👍')

if token:
    client.run(token)
else:
    print('[ERROR] No token provided')
    print('[HELP] Set DISCORD_TOKEN variable and run again')
    print('[EXAMPLE] export DISCORD_TOKEN=\'mycooltoken\'')