import discord
from discord.ext import commands
from src.core.logging import get_logger
from src.stories.core import load_cache

class Akyuu(commands.Bot):
    def __init__(self, args):
        super().__init__(command_prefix=args.prefix, intents=discord.Intents.all())
        self.args = args
        self.logger = get_logger(__name__)
        load_cache()
        self.load_extension('src.bot.storycog')

    async def on_ready(self):
        self.logger.info(f'Logged in as {self.user.name} ({self.user.id})')
        await self.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name='over the records.📚'))
    
    async def close(self):
        await self.close()