from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals
)
from builtins import *
from bitmex_websocket.websocket import BitMEXWebsocket
from tests import *
from tests.helpers import *
import pytest
import json


orderBookL2_data = {}
with open('./tests/fixtures/order_book_l2_partial_action_message.json')\
        as partial_data:
    orderBookL2_data['partial'] = json.load(partial_data)
with open('./tests/fixtures/order_book_l2_insert_action_message.json')\
        as insert_data:
    orderBookL2_data['insert'] = json.load(insert_data)
with open('./tests/fixtures/order_book_l2_delete_action_message.json')\
        as delete_data:
    orderBookL2_data['delete'] = json.load(delete_data)
with open('./tests/fixtures/order_book_l2_update_action_message.json')\
        as update_data:
    orderBookL2_data['update'] = json.load(update_data)


def test_connect_should_connect_ws(mocker):
    connect_websocket = mocker.patch(
        'bitmex_websocket.websocket.BitMEXWebsocket.connect_websocket')

    socket = BitMEXWebsocket()
    socket.connect()

    connect_websocket.assert_called_once()


def test_build_websocket_url_w_heartbeat(mocker):
    socket = BitMEXWebsocket()
    socket.heartbeatEnabled = True
    url = socket.build_websocket_url('https://testnet.bitmex.com/api/v1/')

    assert url == 'wss://testnet.bitmex.com/realtime?heartbeat=true'


def test_build_websocket_url_without_heartbeat(mocker):
    socket = BitMEXWebsocket()
    socket.heartbeatEnabled = False

    url = socket.build_websocket_url('https://testnet.bitmex.com/api/v1/')

    assert url == 'wss://testnet.bitmex.com/realtime'


def test_connect_websocket_with_heartbeat(mocker):
    '''
    Ensure heartbeat is enabled on the websocket.
    '''
    websocket_run_forever = mocker.patch(
        'bitmex_websocket.websocket.BitMEXWebsocket.websocket_run_forever')
    init_websocket = mocker.patch(
        'bitmex_websocket.websocket.BitMEXWebsocket.init_websocket')
    wait_for_connection = mocker.patch(
        'bitmex_websocket.websocket.BitMEXWebsocket.wait_for_connection')
    socket = BitMEXWebsocket()
    socket.shouldAuth = False
    socket.heartbeatEnabled = True
    socket.connect_websocket()

    websocket_run_forever.assert_called_with(
        {'ping_timeout': 10, 'ping_interval': 25})
    init_websocket.assert_called_once()
    wait_for_connection.assert_called_once()


def test_connect_websocket_without_heartbeat(mocker):
    '''
    Ensure heartbeat is disabled on the websocket.
    '''
    websocket_run_forever = mocker.patch(
        'bitmex_websocket.websocket.BitMEXWebsocket.websocket_run_forever')
    init_websocket = mocker.patch(
        'bitmex_websocket.websocket.BitMEXWebsocket.init_websocket')
    wait_for_connection = mocker.patch(
        'bitmex_websocket.websocket.BitMEXWebsocket.wait_for_connection')
    socket = BitMEXWebsocket()
    socket.shouldAuth = False
    socket.heartbeatEnabled = False
    socket.connect_websocket()

    # neither ping_timeout or ping_interval are passed as args
    websocket_run_forever.assert_called_with({})
    init_websocket.assert_called_once()
    wait_for_connection.assert_called_once()


def test_subscribe_to_channel(mocker):

    send_message = mocker.patch(
        'bitmex_websocket.websocket.BitMEXWebsocket.send_message')
    socket = BitMEXWebsocket()
    socket.symbol = 'test_symbol'
    socket.heartbeatEnabled = False
    socket.subscribe('test_channel')

    send_message.assert_called_with(
        {'op': 'subscribe', 'args': ['test_channel:test_symbol']})


def test_subscribe_instrument_on_message(mocker):
    on_subscribe = mocker.patch(
        'bitmex_websocket.websocket.BitMEXWebsocket.on_subscribe')
    socket = BitMEXWebsocket()
    message = {
        "success": "true",
        "subscribe": "instrument:XBTH17",
        "request": {
            "op": "subscribe",
            "args": ["instrument:XBTH17"]
        }
    }
    socket.on_message({}, json.dumps(message))

    on_subscribe.assert_called_once()


def test_on_subscribe_success(mocker):
    error = mocker.patch(
        'bitmex_websocket.websocket.BitMEXWebsocket.error')
    socket = BitMEXWebsocket()
    message = {
        "success": "true",
        "subscribe": "instrument:XBTH17",
        "request": {
            "op": "subscribe",
            "args": ["instrument:XBTH17"]
        }
    }
    socket.on_subscribe(message)

    error.assert_not_called()


def test_on_subscribe_called_on_sub_error_message(mocker):
    '''
    on_message should call on_subscribe when subscription error is received
    '''
    error = mocker.patch(
        'bitmex_websocket.websocket.BitMEXWebsocket.error')
    socket = BitMEXWebsocket()
    message = {
        "status": 400,
        "error": "Unknown table: instrument_",
        "meta": {},
        "request": {
            "op": "subscribe",
            "args": ["instrument_:XBTH17"]
        }
    }

    socket.on_message({}, json.dumps(message))
    error.assert_called_with("Unknown table: instrument_")


def test_on_partial_action_data(mocker):
    socket = BitMEXWebsocket()
    with open('./tests/fixtures/instrument_partial_action_message.json')\
            as message_data:
        message = json.load(message_data)

        action = message['action']
        socket.on_action(action, message)

        assert socket.data['instrument']


def test_on_partial_orderBookL2_action_data(mocker):
    socket = BitMEXWebsocket()

    message = orderBookL2_data['partial']

    action = message['action']
    socket.on_action(action, message)

    assert socket.data['orderBookL2']


def test_on_orderBookL2_action_data(mocker):
    """
    Ensure orderBookL2 is updated on delete, insert and update actions.
    """
    socket = BitMEXWebsocket()

    # Recieve partial action message
    partial_action_message = orderBookL2_data['partial']
    partial_data = partial_action_message['data']
    socket.on_action('partial', partial_action_message)
    orderBookL2 = socket.data['orderBookL2']
    for partial_level in partial_data:
        level = next(level for level in orderBookL2
                    if level['id'] == partial_level['id'])
        assert level

    # Receive delete action message
    delete_action_message = orderBookL2_data['delete']
    delete_level_id = delete_action_message['data'][0]['id']

    socket.on_action('delete', delete_action_message)
    delete_level = next((level for level in partial_data
                        if level['id'] == delete_level_id), None)
    assert not delete_level

    # Receive insert action message
    insert_action_message = orderBookL2_data['insert']
    socket.on_action('insert', insert_action_message)
    insert_data = insert_action_message['data']

    for insert_level in insert_data:
        level = next(level for level in orderBookL2
            if level['id'] == insert_level['id'])
        assert level

    # Receive update action message
    update_action_message = orderBookL2_data['update']
    update_data = update_action_message['data']
    level_update = update_data[0]
    socket.on_action('update', update_action_message)
    updated_level = next(level for level in orderBookL2
                        if level['id'] == level_update['id'])

    assert updated_level['size'] == level_update['size']

@pytest.mark.xfail
def test_should_fail(self):
    self.assertEqual(False, True)
