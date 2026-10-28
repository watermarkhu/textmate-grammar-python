import asyncio
from contextlib import asynccontextmanager


@asynccontextmanager
async def connection(pool):
    async with pool.acquire() as conn:
        try:
            yield conn
        finally:
            await conn.close()


async def main():
    async for item in stream():
        print(f"received: {item!r}")


asyncio.run(main())
