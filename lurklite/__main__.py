#!/usr/bin/python3
#
# lurklite: A "lightweight™" version of lurk.
#

import argparse, configparser, miniirc, sys
import lurklite.core as core

# Process arguments
def main():
    parser = argparse.ArgumentParser(prog='lurklite')
    parser.add_argument('config_file',
        help='The config file to use with lurklite.')
    parser.add_argument('--verbose', '--debug', action='store_true',
        help='Enable verbose/debugging mode.')
    parser.add_argument('-v', '--version', action='version',
        version=miniirc.version)
    args = parser.parse_args()

    # Load the config file
    config = configparser.ConfigParser()
    config.read(args.config_file)

    # Create the bot
    try:
        core.Bot(config, debug=args.verbose)
    except core.BotError as e:
        print(f'ERROR: {e}', file=sys.stderr)
        raise SystemExit(1)

# Call main() if required.
if __name__ == '__main__':
    main()
