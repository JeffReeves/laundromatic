#!/usr/bin/env python3
"""
purpose: Discord Bot that sends laundry status messages.
    Built for use with a Raspberry Pi +
        photoresistor (light sensor) attached via GPIO pins.

author: Jeff Reeves
"""


#==[ IMPORTS ]=============================================================================================================================

import logging
from datetime import datetime, timedelta
import sys
import os
import traceback
import json
import base64
import argparse
import getpass
import asyncio
import gpiozero # type: ignore
import discord
from discord.ext import commands


#==[ CONFIG ]==============================================================================================================================

# logging
formatter = logging.Formatter('[ %(asctime)-23s ][ %(name)-8s ][ %(levelname)-8s ][ %(funcName)-20s ] (%(filename)s:%(lineno)s) - %(message)s')

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
    # use arguments if available, or set defaults
    token    = args.token               or getpass.getpass('Token: ')
    channel  = args.channel             or 'laundromatic'
    delay    = args.delay               or timedelta(minutes = 30)
    gpiopin  = args.gpiopin             or 4
    loglevel = args.loglevel            or logging.INFO
    prefix   = args.prefix              or '!'
    watchers = args.watchers            or []
    users    = dict.fromkeys(watchers)  or {}
    

    # initalize GPIO watching
    light_sensor = gpiozero.DigitalInputDevice(gpiopin, pull_up = True)

    # datetime since laundry was last done
    laundry_done_last = datetime.now() - timedelta(days = 365)
    threshold_delta   = timedelta(minutes = delay)

    # set log level
    logger.setLevel(loglevel)

    logger.debug(f'All arguments passed to script: {args}')
    logger.debug(f'token:    {token}')
    logger.debug(f'channel:  {channel}')
    logger.debug(f'delay:    {delay}')
    logger.debug(f'gpiopin:  {gpiopin}')
    logger.debug(f'loglevel: {loglevel}')
    logger.debug(f'prefix:   {prefix}')
    logger.debug(f'watchers: {watchers}')
    logger.debug(f'users:    {users}')

    # discord client
    # NOTE: intents are needed to get users by id, 
    #   this must be set in the Discord Dev Center:
    #       https://discord.com/developers/applications/ ->
    #       Application -> Bot -> SERVER MEMBERS INTENT (ON)
    intents         = discord.Intents.default()
    intents.members = True
    #client          = discord.Client(intents = intents)
    client          = commands.Bot(command_prefix = prefix,
                                   intents        = intents)


    #--[ CUSTOM FUNCTIONS ]--------------------------------------------------------------------------------------------

    # sets user details for all users
    async def set_user_details(users):
        user = None
        logger.debug(f'users: {users}')
        for index, user_id in enumerate(users):
            logger.debug(f'user id: {user_id}')
            if user_id in users:
                logger.debug( 'user id in users')
                logger.debug(f'users[user_id]: {users[user_id]}')
                logger.debug(f'bool:           {bool(users[user_id])}')
                if not users[user_id]:
                    user = await client.fetch_user(user_id)
                    if(user):
                        logger.debug(f'acquired user details: {user}')
                        users[user_id] = user
                    else:
                        logger.error('unable to acquire user by user_id')
                else:
                    logger.debug('user already set')
        return users

    # send DM to a single user
    async def send_dm(user, message = 'test message'):
        logger.debug(f'sending DM to: {user}')
        logger.debug(f'message:       {message}')
        await user.send(message)
        return

    # send DMs to many users
    async def send_dms(users, message = 'test message'):
        logger.debug( 'sending DMs to many users')
        logger.debug(f'users: {users}')
        for index, user_id in enumerate(users):
            await send_dm(users[user_id], message)
        return

    # send message to specific channel
    async def send_channel_message(name = channel, message = 'test message'):
        logger.debug(f'channel name: {name}')
        channel_obj = discord.utils.get(client.get_all_channels(), name = name)
        if channel_obj:
            logger.debug(f'channel:    {channel_obj}')
            logger.debug(f'channel.id: {channel_obj.id}')
            logger.info( f'Sending message to #{channel_obj}: {message}')
            await channel_obj.send(message)
        return

    # send list of current users
    async def message_current_users(ctx, user_message = ''):
        current_users = '\n'
        nonlocal users
        if users:
            logger.info(f'Current Users:\n{users}')
            current_users      =  'Watch List:\n```properties\n'
            for index, user_id in enumerate(users):
                current_users += f'{users[user_id].name} {users[user_id].id}\n'
            current_users     +=  '```'
        else:
            no_users_message   = 'No current users watching'
            current_users      = no_users_message
            logger.info(no_users_message)

        if current_users:
            complete_message   = user_message + current_users
            logger.info(f'complete_message: {complete_message}')
            await ctx.send(complete_message)

            # if command was received on a DM, also send output to a channel
            if ctx.message.channel.type == discord.ChannelType.private:
                logger.debug(f'Sending message of current_users:\n{current_users}')
                await send_channel_message(message = complete_message)
        return

    # send message and dms when laundry is done
    async def message_laundry_done(time_done = datetime.now()):
        nonlocal users
        format           = "%a, %b %-d @ %H:%M:%S (Arizona)" 
        arizona_datetime = time_done - timedelta(hours = 7) # Arizona is UTC -0700
        time_done_string = arizona_datetime.strftime(format)
        message          = f'Washing cycle complete on `{time_done_string}`'
        logger.debug(f'{message}')
        await send_dms(users, message = message)
        await send_channel_message(message = message)
        return

    # wrapper function to call message_laundry_done
    #   NOTE: needed by gpiozero, since it can't await async functions
    def laundry_done_wrapper():

        nonlocal laundry_done_last
        nonlocal threshold_delta
        
        now = datetime.now()
        delta_since_last_done = now - laundry_done_last

        logger.info( f'laundry done wrapper called at: {str(now)}')
        logger.info( f'laundry was last done at:       {str(laundry_done_last)}')
        logger.info( f'delta_since_last_done:          {str(delta_since_last_done)}')
        logger.debug(f'threshold_delta:                {threshold_delta}')
        logger.debug(f'over threshold:                 {bool(delta_since_last_done > threshold_delta)}')

        if delta_since_last_done > threshold_delta:
            laundry_done_last = now
            logger.debug(f'last laundry load was done beyond the threshold duration')
            logger.debug(f'set new laundry_done_last value: {laundry_done_last}')
            logger.debug(f'client.loop:                     {client.loop}')
            client.loop.create_task(message_laundry_done(now))
        return


    #--[ COMMANDS ]----------------------------------------------------------------------------------------------------

    # get user ID by username
    @client.command(name = 'id', aliases = ['get-id', 'user-id', 'uid'])
    async def get_id_by_username(ctx, username = '', send_message = True):

        user_id = None

        # if no username was passed as an argument, 
        #   assume the user passed their own username
        if not username:
            logger.debug( 'no argument passed to command')
            logger.debug(f'netting argument to author: {ctx.author.name}')
            user_id = str(ctx.author.id)
            message = f'`{ctx.author.name}`\'s user ID is:\n`{user_id}`'
            if send_message:
                await ctx.send(message)
            return user_id

        logger.info(f'attempting to find user ID for: {username}')

        # get a member that matches the username, from all members of the guild
        member = discord.utils.get(client.get_all_members(), name = username)

        if member:
            logger.debug(f'member:    {member}')
            logger.info( f'member.id: {member.id}')
            user_id = member.id
            message = f'`{username}`\'s user ID is:\n`{user_id}`'
            logger.info(message)
        else:
            message = f'Unable to acquire user ID for `{username}`'
            logger.warning(message)

        if send_message:
            await ctx.send(message)

        return user_id

    # list all current watchers
    @client.command(name = 'watchlist', aliases = ['watchers', 'list', 'users'])
    async def list_watchers(ctx):
        await message_current_users(ctx)
        return

    # send a DM to all watchers
    @client.command(name = 'broadcast', aliases = ['dm'])
    async def send_dm_to_all_watchers(ctx, message = 'test DM to all watchers'):
        nonlocal users
        await send_dms(users, message)
        return

    # add user to watch list
    @client.command(name = 'watch', aliases = ['add', 'subscribe'])
    async def add_user_to_watchers(ctx, *user_ids_or_names):

        # if no user IDs or usernames were passed as arguments, 
        #   assume the user passed their own user ID
        if not user_ids_or_names:
            logger.debug( 'No arguments passed to command')
            logger.debug(f'Using author ID {ctx.author.id} as argument')
            user_ids_or_names = [ str(ctx.author.id) ]

        logger.debug(f'user_ids_or_names: {user_ids_or_names}')

        # include nonlocal users 
        nonlocal users
        logger.debug(f'nonlocal users: {users}')

        user_message = ''
        # iterate over all user IDs or usernames
        for index, user_id in enumerate(user_ids_or_names):

            username = ''
            # if an argument wasn't numeric, try to get the user ID from the username
            if not user_id.isnumeric():
                username = user_id
                logger.warning(f'The argument is not numeric ({username})')
                logger.info(   f'Trying to get user ID from username...')
                user_id = str(await get_id_by_username(ctx, username, send_message = False))
                logger.debug(  f'user_id after get_id_by_username: {user_id}')
                logger.debug(  f'if not user_id ({bool(not user_id)}) or user_id == None ({bool(user_id == None)}): ')
                if not user_id or user_id == None:
                    logger.warning(f'Unable to get user ID for username: {username}')
                    continue

            # if the user ID is not in the users dict, 
            #   1. add the user ID as a new key
            #   2. fetch user details
            #   3. DM the user to let them know they've been added
            logger.debug(f'if user_id ({user_id}) not in users: {bool(user_id not in users)}')
            if user_id not in users:
                logger.info(f'User ID {user_id} not in users list')
                users[user_id] = None
                logger.debug(f'Users: {users}')
                users = await set_user_details(users)
                user_message += f'Added `{users[user_id].name}` to the watch list\n'
                add_message   = f'You have been added to the watch list'
                if users[user_id].id != ctx.author.id:
                    user_message += f'(requested by `{ctx.author.name}`)\n'
                    add_message  += f' by `{ctx.author.name}`'
                await send_dm(users[user_id], message = add_message)
            else:
                user_message +=  f'User `{username or user_id}` is already on the watch list\n'

            logger.info(user_message)

        await message_current_users(ctx, user_message)
        return

    # # handle errors on adding users
    # @add_user_to_watchers.error
    # async def add_user_to_watchers_error(ctx, error):
    #     logger.error(f'{error}')
    #     if isinstance(error, commands.BadArgument):
    #         await ctx.send('[ERROR] Invalid user ID(s)')
    #     return

    # remove user from watch list
    @client.command(name = 'stop', aliases = ['remove', 'unsubscribe', 'unwatch'])
    async def remove_user_from_watchers(ctx, *user_ids_or_names):

        # if no user IDs or usernames were passed as arguments, 
        #   assume the user passed their own user ID
        if not user_ids_or_names:
            logger.debug( 'No arguments passed to command')
            logger.debug(f'Using author ID {ctx.author.id} as argument')
            user_ids_or_names = [ str(ctx.author.id) ]

        logger.debug(f'user_ids_or_names: {user_ids_or_names}')

        # include nonlocal users
        nonlocal users
        logger.debug(f'nonlocal users: {users}')

        user_message = ''
        # iterate over all user IDs or usernames
        for index, user_id in enumerate(user_ids_or_names):

            username = ''
            # if an argument wasn't numeric, try to get the user ID from the username
            if not user_id.isnumeric():
                username = user_id
                logger.warning(f'The argument is not numeric ({username})')
                logger.info(   f'Trying to get user ID from username...')
                user_id = str(await get_id_by_username(ctx, username, send_message = False))
                logger.debug(  f'user_id after get_id_by_username: {user_id}')
                logger.debug(  f'if not user_id ({bool(not user_id)}) or user_id == None ({bool(user_id == None)}): ')
                if not user_id or user_id == None:
                    logger.warning(f'Unable to get user ID for username: {username}')
                    continue

            # if the user ID is in the users dict: 
            #   1. message the user they are being removed from watch list
            #   2. delete the key from the users dict
            #   3. send a confirmation message the user was removed
            logger.debug(f'if user_id ({user_id}) in users: {bool(user_id in users)}')
            if user_id in users:
                user_message   += f'Removed `{users[user_id].name}` from the watch list\n'
                remove_message  = f'You have been removed from the watch list'
                if users[user_id].id != ctx.author.id:
                    user_message   += f'(requested by `{ctx.author.name}`)\n'
                    remove_message += f' by `{ctx.author.name}`'
                await send_dm(users[user_id], message = remove_message)
                del users[user_id]
            else:
                user_message +=  f'User `{username or user_id}` is not on the watch list\n'
                
            logger.info(user_message)

        await message_current_users(ctx, user_message)
        return


    #--[ READY ]-------------------------------------------------------------------------------------------------------

    @client.event
    async def on_ready():

        # set an online message, log it, and send it to the management channel
        online_message = f'{client.user.name} is online and watching laundry'
        logger.info(online_message)
        await send_channel_message(channel, message = online_message)

        # if users are present, 
        #   set their user details and send them all a message too
        nonlocal users
        logger.debug(f'nonlocal users: {users}')
        if users:
            users = await set_user_details(users)
            await send_dms(users, message = online_message)

        # set up the watcher function on the GPIO light sensor
        light_sensor.when_activated = laundry_done_wrapper

        return


    #--[ DISCONNECT ]--------------------------------------------------------------------------------------------------

    @client.event
    async def on_disconnect():
        logger.warning(f'{client.user} disconnected from Discord')
        return


    #--[ ERROR ]-------------------------------------------------------------------------------------------------------

    @client.event
    async def on_error(event, *args, **kwargs):
        message = args[0]
        logger.error(f'Error Message: {message}\n{traceback.format_exc()}')
        error_message  = f'{client.user} has encountered an error. Check server log for details.' 
        await send_dms(users, message = error_message)
        return


    #--[ MESSAGE ]-----------------------------------------------------------------------------------------------------

    @client.event
    async def on_message(message):

        # if the message is from the bot, return
        if message.author == client.user:
            return

        # process commands 
        #   NOTE: required when using the on_message event
        await client.process_commands(message)

    if token:
        client.run(token)
    else:
        logger.error('No token provided')

    return


