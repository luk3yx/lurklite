#!/usr/bin/python3
#
# lurk lite: A "lightweight™" version of lurk.
#

import argparse, configparser, os, miniirc, re, sys, tempcmds

# Process arguments
_parser = argparse.ArgumentParser()
_parser.add_argument('config_file',
    help = 'The config file to use with lurklite.')
_parser.add_argument('--verbose', '--debug', action = 'store_true',
    help = 'Enable verbose/debugging mode.')
_parser.add_argument('-v', '--version', action = 'version',
    version = 'lurklite v0.1.0')
_args = _parser.parse_args()
del _parser

# Error and quit
def err(msg, *args, **kwargs):
    if len(args) > 0 or len(kwargs) > 0:
        msg = msg.format(*args, **kwargs)
    print('ERROR:', msg, file = sys.stderr)
    raise SystemExit(1)

# Load the config file
config = configparser.ConfigParser()
config.read(_args.config_file)

if 'core' not in config:
    err('Invalid or non-existent config file!')

# Make sure config values exist
def _conf_assert(section, *keys):
    for key in keys:
        req = None
        if type(key) == tuple:
            key, req = key

        if key not in config[section]:
            err('Required config value {} missing (in section {})!',
                repr(key), repr(section))
        elif req:
            try:
                req(config[section][key])
            except:
                err('Config value {} (in section {}) contains an invalid {}.',
                    repr(key), repr(section), req.__name__)

_conf_assert('core', 'command_db', 'prefix')

# Add the comamnd handler config
if 'tempcmds' in config:
    tempcmds.config = config['tempcmds']

# Get the global ignores list
def process_ignores(section):
    res = set()
    for victim in config[section].get('ignored', '').split(','):
        victim = victim.strip()
        res.add(re.escape(victim).lower().replace('\\*', '.*'))
    return re.compile('^(' + ')|('.join(res) + ')$')

global_ignores = process_ignores('core')
prefs = {}

# Try getting the "reply_on_invalid" config line
try:
    _reply = config['core'].getboolean('reply_on_invalid')
except:
    err('Config value \'reply_on_invalid\' (in section \'core\') contains an'
        ' invalid boolean.')

# Create the commands database
commands = tempcmds.CommandDatabase(config['core']['command_db'],
    prefix = config['core']['prefix'], reply_on_invalid = _reply)
del _reply

# Get the "enable_static_cmds" flag
try:
    static_cmds = config['core'].getboolean('enable_static_cmds', True)
except:
    err('Config value \'enable_static_cmds\' (in section \'core\') contains an'
        ' invalid boolean.')

if static_cmds:
    import static_cmds
    static_cmds.tempcmd_db, static_cmds.prefs = commands, prefs

# Handle PRIVMSGs
@miniirc.Handler('PRIVMSG')
def handle_privmsg(irc, hostmask, args):
    # Check for ignored users
    h = '{}!{}@{}'.format(*hostmask)
    _ignores = prefs[irc].get('ignored')
    if global_ignores.match(h) or (_ignores and _ignores.match(h)):
        return

    # [off] handling
    msg = args[-1][1:]
    reply_prefix = ''
    if msg.startswith('[off]'):
        reply_prefix = '[off]'
        msg = msg[5:]

    # Relayed nick handling
    if msg.startswith('<') and msg.endswith('>') and msg.isalnum():
        _nick = msg.split(' ', 1)[0][1:-1]
        hostmask = (
            _nick + '@' + hostmask[0],
            hostmask[1],
            hostmask[2] + '/relayed/' + _nick
        )

    # Remove any leading/trailing spaces
    msg      = msg.strip(' \t\r\n')
    args[-1] = ':' + msg
    msg      = msg.lower()

    # Unprefixed commands here
    if msg.startswith('yay'):
        irc.msg(args[0], reply_prefix + '\u200bYay!')
    elif msg.startswith('ouch'):
        irc.msg(args[0], reply_prefix + '\u200bOuch.')
    elif msg.startswith(irc.nick.lower() + '!'):
        irc.msg(args[0], reply_prefix + nick + '!')
    else:
        # "Static" commands
        if static_cmds and msg.startswith(commands.prefix):
            cmd = msg[len(commands.prefix):].split(' ', 1)[0]

            if cmd in static_cmds.commands:
                # Decide if the user is an admin
                if type(irc).__name__ == 'Discord':
                    h = hostmask[1]
                else:
                    h = hostmask[2]
                admins = prefs[irc].get('admins')
                is_admin = admins and h.lower() in admins and h

                # Launch the command
                args[-1] = args[-1][len(cmd) + 3:]
                return static_cmds.commands[cmd](irc, hostmask, is_admin, args)

        # Call the command handler
        commands(irc, hostmask, args, reply_prefix = reply_prefix or None)

# Add extra items
def _add_extras(c, irc):
    p = {}
    prefs[irc] = p

    # Process the ignores list
    if 'ignored' in c:
        p['ignored'] = process_ignores(section)

    # Process the admins list
    if 'admins' in c:
        p['admins'] = set()
        for admin in c['admins'].split(','):
            p['admins'].add(admin.lower().strip())

    # Add the tempcmds log channel
    if 'tempcmd_log' in c:
        p['tempcmd_log'] = c['tempcmd_log']

# Get the IRC servers to connect to
_servers = {}
for section in config.sections():
    if section == 'irc' or section.startswith('irc.'):
        _conf_assert(section, 'ip', ('port', int), 'nick', 'channels')

        c = config[section]
        kwargs = {}

        for i in 'ident', 'realname', 'ns_identity', 'connect_modes', \
          'quit_message':
            if i in c:
                kwargs[i] = c[i]

        # Add the SSL option
        ssl = None
        if 'tls' in c:
            ssl = 'tls'
        elif 'ssl' in c:
            ssl = 'ssl'

        if ssl:
            try:
                kwargs['ssl'] = c.getboolean(ssl)
            except:
                err('Config value \'ssl\' (in section {}) contains an invalid'
                    ' boolean.', repr(section))

        # Create the IRC object
        irc = miniirc.IRC(c['ip'], int(c['port']), c['nick'],
            c['channels'].split(','), auto_connect = False,
            debug = _args.verbose, **kwargs)
        _servers[section] = irc

        # Add the ignores list
        _add_extras(c, irc)


# Get the Discord bot account (if any)
if 'discord' in config:
    try:
        import miniirc_discord
    except ImportError:
        err('miniirc_discord is not installed, and a Discord account has been'
            'specified in the config file!')

    _conf_assert('discord', 'token')

    c = config['discord']

    # Create the Discord object
    irc = miniirc_discord.Discord(c['token'], 0,
        c.get('nick', '???'), debug = _args.verbose)
    _servers['Discord'] = irc

    # Add the ignores list
    _add_extras(c, irc)

# Mass connect
for name in _servers:
    irc = _servers[name]
    irc.debug('Connecting to ' + repr(name) + '...')
    irc.connect()
irc.debug('Finished connecting to servers!')

# Delete unrequired globals
del c, irc, kwargs, _servers

# miniirc update reminder™
if miniirc.ver < (1,0,8):
    print('You are not running the latest version of miniirc™.')

# Nuke more unused variables
del argparse, _args
del sys.modules['argparse']
