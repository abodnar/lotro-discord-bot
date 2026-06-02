#!/usr/bin/env python3

import logging

from bot import Bot

def main():
    bot = Bot()
    handler = logging.StreamHandler()
    bot.run(bot.token, log_handler=handler)
    bot.logger.info("Shutting down.")


if __name__ == '__main__':
    main()