#==[ COMMAND LINE ]========================================================================================================================

if __name__ == "__main__":

    # important values
    token    = None # REQUIRED
    channel  = None # Defaults in main() to '#laundromatic'
    delay    = None # Defaults in main() to '30' (minute timedelta)
    gpiopin  = None # Defaults in main() to '4'
    loglevel = None # Defaults in main() to 'info'
    prefix   = None # Defaults in main() to '!'   
    watchers = []   # Optional - user IDs

    # the above values get set from (in order):
    #   1. JSON config file
    #   2. environment variables
    #   3. command line arguments
    #   4. prompts to the user - in main()
    #   5. using bot commands in a direct message (DM) or management channel


    #--[ 1. JSON CONFIG ]----------------------------------------------------------------------------------------------

    config_file = 'config.json'
    if os.path.exists(config_file):
        with open(config_file) as json_config_file:
            config = json.load(json_config_file)
            if 'token'    in config:
                token     = config['token']

            if 'channel'  in config:
                channel   = config['channel']

            if 'delay'    in config:
                delay     = config['delay']

            if 'gpiopin'  in config:
                gpiopin   = config['gpiopin']

            if 'loglevel' in config:
                loglevel  = config['loglevel']

            if 'prefix'   in config:
                prefix    = config['prefix']

            if 'watchers' in config:
                if all(config['watchers']):
                    watchers = config['watchers']


    #--[ 2. ENVIRONMENT VARIABLES ]------------------------------------------------------------------------------------

    if not token:
        token    = os.environ.get('LAUNDROMATIC_TOKEN')

    if not channel:
        channel  = os.environ.get('LAUNDROMATIC_CHANNEL')

    if not delay:
        delay    = os.environ.get('LAUNDROMATIC_DELAY')

    if not gpiopin:
        gpiopin  = os.environ.get('LAUNDROMATIC_GPIOPIN')    

    if not loglevel:
        loglevel = os.environ.get('LAUNDROMATIC_LOGLEVEL')

    if not prefix:
        prefix   = os.environ.get('LAUNDROMATIC_PREFIX')

    if not watchers:
        watchers = os.environ.get('LAUNDROMATIC_WATCHERS')
        if watchers:
            watchers = watchers.split() # convert space separated string to list


    #--[ 3. COMMAND LINE ARGUMENTS ]-----------------------------------------------------------------------------------

    parser = argparse.ArgumentParser()

    # token
    required     = bool(not token)
    group_tokens = parser.add_mutually_exclusive_group(required = required)    

    def decode_base64_token(base64_token):
        return base64.b64decode(base64_token).decode('UTF-8')

    group_tokens.add_argument('-t',
                              '--token',
                              dest = 'token',
                              type = str,
                              help = 'Token')

    group_tokens.add_argument('-b',
                              '--base64_token',
                              dest = 'token',
                              type = decode_base64_token,
                              help = 'Token (base64)')
    # channel
    parser.add_argument('-c',
                        '--channel',
                        dest = 'channel',
                        type = str,
                        help = 'Channel Name for management')

    # delay
    def set_delay_timedelta(minutes):
        return timedelta(minutes = int(minutes) or 30)

    parser.add_argument('-d',
                        '--delay',
                        dest = 'delay',
                        type = set_delay_timedelta,
                        help = 'Delay (minutes) between "complete" messages')

    # gpiopin
    parser.add_argument('-g',
                        '--gpio',
                        '--pin',
                        dest = 'gpiopin',
                        type = int,
                        help = 'GPIO pin for digital output (DO) from light sensor (LDR)')

    # loglevels
    loglevels = {
        'debug'     : logging.DEBUG,
        'info'      : logging.INFO,
        'warning'   : logging.WARNING,
        'error'     : logging.ERROR,
        'critical'  : logging.CRITICAL,
    }

    def set_log_level(level):
        if level is None:
            level = 'info'
        if level not in loglevels:
            raise ValueError(f"Log Level must be one of: {' | '.join(loglevels.keys())}")
        return loglevels[level]

    parser.add_argument('-l',
                        '--loglevel',
                        dest = 'loglevel',
                        type = set_log_level,
                        help = f"Logging Level ({' | '.join(loglevels.keys())})")

    # prefix
    parser.add_argument('-p',
                        '--prefix',
                        dest = 'prefix',
                        type = str,
                        help = 'Prefix for commands')

    # watchers
    group_watchers = parser.add_mutually_exclusive_group(required = False)
    
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


    # parse arguments
    args, unknown = parser.parse_known_args()

    # set args values
    args.token      = args.token    or token
    args.channel    = args.channel  or channel
    args.delay      = args.delay    or delay
    args.gpiopin    = args.gpiopin  or gpiopin    
    args.loglevel   = args.loglevel or loglevel
    args.prefix     = args.prefix   or prefix
    args.watchers   = args.watchers or watchers

    # pass all args to main
    main(args)
