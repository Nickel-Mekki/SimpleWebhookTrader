import logging
import sys
import os
import errno
import configparser
import asyncio
from aiohttp import web
import ccxt.async_support as ccxt
from exchange import exchange
from binance import binance
from bybit import bybit


# 設定の読み込み
config = configparser.ConfigParser()
path = os.path.dirname(os.path.abspath(__file__)) + '/config.ini'
if not os.path.exists(path):
   raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), path)
config.read(path, encoding="UTF-8")


# ロガーの初期化
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(filename)s:%(lineno)d %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)


# 定数の初期化
PORT = 80


# 辞書の初期化
bot = {}


# モジュールの初期化
routes = web.RouteTableDef()


@routes.post('/')
async def post_handler(request):
    try:
        request = await request.json()
        await trader(request)

    except Exception as e:
        logger.exception(str(e))

def output_exception_message(request):
    logger.info('Exception!---------------------------------------')
    logger.info(f'Strategy: {request["strategy"]["order"]["alert_message"]}')
    logger.info(f'Exchange/Symbol: {request["exchange"]}:{request["symbol"]}')

async def trader(request):
    global bot
    
    exchange = request['exchange'].lower()
    order = request['strategy']['order']
    params = order['id'].split(':')
    ticker_id = request['symbol']
    symbol = params[0]
    wallet_symbol = params[2]
    default_type =  params[1].lower()
    if exchange not in bot:
        try:
            exchange_cls = globals()[exchange]
            bot[exchange] = exchange_cls(
                default_type=default_type,
                key=config[exchange.upper()]['key'],
                secret=config[exchange.upper()]['secret'],
            )
            await bot[exchange].prepare()

        except Exception as e:
            output_exception_message(request)
            logger.exception(str(e))
            return
    else:
        bot[exchange].client.options['defaultType'] = default_type

    # 残高/ポジションの取得
    base, quote = symbol.split('/')
    balance, position = None, None
    task = [bot[exchange].get_balance()]

    if default_type not in ['', 'spot']:
        task.append(bot[exchange].get_position(symbol=symbol))
    if len(task) == 1:
        try:
            balance = await asyncio.gather(*task)

        except Exception as e:
            output_exception_message(request)
            logger.exception(str(e))
            return

    if len(task) == 2:
        try:
            balance, position = await asyncio.gather(*task)

        except Exception as e:
            output_exception_message(request)
            logger.exception(str(e))
            return

    if default_type in ['', 'spot']:
        position = balance[base]['total']
    balance = balance[wallet_symbol]['total']

    # マーケット情報の取得
    market = bot[exchange].client.markets[symbol]
    min_amount = market['limits']['amount']['min']
    amount_precision = market['precision']['amount']

    # 注文情報の前処理
    if order['market_position'] == 'short':
        order['market_position_size'] = -order['market_position_size']

    # 発注処理    
    position_disparity = position - order['market_position_size']

    try:
        if abs(position_disparity) < min_amount:
            # 最小数量を下回っている際は例外発生
            raise ValueError('Error: Order amount is Please specify min amount or more for the amount.')
    except Exception as e:
        output_exception_message(request)
        logger.exception(str(e))
        return

    client_order = {
        'symbol': symbol,
        'ord_type': 'market',
        'side': 'Buy',
        'amount': round(abs(position_disparity), amount_precision),
        'params': {},
    }
    if position_disparity > 0:
        client_order['side'] = 'Sell'
    
    if position_disparity != 0:
        try:
            # result = {'id': ''}
            # pass
            result = await bot[exchange].post_order(**client_order)

        except Exception as e:
            output_exception_message(request)
            logger.exception(str(e))
            return

        # ログ出力
        logger.info('-------------------------------------------------')
        logger.info(f'Strategy: {order["alert_message"]}')
        logger.info(f'Exchange/Symbol: {request["exchange"]}:{ticker_id}')
        logger.info(f'Alert timestamp: {request["timestamp"]}')
        logger.info(f'Trading view position: {order["market_position_size"]}')
        logger.info(f'Prev client position: {position}')
        logger.info(f'Position disparity: {position_disparity}')
        logger.info(f'Order action: {client_order["side"]}')
        logger.info(f'Client order id: {result["id"]}')

    else:
        logger.info('-------------------------------------------------')
        logger.info(f'Strategy: {order["alert_message"]}')
        logger.info(f'Exchange/Symbol: {request["exchange"]}:{ticker_id}')
        logger.info(f'Alert timestamp: {request["timestamp"]}')
        logger.info(f'Trading view position: {order["market_position_size"]}')
        logger.info(f'Prev client position: {position}')
        logger.info(f'Position disparity: {position_disparity}')


if __name__ == '__main__':
    try:
        app = web.Application()
        app.add_routes([web.post('/', post_handler)])
        web.run_app(app, port=PORT)
    except Exception as e:
        logger.exception(str(e))
