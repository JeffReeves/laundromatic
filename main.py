#!/usr/bin/env python3
"""
purpose: Discord Bot that sends laundry status messages.
    Built for use with a Raspberry Pi + 
        photoresistor (light sensor) attached via GPIO pins.

author: Jeff Reeves
"""

# TODO:
# - Get bot commands working
# - Get GPIO pins working with light sensor


#==[ IMPORTS ]=============================================================================================================================

import logging
import sys
import os
import traceback
import json
import base64
import argparse
import getpass
import discord


#==[ CONFIG ]==============================================================================================================================

# logging
formatter = logging.Formatter('[ %(asctime)s ] [ %(name)s ] [ %(levelname)s ] [ %(funcName)s ]\n%(message)s')

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(formatter)
console_handler.setLevel(logging.DEBUG)

file_handler = logging.FileHandler('laundromatic.log')
file_handler.setFormatter(formatter)
file_handler.setLevel(logging.DEBUG)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(console_handler)
logger.addHandler(file_handler)

# discord client 
# NOTE: intents are needed to get users by id, this must be set in 
#   the Discord Dev Center:
#       https://discord.com/developers/applications/ -> 
#       Application -> Bot -> SERVER MEMBERS INTENT (ON)
intents         = discord.Intents.default()
intents.members = True
client          = discord.Client(intents = intents)


#==[ MAIN ]================================================================================================================================

def main(args):

    # config
    # use arguments if available, else get from user input
    debug    = args.debug    or False
    token    = args.token    or getpass('Token: ')
    watchers = args.watchers or input('Watchers (space separated user IDs):').split()
    prefix   = args.prefix   or '!' 
    loglevel = args.loglevel or logging.INFO

    # set log level
    logger.setLevel(loglevel)

    if debug:
        logger.debug('All arguments passed to script:')
        logger.debug(args)
        logger.debug(f'token:\n{token}')
        logger.debug(f'watchers:\n{watchers}')
        logger.debug(f'prefix:\n{prefix}')
        logger.debug(f'loglevel:\n{loglevel}')

    # get user by ID
    async def get_user_by_id(watcher):
        logger.debug(f'watcher:\n{watcher}')
        user = await client.fetch_user(watcher)
        logger.debug(f'user:\n{user}')
        return user

    # send DM
    async def send_dm(user, message = 'Sending you a message'):
        logger.debug(f'Sending DM to:\n{user}')
        logger.debug(f'Message:\n{message}')
        await user.send(message)

    # READY
    @client.event
    async def on_ready():
        logger.info(f'Bot {client.user} is ready')
        for index, watcher in enumerate(watchers):
            user = await get_user_by_id(watcher)
            if user:
                await send_dm(user)

    # DISCONNECT
    @client.event
    async def on_disconnect():
        logger.warning('Disconnected from Discord')

    # ERROR
    @client.event
    async def on_error(event, *args, **kwargs):
        message = args[0] #Gets the message object
        logger.error(f'Error Message: {message}')
        logger.error(traceback.format_exc())
        for watcher in enumerate(watchers):
            user = await get_user_by_id(watcher)
            if user:
                logger.debug(f'User:\n{user}')
                await send_dm(user, 'Encountered an error...')

    # MESSAGE
    @client.event
    async def on_message(message):

        # return if the message is from the bot
        if message.author == client.user:
            return

        # check for command prefix
        if message.content.startswith(prefix):

            # debugging
            logger.debug(f'message:\n{message}')
            logger.debug(f'message.author.id:\n{message.author.id}')
            logger.debug(f'client.user:\n{client.user}')
            logger.debug(f'message.channel:\n{message.channel}')
            logger.debug(f'message.channel.type:\n{message.channel.type}')
            logger.debug(f'message:\n{message}')

            # send a message back to the channel
            await message.channel.send('Hello!')

            # check if private message
            if message.channel.type == discord.ChannelType.private:
                logger.debug(f'Received a private message')

                # send PM to the author
                await message.author.send('👀 I see you 👍')
                #user = await get_user_by_id(message.author.id)
                #await send_dm(user, message = '👀 I see you 👍')

    if token:
        client.run(token)
    else:
        logger.error('No token provided')

    return


#==[ COMMAND LINE ]========================================================================================================================

if __name__ == "__main__":

    # these important values must be set
    token    = None
    watchers = []
    prefix   = None
    loglevel = None

    # the values get set from (in order):
    #   1. JSON config file
    #   2. environment variables
    #   3. arguments passed via command line


    # 1. JSON config file
    config_file = 'config.json'
    if os.path.exists(config_file):
        with open(config_file) as json_config_file:
            config = json.load(json_config_file)

            if 'token' in config:
                token = config['token']

            if 'watchers' in config:
                if all(config['watchers']):
                    watchers = config['watchers']

            if 'prefix' in config:
                prefix = config['prefix']

            if 'loglevel' in config:
                loglevel = config['loglevel']


    # 2. environment variables
    if not token:
        token    = os.environ.get('DISCORD_TOKEN')

    if not watchers:
        watchers = os.environ.get('DISCORD_WATCHERS')
        if watchers:
            watchers = watchers.split() # convert space separated string to list

    if not prefix:
        prefix   = os.environ.get('DISCORD_PREFIX')

    if not loglevel:
        loglevel = os.environ.get('DISCORD_LOGLEVEL')


    # 3. arguments on command line
    parser = argparse.ArgumentParser()

    loglevels = {
        'debug'     : logging.DEBUG,
        'info'      : logging.INFO,
        'warning'   : logging.WARNING,
        'error'     : logging.ERROR,
        'critical'  : logging.CRITICAL,
    }

    # custom type for argparse
    def set_log_level(level):
        if level is None:
            level = 'info'
        if level not in loglevels:
            raise ValueError(f"Log Level must be one of: {' | '.join(loglevels.keys())}")
        return loglevels[level]

    parser.add_argument('-l',
                        '--loglevel',
                        dest    = 'loglevel',
                        type    = set_log_level,
                        help    = f"Logging Level ({' | '.join(loglevels.keys())})")

    if not prefix:

        parser.add_argument('-p', 
                            '--prefix', 
                            dest        = 'prefix',
                            type        = str,
                            help        = 'Prefix for commands')

    if not token:

        # custom type for argparse
        def decode_base64_token(base64_token):
            return base64.b64decode(base64_token).decode('UTF-8')

        group_tokens = parser.add_mutually_exclusive_group(required = True)

        group_tokens.add_argument('-t', 
                                  '--token',
                                  dest      = 'token',
                                  type      = str,
                                  help      = 'Token')

        group_tokens.add_argument('-b', 
                                  '--base64_token',
                                  dest      = 'token',
                                  type      = decode_base64_token, 
                                  help      = 'Token (base64)')

    if not watchers:

        group_watchers = parser.add_mutually_exclusive_group(required = True)

        group_watchers.add_argument('-w', 
                                    '--watcher', 
                                    dest    = 'watchers',
                                    type    = str,
                                    action  = 'append', 
                                    help    = 'User ID of Watcher (can be used multiple times)')

        group_watchers.add_argument('--watchers', 
                                    dest    = 'watchers',
                                    type    = str,
                                    nargs   = '+', 
                                    help    = 'User IDs for Watchers (space separated list)')

    args, unknown = parser.parse_known_args()

    if 'token' not in args:
        args.token      = token

    if 'watchers' not in args:
        args.watchers   = watchers

    if 'prefix' not in args:
        args.prefix     = prefix

    if 'loglevel' not in args:
        args.loglevel  = loglevel

    if 'debug' not in args:
        args.debug     = True

    main(args)