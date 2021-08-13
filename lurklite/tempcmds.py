#!/usr/bin/python3
#
# Command handler - Processes commands
#

import json, os, re, threading, time, urllib.request, urllib.parse

def web_quote(string):
    return urllib.parse.quote(string, '')

# Try importing msgpack
try:
    import msgpack
except ImportError:
    msgpack = None

# Register "command types"
# You should not use "_hex" for "custom" command types to prevent conflicts
_command_types = {}
_command_ids   = {}
_unknown_regex = []
def register_command_type(type_, use_config=False, *, unknown_re=None,
        _hex=None):
    if unknown_re:
        _unknown_regex.insert(0, (re.compile(unknown_re), type_))

    if type(_hex) == int:
        _command_ids[_hex] = type_

    def n(func):
        if use_config:
            func._tempcmds_config = True
        _command_types[type_] = func
        return func

    return n

# Check if a command type exists
command_type_exists = lambda type_ : type_ in _command_types

# Run a command
def _run_raw_command(cmd_type, code, irc, hostmask, channel, args, *,
        config={}, reply_prefix=None):
    try:
        assert cmd_type in _command_types, 'Invalid command type!'
        handler = _command_types[cmd_type]
        if hasattr(handler, '_tempcmds_config'):
            res = handler(irc, hostmask, channel, code, config, args)
        else:
            res = handler(irc, hostmask, channel, code, args)

        # Sanity check
        assert type(res) == str, 'The command handler did not return a string!'

        # Handle ACTIONs separately
        if res.startswith('\x1b') and res.endswith('\x1b'):
            res    = res[1:-1]
            action = True
        else:
            action = False

        # Make sure the result is a sane length
        if hasattr(irc, 'msglen'):
            maxlen = irc.msglen - 112
        else:
            maxlen = 400

        if len(res) > maxlen:
            res = res[:maxlen] + '...'

        mention = hostmask[0]
        if not mention.endswith('>'):
            mention += ':'

        # Display the output
        if action:
            irc.me(channel, '\u200b' + res)
        elif reply_prefix:
            irc.msg(channel, reply_prefix + mention, res)
        else:
            irc.msg(channel, mention, res)

    except Exception as err:
        irc.notice(channel, '\x034Error running command!\x0f\n' \
            '{}: {}'.format(type(err).__name__, err))
        if irc.debug_file:
            raise

# Command class
class Command:
    type   = 'string'
    config = {}

    def __eq__(self, other):
        return type(self) == type(other) and  self.type == other.type and \
            self.code == other.code

    def as_list(self):
        type_id = self.type

        # Try and use a (more compact) hex code to represent the type
        for _hex in _command_ids:
            if _command_ids[_hex] == type_id:
                type_id = _hex
                break

        return [0, type_id, self.code]

    def as_dict(self):
        return {
            'type': self.type,
            'code': self.code
        }

    def __call__(self, irc, hostmask, args, *, reply_prefix=None):
        return _run_raw_command(self.type, self.code, irc, hostmask, args[0],
            args[1:], config=self.config, reply_prefix=reply_prefix)

    def __init__(self, cmdinfo={}, **kwargs):
        if type(cmdinfo) in (list, tuple) and len(cmdinfo) == 3:
            # cmdinfo: Version (0), type, code
            if cmdinfo[0] == 0:
                cmdinfo = {'type': cmdinfo[1], 'code': cmdinfo[2]}
        elif type(cmdinfo) == str:
            cmdinfo = {'code': cmdinfo}

        cmdinfo.update(kwargs)
        self.code = cmdinfo['code']

        if 'type' in cmdinfo:
            self.type = cmdinfo['type']

            if type(self.type) == int:
                self.type = _command_ids.get(self.type)
        else:
            # Try and guess the command type
            for d in _unknown_regex:
                if d[0].match(self.code):
                    self.type = d[1]
                    break


