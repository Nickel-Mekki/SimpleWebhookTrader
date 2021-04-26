import logging
import asyncio
from exchange import exchange


class binance(exchange):

    def __init__(self, default_type, key, secret):
        super(binance, self).__init__(
            default_type=default_type,
            key=key,
            secret=secret,
        )

    async def get_position(self, symbol):
        try:
            response = await self.client.fetch_positions(symbols=[symbol])
            position = 0.0
            for position in response:
                if symbol.replace('/', '') == position['symbol']:
                    position = float(position['positionAmt'])
                    break
            return position

        except Exception as e:
            self.logger.exception(str(e))
