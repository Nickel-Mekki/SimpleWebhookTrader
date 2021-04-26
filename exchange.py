import logging
import asyncio
import ccxt.async_support as ccxt


class exchange:

    def __init__(self, default_type, key, secret):
        self.logger = logging.getLogger()

        self.default_type = default_type

        try:
            options = {}
            if self.default_type != '':
                options['defaultType'] = self.default_type
            self.client = getattr(ccxt, self.__class__.__name__)({
                'apiKey': key,
                'secret': secret,
                'options': options,
            })

        except Exception as e:
            logger.exception(str(e))

        self.market = None

    async def prepare(self):
        await self.load_market()

    async def load_market(self):
        try:
            await self.client.load_markets()

        except Exception as e:
            self.logger.exception(str(e))

    async def get_balance(self):
        try:
            response = await self.client.fetch_balance()
            return response

        except Exception as e:
            self.logger.exception(str(e))

    async def get_position(self, symbol):
        try:
            response = await self.client.fetch_positions(symbols=[symbol])
            return response

        except Exception as e:
            self.logger.exception(str(e))

    async def post_order(self, symbol, ord_type, side, amount, params={}):
        try:
            response = await self.client.create_order(
                symbol=symbol,
                type=ord_type,
                side=side,
                amount=amount,
                params=params,
            )
            return response

        except Exception as e:
            self.logger.exception(str(e))
