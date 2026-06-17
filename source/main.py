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
    handler = logging.StreamHandler()
    logging.getLogger('discord.client').addFilter(_SuppressReconnectTraceback())
    bot.run(bot.token, log_handler=handler)
    bot.logger.info("Shutting down.")


if __name__ == '__main__':
    main()
