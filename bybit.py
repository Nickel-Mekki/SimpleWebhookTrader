import logging
import asyncio
from exchange import exchange


class bybit(exchange):

    def __init__(self, default_type, key, secret):
        super(bybit, self).__init__(
            default_type=default_type,
            key=key,
            secret=secret,
        )

    async def get_position(self, symbol):
        try:
            response = await self.client.fetch_positions()
            positions = [p['data'] for p in response]
            position = 0.0
            for p in positions:
                if p['symbol'] != symbol.replace('/', ''):
                    continue
                else:
                    position += float(p['size'])
            return position

        except Exception as e:
            self.logger.exception(str(e))
