# flake8: noqa

__version__ = '1.7.0'

import asyncio
from sys import platform, version_info

from .paste import Client

# fix for python 3.8
if platform == 'win32' and version_info >= (3, 8):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())