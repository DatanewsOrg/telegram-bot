from typing import Callable, Any
import telegram as tg
import telegram.ext
import logging
import datanews
import re

PERSISTENCE_FILE_NAME = 'datanewsbot'

MONITORS_COMMAND = 'monitors'
SEARCH_COMMAND = 'search'
PUBLISHER_COMMAND = 'publisher'

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def get_usage() -> str:
    return f'''This bot allows you to query news articles from Datanews API.

Available commands:
/help, /start - show this help message.
/{SEARCH_COMMAND} <query> - retrieve news articles containing <query>.
   Example: "/{SEARCH_COMMAND} covid"
/{PUBLISHER_COMMAND} <domain> - retrieve newest articles from <publisher>.
   Example: "/{PUBLISHER_COMMAND} techcrunch.com"
'''


def help_command(update: tg.update.Update, context: tg.ext.CallbackContext) -> None:
    update.message.reply_markdown(get_usage())


def _fetch_data(update: tg.update.Update, context: tg.ext.CallbackContext, fetcher: Callable[[str], Any]) -> None:
    if not context.args:
        help_command(update, context)
        return

    query = '"' + ' '.join(context.args) + '"'
    result = fetcher(query)

    if result['status'] == 401:
        update.message.reply_text('API key is invalid')
        return

    if not result['hits']:
        update.message.reply_text('No news is good news')
        return

    last_message = update.message
    for article in reversed(result['hits']):
        text = article['title'] + ': ' + article['url']
        last_message = last_message.reply_text(text)


def search_command(update: tg.update.Update, context: tg.ext.CallbackContext) -> None:
    def fetcher(query: str) -> Any:
        return datanews.headlines(query, size=10, sortBy='date', page=0, language='en')
    _fetch_data(update, context, fetcher)


def publisher_command(update: tg.update.Update, context: tg.ext.CallbackContext) -> None:
    def fetcher(query: str) -> Any:
        return datanews.headlines(source=query, size=10, sortBy='date', page=0, language='en')
    _fetch_data(update, context, fetcher)


def main(token: str) -> None:
    persistence = tg.ext.PicklePersistence(filename=PERSISTENCE_FILE_NAME)
    updater: tg.ext.Updater = tg.ext.Updater(token=token, persistence=persistence)

    updater.dispatcher.add_handler(tg.ext.CommandHandler('start', help_command))
    updater.dispatcher.add_handler(tg.ext.CommandHandler('help', help_command))
    updater.dispatcher.add_handler(tg.ext.CommandHandler(SEARCH_COMMAND, search_command))
    updater.dispatcher.add_handler(tg.ext.CommandHandler(PUBLISHER_COMMAND, publisher_command))

    updater.dispatcher.add_handler(
        tg.ext.MessageHandler(
            tg.ext.Filters.text & tg.ext.Filters.regex(pattern=re.compile('help', re.IGNORECASE)),
            help_command
        )
    )

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    import sys

    if not sys.argv or len(sys.argv) != 3:
        print("Usage: python main.py <api key> <telegram token>")
        exit(1)

    datanews.api_key = sys.argv[1]
    main(sys.argv[2])
