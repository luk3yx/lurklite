#!/usr/bin/python3
#
# lurklite core
#

import os, miniirc, re, sys, time
import lurklite.tempcmds as tempcmds
static_cmds = None

# The version
miniirc.version = f'lurklite v0.4.19 (powered by {miniirc.version})'

# Throw errors
class BotError(Exception):
    pass

def err(msg, *args, **kwargs):
    if len(args) > 0 or len(kwargs) > 0:
        msg = msg.format(*args, **kwargs)
    raise BotError(msg)

# The bot class
class Bot:
    # Make sure config values exist
    def _conf_assert(self, section, *keys):
        for key in keys:
            req = None
            if type(key) == tuple:
                key, req = key

            if key not in self.config[section]:
                err('Required config value {} missing (in section {})!',
                    repr(key), repr(section))
            elif req:
                try:
                    req(self.config[section][key])
                except:
                    err('Config value {} (in section {}) contains an invalid '
                        '{}.', repr(key), repr(section), req.__name__)

    # Make sure booleans are valid
    def _conf_bool(self, section, key, default=None):
        try:
            return self.config[section].getboolean(key, default)
        except:
            err(f'Config value {key!r} (in section {section!r}) contains an '
                f'invalid boolean.')

    # Convert an ignores list into a RegEx
    def process_ignores(self, section):
        res = set()
        for victim in self.config[section].get('ignored', '').split(','):
            victim = victim.strip()
            if victim:
                res.add(re.escape(victim).lower().replace('\\*', '.*'))

        regex_ignore = self.config[section].get('regex_ignore', '').strip()
        if regex_ignore:
            res.add(regex_ignore)
        return re.compile('^(' + ')|('.join(res) + ')$')

    # Add extra items
    def _add_extras(self, section, c, irc):
        p = {}
        self._prefs[irc] = p

        # Process the ignores list
        if 'ignored' in c:
            p['ignored'] = self.process_ignores(section)

        # Process the admins list
        if 'admins' in c:
            p['admins'] = set()
            for admin in c['admins'].split(','):
                p['admins'].add(admin.lower().strip())

        # Add the tempcmds log channel
        if 'tempcmd_log' in c:
            p['tempcmd_log'] = c['tempcmd_log']

    # Handle PRIVMSGs
    def handle_privmsg(self, irc, hostmask, args):
        # Check for ignored users
        h = '{}!{}@{}'.format(*hostmask)
        _ignores = self._prefs[irc].get('ignored')
        if self.ignores.match(h) or (_ignores and _ignores.match(h)):
            return

        # Handle PMs correctly
        if args[0].lower() == irc.nick.lower():
            args[0] = hostmask[0]

        # [off] handling
        msg = args[-1]
        reply_prefix = ''
        if msg.startswith('[off]'):
            reply_prefix = '[off] '
            msg = msg[5:]

        # Relayed nick handling
        if msg.startswith('<'):
            n = msg.split(' ', 1)
            if n[0].endswith('>') and len(n) > 1 and msg[1].isalnum():
                _nick = n[0][1:-1]
                hostmask = (
                    _nick + '@' + hostmask[0],
                    hostmask[1],
                    hostmask[2] + '/relayed/' + _nick
                )
                msg = n[1]

        # Remove any leading/trailing spaces
        msg      = msg.strip(' \t\r\n')
        args[-1] = msg
        msg      = msg.lower()

        # Unprefixed commands here
        if not self.disable_yay and msg.startswith('yay'):
            irc.msg(args[0], reply_prefix + '\u200bYay!')
        elif not self.disable_ouch and msg.startswith('ouch'):
            irc.msg(args[0], reply_prefix + '\u200bOuch.')
        elif msg.startswith(irc.nick.lower() + '!'):
            irc.msg(args[0], reply_prefix + hostmask[0] + '!')
        else:
            # "Static" commands
            prefix = self.cmd_db.prefix
            if msg.startswith(prefix) and self.static_cmds:
                cmd = msg[len(prefix):].split(' ', 1)[0]

                if cmd in static_cmds.commands:
                    # Decide if the user is an admin
                    admins = self._prefs[irc].get('admins', ())
                    host = hostmask[2]

                    if type(irc).__name__ == 'Discord':
                        # Discord privileges are checked against both the user
                        # ID and username#discriminator.
                        if (host.startswith('discord/user/<') and
                                host[15:-1] in admins):
                            # Admin from user ID
                            is_admin = host[15:-1]
                        elif ('#' in hostmask[1] and
                                hostmask[1].lower() in admins):
                            # Admin from username#discriminator
                            is_admin = hostmask[1]
                        else:
                            # Not an admin
                            is_admin = False
                    else:
                        # IRC privileges are just checked against the hostname.
                        is_admin = host.lower() in admins and host

                    # Launch the command
                    args[-1] = args[-1][len(cmd) + len(prefix) + 1:]
                    func = static_cmds.commands[cmd]
                    if hasattr(func, '_lurklite_self'):
                        return func(self, irc, hostmask, is_admin, args)
                    else:
                        return func(irc, hostmask, is_admin, args)

            # Call the command handler
            self.cmd_db(irc, hostmask, args, reply_prefix=reply_prefix or None)

        # Update the Discord server count
        if 'next_update' in self._prefs[irc] and \
                time.time() > self._prefs[irc]['next_update']:
            c = irc.get_server_count()
            irc.quote('AWAY', ':{} guild{}. | {}help'.format(
                c, '' if c == 1 else 's', self.cmd_db.prefix
            ), tags = {'+discordapp.com/type': 'watching'})
            irc.debug('Updated Discord status text.')
            self._prefs[irc]['next_update'] = time.time() + 60

    # The init function
    def __init__(self, config, *, debug=False):
        self.config = config
        if 'core' not in config:
            err('Invalid or non-existent config file!')
        self._conf_assert('core', 'command_db', 'prefix')
        self.ignores = self.process_ignores('core')
        self._prefs = {}

        # Create the commands database
        if 'tempcmds' in config:
            tempcmds_config = config['tempcmds']
        else:
            tempcmds_config = {}
        self.cmd_db = tempcmds.CommandDatabase(config['core']['command_db'],
            config=tempcmds_config, prefix=config['core']['prefix'],
            reply_on_invalid=self._conf_bool('core', 'reply_on_invalid'))

        # Get the "enable_static_cmds" flag
        global static_cmds
        self.static_cmds = self._conf_bool('core', 'enable_static_cmds', True)

        if self.static_cmds:
            if static_cmds is None:
                import lurklite.static_cmds as static_cmds

            # Get the custom commands file
            custom_cmds = config['core'].get('custom_cmds')
            if custom_cmds:
                static_cmds.load_cmd_file(custom_cmds)
        elif 'custom_cmds' in config['core']:
            print('WARNING: A custom commands path is specified, but static co'
                'mmands are disabled! The custom commands will not be loaded.')

        # Get the disable yay/ouch flags
        self.disable_yay  = self._conf_bool('core', 'disable_yay')
        self.disable_ouch = self._conf_bool('core', 'disable_ouch')

        # Get the IRC servers to connect to
        _servers = {}
        kwargs   = None
        for section in config.sections():
            if section == 'irc' or section.startswith('irc.'):
                self._conf_assert(section, 'ip', ('port', int), 'nick',
                    'channels')

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
                    kwargs['ssl'] = self._conf_bool(section, ssl)

                # Create the IRC object
                irc = miniirc.IRC(c['ip'], int(c['port']), c['nick'],
                    c['channels'].split(','), auto_connect=False,
                    debug=debug, **kwargs)
                _servers[section] = irc

                # Add the ignores list
                self._add_extras(section, c, irc)

        # Get the Discord bot account (if any)
        if 'discord' in config:
            try:
                import miniirc_discord
            except ImportError:
                err('miniirc_discord is not installed, and a Discord account'
                    ' has been specified in the config file!')

            if getattr(miniirc_discord, 'ver', ()) < (0,5,18):
                print('Support for this version of miniirc_discord will be '
                    'removed in the future.')
                kw = {}
            else:
                kw = {'stateless_mode': True}

            self._conf_assert('discord', 'token')

            c = config['discord']

            # Create the Discord object
            irc = miniirc_discord.Discord(c['token'], 0,
                c.get('nick', '???'), debug=debug, **kw)
            _servers['Discord'] = irc

            # Add the ignores list
            self._add_extras('discord', c, irc)
            self._prefs[irc]['next_update'] = 0

        # Mass connect
        for name in _servers:
            irc = _servers[name]
            irc.debug('Connecting to ' + repr(name) + '...')
            irc.Handler('PRIVMSG', colon=False)(self.handle_privmsg)
            try:
                irc.connect()
            except Exception as exc:
                print(f'Failed to connect to {name!r} - '
                      f'{exc.__class__.__name__}: {exc}')
        irc.debug('Finished connecting to servers!')

# miniirc update reminder™
assert miniirc.ver >= (1,4,0), 'lurklite requires miniirc >= v1.4.0!'
if miniirc.ver < (1,6,2):
    print('You are not running the latest version of miniirc™.')
