import os
import sys

import colorama

from first_setup import setup_telegram_proxy


if getattr(sys, "frozen", False):
    os.chdir(os.path.dirname(sys.executable))
else:
    os.chdir(os.path.dirname(__file__))


if __name__ == "__main__":
    colorama.init()
    setup_telegram_proxy()
