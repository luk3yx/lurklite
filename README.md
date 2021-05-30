<div align="center">
    <h1>
        <img src="./lurklite.png"
            width="128" alt=" " />
        <br/>
        lurklite
    </h1>
</div>

![Python 3.6+] [![Available on PyPI.]](https://pypi.org/project/lurklite/) [![License: AGPLv3]](https://github.com/luk3yx/miniirc/blob/master/LICENSE.md)

[Python 3.6+]: https://img.shields.io/badge/python-3.6+-blue.svg
[Available on PyPI.]: https://img.shields.io/pypi/v/lurklite.svg
[License: AGPLv3]: https://img.shields.io/pypi/l/lurklite.svg

luk3yx's "lightweight™" IRC and Discord bot (excluding commands).

## Official bot

If you can't or don't want to run your own bot, you can request that the
official bot be added to your channel. The official bot is on a few IRC
networks, most notably Libera Chat and xeroxIRC. PM `luk3yx` there if you want
the bot on an IRC channel you own. *Note that this IRC bot is running
[Sopel](https://github.com/sopel-irc/sopel) and not lurklite, hopefully I'll
release the API shim it uses sometime.*

Alternatively, if you use Discord, you can use [https://bit.ly/lurkdiscord] to
add lurklite (without any permissions) to your Discord guild/server.

[https://bit.ly/lurkdiscord]: https://discordapp.com/oauth2/authorize?&client_id=525031486047387648&scope=bot&permissions=0

## Installation

To install lurklite, you can simply install it with `pip`
(`sudo pip3 install lurklite` on most GNU/Linux distributions). After
installation, you should be able to run `lurklite` (or `python3 -m lurklite`).

## Config file

The lurklite config file has a format similar to `ini` files. It must have a
`[core]` section with the following values:

```ini
[core]
# The tempcmd db, commands added with .tempcmd are stored here.
# If you have msgpack installed, this database will be slightly smaller and
#   faster to read/write to/from.
command_db = /path/to/tempcmd/database

# The bot's command prefix.
prefix     = .

# (Optional) A list of hostmasks to ignore.
# ignored  = *!*@*/bot/*, baduser!*@*

# (Optional) Disable "Yay!" and "Ouch." replies.
# disable_yay  = false
# disable_ouch = false
```

### Connecting to IRC servers

You can then create sections starting with `irc.` (for example `irc.mynetwork`)
to connect to IRC servers:

```ini
[irc.mynetwork]
ip   = irc.example.com
port = 6697
nick = testbot
channels = #botwar,#other-channel

# List of hostmasks to ignore (optional)
# ignored = *!*@*/bot/*, *!*sopel*@*

# List of hostnames for admins
# admins = unaffiliated/user
```

The following optional values may be added to the above config, and are sent
directly to [miniirc]:

```ini
connect_modes = +g
ident         = ident
ns_identity   = username password
quit_message  = Quit message
realname      = realname
ssl           = true
```

### Connecting to Discord servers

You can also connect to Discord servers (via [miniirc_discord]) with the
following config section:

```ini
[discord]
# You need miniirc_discord installed for this to work.
token    = your-discord-token

# Using user IDs instead of username#discriminator improves security.
# admins = username#1234, userid
```

You can only have one Discord connection per bot process, and lurklite will use
slightly more RAM if `[discord]` exists, as [miniirc_discord] will be imported
(and if you don't specify a Discord bot token, [miniirc_discord] won't be
imported).

### Storing the command database in an ASCII-safe format.

If you have the habit of opening and modifying `commands.db` in a text editor,
it might be a good idea to store it with JSON by adding the following to your
configuration file:

```ini
[tempcmds]
db_format = json
```

*Note that this will very slightly degrade performance and increase the size,
however this should be a negligible amount for most purposes.*

## Creating commands

Once your bot has connected to IRC (or Discord), you can use `tempcmd` to
create (permanent) commands. You can either do
`.tempcmd <command> <type> <code>` to add a tempcmd with a set type, or
`.tempcmd <command> <code>` to auto-detect the type (as long as the first word
in `<code>` is not a valid type).

*For now, tempcmds.py has a list of code types/formats and what they do.*

To delete commands, you can use `tempcmd del/delete/remove <command>`. To create
a command called `del`, `delete` or `remove`, you can prepend your bot's prefix
to the command name.

### Creating non-"tempcmd" commands

If you want more fine-grained control over a command, you can add a
`custom_cmds` line to the `[core]` section of config.ini. The file specified
will be loaded and can define more powerful commands, for example:

```py
# A simple version command
# The "requires_admin" parameter is optional and defaults to False.
@register_command('version', requires_admin=False)
def version_command(irc, hostmask, is_admin, args):
    # irc: The miniirc.IRC (or miniirc_discord.Discord) object.
    # hostmask: The hostmask tuple, mostly from miniirc. Note that relayed
    #   messages (for example "<relayed_user> test") will have a hostmask
    #   similar to ('relayed_user@relay_bot', 'relay_bot_ident',
    #       'relay.bot.host/relayed/relayed_user').
    # is_admin: Either `False` or a string with the admin match (for example
    #   a hostmask or Discord tag.
    # args: ["#channel", "command parameters"]
    #   For PMs, "#channel" will be the sender (hostmask[0]).

    irc.msg(args[0], miniirc.version)
```

*You do not have to import anything to get `register_command`.*

If `custom_cmds` is a directory, all `.py` files in that directory will be
loaded. If you want your custom commands file/directory in lurklite's source
directory, you can name it `custom_cmds.py` (or, for directories, `custom_cmds`
or `commands`) to make `git` ignore it.

## Built-in commands

lurklite has the following built-in commands:

 - `reboot`: Reboot the bot.
 - `tempcmd`: Create and delete commands.
 - `version`: Display the miniirc version and quit.

## Migrating from very old versions of lurklite

Older versions of lurklite (pre-v0.1.0) had a `tempcmds.db` created using
`repr()`. This is slow(-ish) and inefficient, so is no longer supported. If you
still have a pre-v0.1.0 `tempcmds.db`, you can run
`tempcmds_migrate.py` to update it to the new msgpack/JSON format.

[miniirc]: https://github.com/luk3yx/miniirc
[miniirc_discord]: https://github.com/luk3yx/miniirc_discord
