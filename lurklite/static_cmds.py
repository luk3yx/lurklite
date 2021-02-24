#!/usr/bin/python3
#
# "Static" commands
#

import miniirc, os, sys, lurklite.tempcmds as tempcmds, time

commands = {}

# Register commands
def register_command(*cmds, with_bot=False, requires_admin=False):
    def n(func):
        if requires_admin:
            def wrap_cmd(bot, irc, hostmask, is_admin, args):
                if not is_admin:
                    irc.msg(args[0], 'Permission denied!')
                elif with_bot:
                    return func(bot, irc, hostmask, is_admin, args)
                else:
                    return func(irc, hostmask, is_admin, args)
            wrap_cmd._lurklite_self = True
        else:
            wrap_cmd = func
            if with_bot:
                wrap_cmd._lurklite_self = True

        for cmd in cmds:
            commands[cmd.lower()] = wrap_cmd

    return n

# Load custom commands
def load_cmd_file(file, *, recursive=True):
    if recursive and os.path.isdir(file):
        for f in os.listdir(file):
            if f.endswith('.py'):
                load_cmd_file(os.path.join(file, f), recursive=False)
        return

    # Hacks to add a global variable
    try:
        with open(file, 'r') as f:
            custom_cmds = f.read()
    except:
        print('WARNING: Failed to read a custom commands file:', repr(file))
        return

    module = type(tempcmds)('custom_cmds')
    module.__file__ = file
    module.register_command = register_command
    exec(custom_cmds, module.__dict__)

# A simple version command
@register_command('version')
def _cmd_version(irc, hostmask, is_admin, args):
    irc.msg(args[0], miniirc.version)

# Reboot
@register_command('reboot', requires_admin=True)
def _cmd_reboot(irc, hostmask, is_admin, args):
    irc.notice(args[0], '\x037\x1dRebooting...\x1d')
    print(is_admin, 'ordered me to reboot.')
    time.sleep(0.3)
    argv = (sys.executable, '-m', 'lurklite', *sys.argv[1:])

    if os.name == 'posix':
        # On POSIX systems, just use execvp().
        os.execvp(sys.executable, argv)
    else:
        # Otherwise spawn a child process because Windows has a horribly
        # broken os.execvp implementation.
        import subprocess
        subprocess.Popen(argv)
        os._exit(0)

# Shutdown
@register_command('die', 'shutdown', requires_admin=True)
def _cmd_die(irc, hostmask, is_admin, args):
    irc.notice(args[0], '\x037\x1dGoodbye, cruel world!\x1d')
    print(is_admin, 'ordered me to die.')
    time.sleep(0.3)
    os._exit(0)

# Privs
@register_command('privs', 'privileges')
def _cmd_privs(irc, hostmask, is_admin, args):
    if is_admin:
        irc.msg(args[0], f'{hostmask[0]}: You are an admin: `{is_admin}`.')
    else:
        irc.msg(args[0], f'{hostmask[0]}: You are not an admin!')

# Get a tempcmd name
def _get_tempcmd_name(bot, cmd):
    prefix = bot.cmd_db.prefix
    if cmd.startswith(prefix):
        r_cmd = repr(cmd)
        cmd   = cmd[len(prefix):]
    else:
        r_cmd = repr(prefix + cmd)

    return cmd, r_cmd

# Add and remove "tempcmds"
@register_command('tempcmd', 'tempcmds', with_bot=True, requires_admin=True)
def _cmd_tempcmd(bot, irc, hostmask, is_admin, args):
    """
    Creates a "tempcmd".
    Usage: tempcmd del <command>
    """

    tempcmd_db = bot.cmd_db
    assert tempcmd_db

    # Handle the arguments
    cmd_type = None
    params = args[-1].split(' ', 2)

    if len(params) > 1 and params[0] == 'add':
        cmd_type = False

        if len(params) == 3:
            params = [params[1]] + params[2].split(' ', 1)
        else:
            del params[0]

    if len(params) == 3:
        if tempcmds.command_type_exists(params[1]):
            cmd, cmd_type, code = params
        else:
            cmd, code = params[0], ' '.join(params[1:])
    elif len(params) == 2:
        cmd, code = params
    else:
        return irc.msg(args[0], hostmask[0] + ': Invalid syntax!')

    log = bot._prefs.get(irc, {}).get('tempcmd_log')

    # Get tempcmd info
    if cmd_type is None and cmd == 'info':
        cmd, r_cmd = _get_tempcmd_name(bot, code)

        if cmd not in tempcmd_db:
            return irc.msg(args[0], hostmask[0] + ': The command '
                + r_cmd + ' does not exist or is not a tempcmd!')

        data = tempcmd_db.get(cmd, allowed_aliases=0)

        return irc.msg(args[0], f'{hostmask[0]}: The command {r_cmd} is a '
            f'{data.type!r} tempcmd.\nCode: `{data.code}`')

    # Delete tempcmds
    if cmd_type is None and cmd in ('del', 'delete', 'remove'):
        cmd, r_cmd = _get_tempcmd_name(bot, code)

        if cmd not in tempcmd_db:
            return irc.msg(args[0], hostmask[0] + ': The command '
                + r_cmd + ' does not exist or is not a tempcmd!')

        del tempcmd_db[cmd]
        if log:
            irc.msg(log, f'User {is_admin!r} deleted temporary command '
                f'{r_cmd}.')
        irc.msg(args[0], hostmask[0] + ': Command ' + r_cmd + ' deleted.')
        return

    # Make sure the command does not start with the prefix
    cmd, r_cmd = _get_tempcmd_name(bot, cmd)

    # Make sure the command is not a non-tempcmd
    if cmd.lower() in commands:
        return irc.msg(args[0], hostmask[0] + ': The command ' + r_cmd +
            ' already exists as a normal command!')

    # Add the command
    verb = 'updated' if cmd in tempcmd_db else 'created'
    c = {'code': code}
    if cmd_type:
        c['type'] = cmd_type
    tempcmd_db[cmd] = c

    # Get the type
    if not cmd_type:
        cmd_type = tempcmd_db.get(cmd, allowed_aliases=0).type

    # Return the message
    if log:
        irc.msg(log, f'User {is_admin!r} {verb} temporary command {r_cmd} '
            f'(of type {cmd_type!r}): {code!r}')
    irc.msg(args[0], f'{hostmask[0]}: Command {r_cmd} (of type {cmd_type!r}) '
        f'{verb}.')