# Command database
class CommandDatabase:
    _next_update = 0

    def __init__(self, location='commands.db', prefix=None, *,
            reply_on_invalid=False, update_interval=10, config={},
            use_ascii_format=False):
        self.location         = location
        self.reply_on_invalid = reply_on_invalid
        self.prefix           = prefix or '{}|'.format(os.getpid())
        self._config          = config
        self._data            = {}
        self._lock            = threading.Lock()
        self._update_interval = update_interval

        # Note that the database format is auto-detected on load, this only
        # modifies the format used to save the database.
        self.db_format = config.get('db_format', 'msgpack').lower()

    def __repr__(self):
        return 'tempcmds.CommandDatabase(' + repr(self.location) + ')'

    # Update the database
    def _update(self, *, force=False):
        if not force and self._next_update > time.time():
            return

        with self._lock:
            try:
                with open(self.location, 'rb') as f:
                    data = f.read()
                    if not msgpack or data.startswith(b'{'):
                        self._data = json.loads(data.decode('utf-8',
                                                            'replace'))
                    else:
                        self._data = msgpack.loads(data, raw=False)
            except Exception as e:
                print('WARNING: Unable to read commands database!', repr(e))

            self._next_update = time.time() + self._update_interval

    # Get commands
    def get(self, item, *, allowed_aliases=10):
        self._update()
        item = item.lower()
        res  = self._data.get(item)

        # Backwards-compatibility weirdness
        if not res and 'µ' + item in self._data:
            item = 'µ' + item
            res  = self._data[item]

        # Convert the command dict/str to a Command object and resolve aliases.
        if res:
            res = Command(res)
            res.config = self._config

            if res.type == 'alias' and allowed_aliases > 0:
                if res.code.startswith('.'):
                    res.code = res.code[1:]

                return self.get(res.code, allowed_aliases=allowed_aliases - 1)

        return res

    def __getitem__(self, item):
        res = self.get(item)
        if not res:
            raise KeyError(item)
        return res

    def __contains__(self, item):
        self._update()
        item = item.lower()
        return item in self._data or 'µ' + item in self._data

    # Set commands
    def __setitem__(self, item, value):
        if type(value) == dict:
            value = Command(value)

        assert value is None or isinstance(value, Command)

        item = item.lower()
        value = value and value.as_list()

        self._update(force=True)

        with self._lock:
            # Delete "legacy" µcommands
            if 'µ' + item in self._data:
                del self._data['µ' + item]

            if value is None:
                if item in self._data:
                    del self._data[item]
            else:
                self._data[item] = value

            if msgpack and self.db_format != 'json':
                with open(self.location, 'wb') as f:
                    f.write(msgpack.dumps(self._data))
            else:
                with open(self.location, 'w') as f:
                    f.write(json.dumps(self._data))

    # Alias for deleting commands
    def __delitem__(self, item):
        self[item] = None

    # Handle function-like calls
    def __call__(self, irc, hostmask, args, *, reply_prefix=None):
        if args[-1].startswith(self.prefix):
            cmd_args = args[-1].split(' ')
            cmd      = cmd_args[0][len(self.prefix):]
            cmd_args[0] = args[0]
            irc.debug(cmd, cmd_args)

            if cmd in self:
                self[cmd](irc, hostmask, cmd_args, reply_prefix=reply_prefix)
            elif self.reply_on_invalid:
                irc.msg(args[0], f'{hostmask[0]}: Invalid command: {cmd!r}')
            elif irc.debug_file:
                irc.debug(f'User {hostmask} tried to execute invalid command '
                          f'{cmd!r}')

# Handle format strings
@register_command_type('string', _hex=0x00)
def _command_string(irc, hostmask, channel, code, args):
    _a = ' '.join(args)
    try:
        result = code.format(*args, nick=hostmask[0], sender=channel,
            host=hostmask[2], hostmask='{}!{}@{}'.format(*hostmask), args=_a,
            ARGS=_a.upper(), NICK=hostmask[0].upper())
    except IndexError:
        return 'Invalid parameters!'

    return result

# Handle ACTIONs
@register_command_type('action', unknown_re=r'^\*.*\*$', _hex=0x01)
def _command_action(irc, hostmask, channel, code, args):
    if code.startswith('*') and code.endswith('*'):
        code = code[1:-1]

    return _command_string(irc, hostmask, channel, '\x1b' + code + '\x1b', args)

# Display an error if an unknown alias is tried and add aliases to the unknown
#   command RegEx.
@register_command_type('alias', unknown_re=r'^\.', _hex=0x02)
def _command_alias(irc, hostmask, channel, code, args):
    raise RecursionError('Maximum alias recursion depth exceeded.')

# Handle URLs
@register_command_type('url', unknown_re='https://', _hex=0x03)
def _command_url(irc, hostmask, channel, code, args):
    assert code.startswith('http://') or code.startswith('https://')

    code = code.format(*[web_quote(a) for a in args],
        args = web_quote(' '.join(args)), nick = web_quote(hostmask[0]))

    data = urllib.request.urlopen(code).read().decode('utf-8', 'replace')

    while data[-1:] in '\r\n':
        data = data[:-1]

    return data

# Remotely execute Python2 lambdas
@register_command_type('lambda', True, unknown_re='lambda', _hex=0x04)
def _command_lambda(irc, hostmask, channel, code, config, args):
    if not code.startswith('lambda'):
        code = 'lambda ' + code

    code = (f'from __future__ import division, generators, nested_scopes,'
            f'print_function, unicode_literals; __builtins__[\'chr\'] = unichr'
            f'; hostmask = {hostmask}; print("|", ({code}){tuple(args)}, "|")')
    lambda_url = config.get('lambda_url',
        'https://tumbolia-two.appspot.com/py/')
    code = lambda_url + web_quote(code)
    res = _command_url(irc, hostmask, channel, code, args)

    # Horrible workaround
    if lambda_url == 'https://tumbolia-two.appspot.com/py/':
        try:
            res = res.encode('latin-1').decode('utf-8')
        except UnicodeError:
            pass

    if res.startswith('TypeError: <lambda>() takes '):
        res = 'Invalid syntax! This command ' + res[22:] + '.'
    elif res.startswith('| ') and res.endswith(' |'):
        res = res[2:-2]

    return res

# Remotely execute node.js functions
@register_command_type('nodejs', True, unknown_re='function', _hex=0x05)
def _command_nodejs(irc, hostmask, channel, code, config, args):
    code = web_quote(f'({code}){tuple(args)}')
    baseurl = config.get('nodejs_url', 'https://untitled-2khw8qubudu1.runkit.sh/')
    code = (f'{baseurl}?code={code}&nick={web_quote(hostmask[0])}'
            f'&channel={web_quote(channel)}&host={web_quote(hostmask[-1])}')
    return _command_url(irc, hostmask, channel, code, args)
