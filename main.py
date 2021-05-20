#!/usr/bin/env python3
"""
purpose: Discord Bot that sends laundry status messages.
    Built for use with a Raspberry Pi + 
        photoresistor (light sensor) attached via GPIO pins.

author: Jeff Reeves
"""

#==[ IMPORTS ]=============================================================================================================================

from pprint import pprint
import os
import traceback
import base64
import argparse
import getpass
import discord


#==[ CONFIG ]==============================================================================================================================

# globals
debug    = True
prefix   = '!'
watchers = []

# create client 
# NOTE: intents are needed to get users by id, this must be set in 
#   the Discord Dev Center:
#       https://discord.com/developers/applications/ -> 
#       Application -> Bot -> SERVER MEMBERS INTENT (ON)
intents         = discord.Intents.default()
intents.members = True
client          = discord.Client(intents = intents)


#==[ FUNCTIONS ]===========================================================================================================================

# get user by ID
async def get_user_by_id(watcher):
    user = await client.fetch_user(watcher)
    if debug:
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
    user = await get_user_by_id(watcher)
    await send_dm(user)

# DISCONNECT
@client.event
async def on_disconnect():
    print('[WARN] Disconnected from Discord')

# ERROR
@client.event
async def on_error(event, *args, **kwargs):
    message = args[0] #Gets the message object
    if debug:
        print('[DEBUG] message:')
        print(message)
    print(traceback.format_exc())
    #logging.warning(traceback.format_exc()) #logs the error
    user = await client.fetch_user(watcher)
    if debug:
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
        if debug:
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
        if message.channel.type == discord.ChannelType.private:
            if debug:
                print('[DEBUG] Received a private message')
            # send PM to the author
            await message.author.send('👀 I see you 👍')
            #user = await get_user_by_id(message.author.id)
            #await send_dm(user, message = '👀 I see you 👍')

#==[ MAIN ]================================================================================================================================

def main(args):

    if args.debug:
        print('[DEBUG] Main called')
        print('[DEBUG] All arguments passed to script:')
        pprint(args)

    # try to get values from environment variables
    token   = os.environ.get('DISCORD_TOKEN')
    watcher = os.environ.get('DISCORD_WATCHER')

    if token:
        client.run(token)
    else:
        print('[ERROR] No token provided')
        print('[HELP] Set DISCORD_TOKEN variable and run again')
        print('[EXAMPLE] export DISCORD_TOKEN=\'mycooltoken\'')

    return

#==[ COMMAND LINE ]========================================================================================================================

if __name__ == "__main__":

    # custom types for argparse
    def decode_base64_token(base64_token):
        return base64.base64decode(base64_token)

    # create parser
    parser = argparse.ArgumentParser()

    # create groups of arguments
    group_tokens    = parser.add_mutually_exclusive_group(required = True)
    group_watchers  = parser.add_mutually_exclusive_group(required = True)

    # add arguments to parser
    parser.add_argument('-d', 
                        '--debug', 
                        dest    = 'debug',
                        action  = 'store_true', 
                        help    = 'Debug Mode')

    group_tokens.add_argument('-t', 
                              '--token',
                              dest      = 'token',
                              type      = str,
                              help      = 'Bot Token')

    group_tokens.add_argument('-b', 
                              '--base64_token',
                              dest      = 'token',
                              type      = decode_base64_token, 
                              help      = 'Bot Token (base64)')

    group_watchers.add_argument('-w', 
                                '--watcher', 
                                dest    = 'watcher',
                                type    = str,
                                action  = 'append', 
                                help    = 'User ID of Watcher')

    group_watchers.add_argument('--watchers', 
                                dest    = 'watchers',
                                type    = str,
                                nargs   = '+', 
                                help    = 'User IDs for Watchers (space separated list)')

    # parse argument
    args = parser.parse_args()

    # decode encrypted token
    if not args.token and not args.base64_token: 
        args.token = getpass('Bot Token: ')

    # pass all arguments as a dictionary to the main function
    main(args)