#!/usr/bin/python3
#
# Transitional script
#

assert __name__ == '__main__'
import sys, warnings

# Display warning
print('WARNING: You are calling lurklite.py! lurklite is now a package, and '
    'you should use that directly (for example python -m lurklite).',
    file = sys.stderr)

# Import lurklite
import lurklite.__main__
lurklite.__main__.main()
