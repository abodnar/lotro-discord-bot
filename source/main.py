#!/usr/bin/env python3

import logging

from bot import Bot


class _SuppressReconnectTraceback(logging.Filter):
    def filter(self, record):
        if record.exc_info and 'reconnect' in record.getMessage().lower():
            record.exc_info = None
            record.exc_text = None
        return True


def main():
    bot = Bot()
    logging.getLogger('discord').setLevel(logging.INFO)
    logging.getLogger('discord.client').addFilter(_SuppressReconnectTraceback())
    # bot.py's basicConfig root handler already prints discord.py records;
    # a second handler from run() would print each one twice.
    bot.run(bot.token, log_handler=None)
    bot.logger.info("Shutting down.")


if __name__ == '__main__':
    main()
