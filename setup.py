#!/usr/bin/python3

from setuptools import setup

with open('README.md', 'r') as f:
    desc = f.read()

setup(
    name        = 'lurklite',
    version     = '0.4.19',
    packages    = ['lurklite'],
    author      = 'luk3yx',
    description = 'A miniirc-based IRC bot.',
    url         = 'https://github.com/luk3yx/lurklite',
    license     = 'AGPLv3',

    entry_points = {'console_scripts': ['lurklite=lurklite.__main__:main']},

    long_description              = desc,
    long_description_content_type = 'text/markdown',
    install_requires              = ['miniirc>=1.4.0', 'msgpack'],
    python_requires               = '>=3.6',

    classifiers = [
        'Development Status :: 5 - Production/Stable',
        'License :: OSI Approved :: GNU Affero General Public License v3',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ]
)
