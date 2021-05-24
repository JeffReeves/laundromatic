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

import enum
from pprint import pprint
import logging
import sys
import os
import traceback
import json
import base64
import argparse
import getpass
import discord
from discord.ext import commands


#==[ CONFIG ]==============================================================================================================================

# logging
formatter = logging.Formatter('[ %(asctime)-23s ][ %(name)-8s ][ %(levelname)-8s ][ %(funcName)-16s ] (%(filename)s:%(lineno)s) - %(message)s')

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


#==[ MAIN ]================================================================================================================================

def main(args):

    # config
    # use arguments if available, else get from user input
    token    = args.token    or getpass('Token: ')
    watchers = args.watchers or input('Watchers (space separated user IDs):').split()
    users    = dict.fromkeys(watchers)
    prefix   = args.prefix   or '!' 
    loglevel = args.loglevel or logging.INFO

    # set log level
    logger.setLevel(loglevel)

    logger.debug(f'All arguments passed to script: {args}')
    logger.debug(f'token: {token}')
    logger.debug(f'watchers: {watchers}')
    logger.debug(f'users: {users}')
    logger.debug(f'prefix: {prefix}')
    logger.debug(f'loglevel: {loglevel}')

    # discord client 
    # NOTE: intents are needed to get users by id, this must be set in 
    #   the Discord Dev Center:
    #       https://discord.com/developers/applications/ -> 
    #       Application -> Bot -> SERVER MEMBERS INTENT (ON)
    intents         = discord.Intents.default()
    intents.members = True
    #client          = discord.Client(intents = intents)
    client          = commands.Bot(command_prefix = prefix, 
                                   intents        = intents)

    # CUSTOM

    # sets user details for all users
    async def set_user_details(users):
        logger.debug(f'users: {users}')
        for index, user_id in enumerate(users):
            logger.debug(f'user id: {user_id}')
            if not users[user_id]:
                user = await client.fetch_user(user_id)
                if(user):
                    logger.debug(f'user: {user}')            
                    #users[user_id] = user
                    users.update({ user_id: user })
                else:
                    logger.error(f'unable to acquire user by user_id: {user_id}')
            else:
                logger.debug(f'user already set: {user}') 
        return

    # send DM
    async def send_dms(users, message = 'test message'):
        logger.debug('Sending DMs to all users')
        for index, user_id in enumerate(users):
            await send_dm(users[user_id], message)
        return

    async def send_dm(user, message = 'test message'):
        logger.debug(f'Sending DM to: {user}')
        logger.debug(f'Message: {message}')
        await user.send(message)
        return

    # send message to channel (#laundromatic)
    async def send_message():
        channel = discord.utils.get(client.get_all_channels(), 
                                    name = 'general')
        return

    # COMMANDS
    @client.command(name = 'watch', aliases = ['subscribe'])
    async def add_user_to_watchers(ctx, *args):

        # NOTE: watchers and users comes from main()

        logger.debug(f'args: {args}')
        logger.debug(f'args length: {len(args)}')

        logger.debug(f'ctx.guild: {ctx.guild}')
        logger.debug(f'ctx.author: {ctx.author}')
        logger.debug(f'ctx.author.id: {ctx.author.id}')
        logger.debug(f'ctx.message: {ctx.message}')
        logger.debug(f'ctx.message.author.id: {ctx.message.author.id}')

        if not args:
            logger.debug('No arguments passed to command')
            logger.debug(f'Using author ID {ctx.author.id} as argument')
            args = [ str(ctx.author.id) ]

        for index, arg in enumerate(args):
            if not arg.isnumeric():
                logger.warning(f'The arguments are not numeric ({arg}). Skipping...')
                continue
            if arg not in users:
                logger.info(f'User ID {arg} not in users list')
                adding_message = f'Adding {arg} to users list'
                adding_message += f'Current Users:\n{users}'
                logger.info(adding_message)
                users[arg] = None
                await set_user_details(users)
                await send_dms(users[arg], 
                               message = 'You have been added to the Watchers list')
                await ctx.send(adding_message)
        #await ctx.send('{} arguments: {}'.format(len(args), ', '.join(args)))
        return 

    @add_user_to_watchers.error
    async def add_user_to_watchers_error(ctx, error):
        logger.error(f'{error}')
        if isinstance(error, commands.BadArgument):
            await ctx.send('[ERROR] Invalid user ID(s)')
        return


    # READY
    @client.event
    async def on_ready():
        logger.info(f'Bot {client.user} is online')

        # get users by user ids
        await set_user_details(users)

        # send a DM to each user that the bot is online
        await send_dms(users, message = '[ONLINE] Watching your laundry')

        # TODO: 
        #   - put a message in the #laundromatic channel that the bot is online
        return 

    # DISCONNECT
    @client.event
    async def on_disconnect():
        logger.warning('Disconnected from Discord')
        return


    # ERROR
    @client.event
    async def on_error(event, *args, **kwargs):
        message = args[0] # get the message object
        logger.error(f'Error Message: {message}')
        logger.error(traceback.format_exc())
        await send_dms(users, message = '[ERROR] Encountered an error')
        return


    # MESSAGE
    @client.event
    async def on_message(message):

        # return if the message is from the bot
        if message.author == client.user:
            return

        # check for command prefix
        if message.content.startswith(prefix):

            # debugging
            logger.debug(f'message: {message}')
            logger.debug(f'message.author.id: {message.author.id}')
            logger.debug(f'client.user: {client.user}')
            logger.debug(f'message.channel: {message.channel}')
            logger.debug(f'message.channel.type: {message.channel.type}')
            logger.debug(f'message: {message}')

            # # general commands
            # if message.content.startswith(prefix + 'watch'):
            #     await message.channel.send('Adding you to watch')
            
            # if message.content.startswith(prefix + 'stop'):
            #     await message.channel.send('Hello!')

            # check if private message
            if message.channel.type == discord.ChannelType.private:
                logger.debug('Received a private message')

                # send PM to the author
                await message.author.send('👀 I see you 👍')
                #user = await get_user_by_id(message.author.id)
                #await send_dm(user, message = '👀 I see you 👍')

                # call commands
                await client.process_commands(message)

            else:
                logger.debug(f'message.channel.name: {message.channel.name}')

                # check if in '#laundromatic' channel
                if message.channel.name == 'laundromatic':
                    logger.debug('Message received in #laundromatic channel')
                    # call commands
                    await client.process_commands(message)

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

    main(args)