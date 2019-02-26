#!/usr/bin/python3
#
# Migrate the old repr-based file to the new JSON-based one.
#

import ast

try:
    from msgpack import dumps
    t = 'msgpack'
except ImportError:
    import json
    t = 'JSON'
    dumps = lambda data : json.dumps(data).encode('utf-8')

def migrate(file):
    print('Loading commands from the file...')
    try:
        with open(file, 'r') as f:
            data = ast.literal_eval(f.read())
    except:
        print('ERROR: Could not load the commands list, are you sure it has not'
            ' already been converted?')
        return False

    print('Converting commands list to {}...'.format(t))
    data = dumps(data)

    if type(data) == str:
        data = data.encode('utf-8')

    print('Writing commands back to the file...')
    with open(file, 'wb') as f:
        f.write(data)

    print('Done!')

    return True

if __name__ == '__main__':
    import argparse
    _parser = argparse.ArgumentParser()
    _parser.add_argument('file',
        help = 'The tempcmds file to "upgrade".')
    args = _parser.parse_args()

    migrate(args.file)
