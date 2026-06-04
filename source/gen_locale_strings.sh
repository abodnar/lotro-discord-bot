#!/bin/bash
# Regenerate the translation template and merge into each language.
# Run from inside Docker: docker exec lotro-bot sh gen_locale_strings.sh
set -e

xgettext --language=Python --keyword=_ --from-code=UTF-8 \
    --output=locale/messages.pot \
    bot.py calendar_cog.py config_cog.py dev_cog.py \
    raid_cog.py time_cog.py \
    cogs/*.py

msgmerge --update locale/es/LC_MESSAGES/messages.po locale/messages.pot
msgmerge --update locale/fr/LC_MESSAGES/messages.po locale/messages.pot

echo "Done. Translate new strings marked with #, fuzzy in the .po files."
