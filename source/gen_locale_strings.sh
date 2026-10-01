#!/bin/bash
# Regenerate the translation template and merge into each language.
# Run from inside Docker: docker exec lotro-bot sh gen_locale_strings.sh
set -e

xgettext --language=Python --keyword=_ --from-code=UTF-8 \
    --output=locale/messages.pot \
    bot.py cogs/*.py

msgmerge --update --backup=none locale/es/LC_MESSAGES/messages.po locale/messages.pot
msgmerge --update --backup=none locale/fr/LC_MESSAGES/messages.po locale/messages.pot

echo "Done. Translate new strings marked with #, fuzzy in the .po files."
