try:
    import conf
except ImportError:
    pass

import sys
import argparse
import asyncio
import traceback
from src.core.config import settings
from src.core.logging import get_logger
from src.bot.akyuu import Akyuu

logger = get_logger(__name__)

def parse_args():
    parser = argparse.ArgumentParser(
        description='Akyuu - A Discord bot for AI powered adventures. Env vars can be overrided by passing arguments.',
        usage='akyuu [arguments]'
    )

    parser.add_argument('--owner-id', type=int, help='The ID of the bot owner.', default=settings.DISCORD_OWNER)
    parser.add_argument('--prefix', type=str, help='The prefix to use for commands.', default=settings.DISCORD_PREFIX)
    parser.add_argument('--token', type=str, help='The token to use for authentication.', default=settings.DISCORD_TOKEN)

    return parser.parse_args()

async def shutdown(bot):
    await bot.close()

def main():
    akyuu = None
    args = parse_args()
    try:
        akyuu = Akyuu(args)
        akyuu.run(args.token)
    except KeyboardInterrupt:
        logger.info('Keyboard interrupt received. Exiting.')
        asyncio.run(shutdown(akyuu))
    except SystemExit:
        logger.info('System exit received. Exiting.')
        asyncio.run(shutdown(akyuu))
    except Exception as e:
        logger.error(e)
        #print traceback to logger
        logger.error(traceback.format_exc())
        asyncio.run(shutdown(akyuu))
    finally:
        sys.exit(0)

if __name__ == '__main__':
    main()