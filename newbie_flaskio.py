import os
import logging
import queue
from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import betfairlightweight
from betfairlightweight.filters import (
    streaming_market_filter,
    streaming_market_data_filter,
)
from account_info import accname, accpass, acckey

logging.basicConfig(level=logging.INFO)

path = os.path.realpath(os.path.join(os.curdir, 'certs', accname))
trading = betfairlightweight.APIClient(accname, accpass, acckey, certs=path)
trading.login()

output_queue = queue.Queue()
listener = betfairlightweight.StreamListener(output_queue=output_queue)
stream = trading.streaming.create_stream(listener=listener)

# create filters (US WIN horse racing)
market_filter = streaming_market_filter(
    event_type_ids=['7'],
    country_codes=['US'],
    market_types=['WIN'])
market_data_filter = streaming_market_data_filter(
    fields=['EX_BEST_OFFERS', 'EX_MARKET_DEF'],
    ladder_levels=3)

stream.subscribe_to_markets(
    market_filter=market_filter,
    market_data_filter=market_data_filter,
    conflate_ms=1000)
stream.start(_async=True)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)


@app.route('/')
def index():
    return render_template('index.html')


@socketio.on('ping')
def handle_message(*_args, **_kwargs):
    market_books = output_queue.get()

    for market_book in market_books:
        emit('my_response',
             {'data': 'update', 'mb': market_book.streaming_update})


def main():
    socketio.run(app, debug=True)
    stream.stop()


if __name__ == '__main__':
    main()

#
