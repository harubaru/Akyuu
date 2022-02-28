import asyncio
from io import StringIO
from typing import Optional
import discord
from discord.commands import SlashCommandGroup, Option
from discord.ext import commands

from src.core.logging import get_logger
from src.core.config import settings
from src.stories.api import GooseAI_ModelProvider, Sukima_ModelProvider
from src.stories.core import *

embed_color = discord.Colour(value=settings.DISCORD_EMBED_COLOR)
logger = get_logger(__name__)

class StoryCog(commands.Cog, name='Stories', description='Use our powerful AI to generate stories.'):
    def __init__(self, bot):
        self.bot = bot
        self.queue = asyncio.Queue()
        self.bot.loop.create_task(self.cmd_executor())
        if settings.GOOSEAI_TOKEN:
            self.model_provider = GooseAI_ModelProvider(token=settings.GOOSEAI_TOKEN)
        else:
            self.model_provider = Sukima_ModelProvider(settings.SUKIMA_ENDPOINT, username=settings.SUKIMA_USERNAME, password=settings.SUKIMA_PASSWORD)

    accounts = SlashCommandGroup('accounts', 'Account management commands.')
    stories = SlashCommandGroup('stories', 'Story management commands.')

    # create listener for on disconnect
    @commands.Cog.listener()
    async def on_disconnect(self):
        # cleanup the task by cancelling self.cmd_executor
        for task in asyncio.Task.all_tasks(self.bot.loop):
            if task is self.cmd_executor:
                task.cancel()

    async def cmd_executor(self):
        while True:
            try:
                task = await self.queue.get()
                # run the task concurrently, do not wait for it to finish
                self.bot.loop.create_task(task)
                self.queue.task_done()
                await asyncio.sleep(0.01)
            except Exception as e:
                logger.error(f'Error in cmd_executor: {e}')
                await asyncio.sleep(0.01)

    @accounts.command(name='register', description='Register a new account.')
    async def register(self, ctx: discord.ApplicationContext):
        embed = discord.Embed(title='Registering...', description='Please wait warmly while we create your account.', color=embed_color)
        embed.set_footer(text=f'{ctx.interaction.user.name}#{ctx.interaction.user.discriminator}', icon_url=ctx.interaction.user.avatar.url)
        await ctx.respond(embed=embed)
        message = await ctx.interaction.original_message()
        try:
            id = ctx.interaction.user.id
            await cmd_user_register(id)

            embed.title = 'Registration complete!'
            embed.description = f'Your account has been registered. Please refer to <#{str(settings.DISCORD_PRIVACY_CHANNEL)}> for more information regarding privacy.'

            await message.edit(embed=embed)
        except Exception as e:
            embed = discord.Embed(title='Error', description=f'An error has occurred while registering your account.\nError: {e}', color=embed_color)
            await message.edit(embed=embed)
    
    @accounts.command(name='delete', description='Delete your account. This action cannot be undone and all your data will be permanently deleted.')
    async def delete(self, ctx: discord.ApplicationContext, confirmation: Option(str, "If you are absolutely sure, type in DELETE for this option.")):
        embed = discord.Embed(title='Deleting...', description='We\'re sorry to see you go. Please wait warmly while we remove your account.', color=embed_color)
        embed.set_footer(text=f'{ctx.interaction.user.name}#{ctx.interaction.user.discriminator}', icon_url=ctx.interaction.user.avatar.url)
        await ctx.respond(embed=embed)
        message = await ctx.interaction.original_message()
        try:
            embed = discord.Embed(color=embed_color)
            if confirmation != 'DELETE':
                embed.title = 'Account Deletion cancelled.'
                embed.description = 'You have not confirmed your deletion.'
                await message.edit(embed=embed)
                return

            id = ctx.interaction.user.id
            await cmd_user_delete(id)

            embed.title = 'Your account has been removed.'
            embed.description = 'Your account and all associated data has been removed. Please come back soon!'
            await message.edit(embed=embed)
        except Exception as e:
            embed = discord.Embed(title='Account Deletion failed.', description=f'An error has occurred while deleting your account.\nError: {e}', color=embed_color)
            await message.edit(embed=embed)
    
    @stories.command(name='new', description='Create a new story.')
    async def new(self, ctx: discord.ApplicationContext, title: Option(str, 'The title of your new story.'), description: Option(str, 'A description of your new story.'), author: Option(str, 'The author that the AI will mimic for your story.', required=False, default=None), genre: Option(str, 'The genre of your new story.', required=False, default=None), tags: Option(str, 'A list of tags for your new story. The AI will use this.', required=False, default=None), style: Option(str, 'The style that the AI will write in.', required=False, default=None)):
        embed = discord.Embed(title='Creating...', description='Please wait warmly while we create your story.', color=embed_color)
        embed.set_footer(text=f'{ctx.interaction.user.name}#{ctx.interaction.user.discriminator}', icon_url=ctx.interaction.user.avatar.url)
        await ctx.respond(embed=embed)
        message = await ctx.interaction.original_message()
        try:
            id = ctx.interaction.user.id
            uuid = await cmd_story_new(id, title, description, author, genre, tags, style)
            await cmd_story_select(id, uuid)

            embed.title = 'Story creation complete!'
            embed.description = 'Your story has been created!'
            await message.edit(embed=embed)
        except Exception as e:
            embed = discord.Embed(title='Story creation failed.', description=f'An error has occurred while creating your story.\nError: {e}', color=embed_color)
            await message.edit(embed=embed)
    
    @stories.command(name='edit', description='Edit a story\'s metadata.')
    async def edit(self, ctx: discord.ApplicationContext, title: Option(str, 'The title of your new story.'), description: Option(str, 'A description of your new story.'), author: Option(str, 'The author that the AI will mimic for your story.', required=False, default=None), genre: Option(str, 'The genre of your new story.', required=False, default=None), tags: Option(str, 'A list of tags for your new story. The AI will use this.', required=False, default=None), style: Option(str, 'The style that the AI will write in.', required=False, default=None)):
        embed = discord.Embed(title='Editing...', description='Please wait warmly while we edit your story.', color=embed_color)
        embed.set_footer(text=f'{ctx.interaction.user.name}#{ctx.interaction.user.discriminator}', icon_url=ctx.interaction.user.avatar.url)
        await ctx.respond(embed=embed)
        message = await ctx.interaction.original_message()
        try:
            id = ctx.interaction.user.id
            await cmd_story_edit(id, title, description, author, genre, tags, style)

            embed.title = 'Story edit complete!'
            embed.description = None
            await message.edit(embed=embed)
        except Exception as e:
            embed = discord.Embed(title='Story edit failed.', description=f'An error has occurred while editing your story.\nError: {e}', color=embed_color)
            await message.edit(embed=embed)
    
    @stories.command(name='delete', description='Delete your story.')
    async def storydelete(self, ctx: discord.ApplicationContext, confirmation: Option(str, "If you are absolutely sure, type in DELETE for this option.")):
        embed = discord.Embed(title='Deleting...', description='Please wait warmly while we delete your story.', color=embed_color)
        embed.set_footer(text=f'{ctx.interaction.user.name}#{ctx.interaction.user.discriminator}', icon_url=ctx.interaction.user.avatar.url)
        await ctx.respond(embed=embed)
        message = await ctx.interaction.original_message()
        try:
            if confirmation != 'DELETE':
                embed = discord.Embed(title='Story deletion cancelled.', description='You have not confirmed your deletion.', color=embed_color)
                await message.edit(embed=embed)
                return

            id = ctx.interaction.user.id
            await cmd_story_delete(id)

            embed.title = 'Story deletion complete!'
            embed.description = None
            await message.edit(embed=embed)
        except Exception as e:
            embed = discord.Embed(title='Story deletion failed.', description=f'An error has occurred while deleting your story.\nError: {e}', color=embed_color)
            await message.edit(embed=embed)
    
    @stories.command(name='list', description='List all your stories.')
    async def list(self, ctx: discord.ApplicationContext):
        embed = discord.Embed(title='Listing...', description='Please wait warmly while we list your stories.', color=embed_color)
        embed.set_footer(text=f'{ctx.interaction.user.name}#{ctx.interaction.user.discriminator}', icon_url=ctx.interaction.user.avatar.url)
        await ctx.respond(embed=embed)
        message = await ctx.interaction.original_message()
        try:
            id = ctx.interaction.user.id
            stories = await cmd_story_list(id)

            embed.title = 'Your stories'
            embed.description = ''
            for i in range(len(stories)):
                embed.description += f'{i}: **``{stories[i].content_metadata.title}``**\n'
            
            await message.edit(embed=embed)
        except Exception as e:
            embed = discord.Embed(title='Story listing failed.', description=f'An error has occurred while listing your stories.\nError: {e}', color=embed_color)
            await message.edit(embed=embed)
    
    @stories.command(name='select', description='Select a story.')
    async def storyselect(self, ctx: discord.ApplicationContext, selection: Option(int, "Please select a story by typing in the number of the story you wish to select.")):
        embed = discord.Embed(title='Selecting...', description='Please wait warmly while we select your story.', color=embed_color)
        embed.set_footer(text=f'{ctx.interaction.user.name}#{ctx.interaction.user.discriminator}', icon_url=ctx.interaction.user.avatar.url)
        await ctx.respond(embed=embed)
        message = await ctx.interaction.original_message()
        try:
            id = ctx.interaction.user.id
            stories = await cmd_story_list(id)
            await cmd_story_select(id, stories[selection].story_uuid)

            embed.title = 'Story selection complete!'
            embed.description = f'You have selected **``{stories[selection].content_metadata.title}``**.'
            
            await message.edit(embed=embed)
        except Exception as e:
            embed = discord.Embed(title='Story selection failed.', description=f'An error has occurred while selecting your story.\nError: {e}', color=embed_color)
            await message.edit(embed=embed)
    
    async def print_story(self, id, char_limit, embed):
        story = await get_current_story(id)
        embed.title = f'{story.content_metadata.title}'
        embed.description = story.raw_txt(format=False, highlight_lastline=True, char_limit=char_limit)
        return embed
    
    async def print_memory(self, id, embed):
        story = await get_current_story(id)
        embed.title = f'{story.content_metadata.title}'
        embed.description = f'**``Memory``**:\n{story.content_metadata.memory}'
        return embed
    
    async def print_authorsnote(self, id, embed):
        story = await get_current_story(id)
        embed.title = f'{story.content_metadata.title}'
        embed.description = f'**``Author\'s Note``**:\n{story.content_metadata.authorsNote}'
        return embed
    
    @stories.command(name='view', description='View your selected story.')
    async def view(self, ctx: discord.ApplicationContext, what: Option(str, "Choose what to view.", choices=['Story', 'Memory', 'Author\'s Note']), text_amount: Option(int, 'The amount of characters to display.', required=False, default=768)):
        embed = discord.Embed(title='Viewing your story content...', description='Please wait warmly while we view your story.', color=embed_color)
        embed.set_footer(text=f'{ctx.interaction.user.name}#{ctx.interaction.user.discriminator}', icon_url=ctx.interaction.user.avatar.url)
        await ctx.respond(embed=embed)
        message = await ctx.interaction.original_message()
        try:
            id = ctx.interaction.user.id

            if what == 'Story':
                embed = await self.print_story(id, text_amount, embed)
            elif what == 'Memory':
                embed = await self.print_memory(id, embed)
            elif what == 'Author\'s Note':
                embed = await self.print_authorsnote(id, embed)
            
            await message.edit(embed=embed)
        except Exception as e:
            embed = discord.Embed(title='Story viewing failed.', description=f'An error has occurred while viewing your story.\nError: {e}', color=embed_color)
            await message.edit(embed=embed)
    
    async def async_submit(self, ctx: discord.ApplicationContext, text, embed):
        original_message = await ctx.interaction.original_message()
        try:
            await cmd_story_submit(ctx.interaction.user.id, text, self.model_provider)
            embed = await self.print_story(ctx.interaction.user.id, 768, embed)
            embed.set_footer(text=f'{ctx.interaction.user.name}#{ctx.interaction.user.discriminator} - Successfully submitted the action.', icon_url=ctx.interaction.user.avatar.url)
            await original_message.edit(embed=embed)
        except Exception as e:
            embed = discord.Embed(title='Story submission failed.', description=f'An error has occurred while submitting your story.\nError: {e}', color=embed_color)
            embed.set_footer(text=f'{ctx.interaction.user.name}#{ctx.interaction.user.discriminator} - Submission failed.', icon_url=ctx.interaction.user.avatar.url)
            await original_message.edit(embed=embed)
    
    async def async_retry(self, ctx: discord.ApplicationContext, embed):
        original_message = await ctx.interaction.original_message()
        try:
            await cmd_story_retry(ctx.interaction.user.id, self.model_provider)
            embed = await self.print_story(ctx.interaction.user.id, 768, embed)
            embed.set_footer(text=f'{ctx.interaction.user.name}#{ctx.interaction.user.discriminator} - Successfully retried the action.', icon_url=ctx.interaction.user.avatar.url)
            original_message = await ctx.interaction.original_message()
            await original_message.edit(embed=embed)
        except Exception as e:
            embed = discord.Embed(title='Story retry failed.', description=f'An error has occurred while retrying your story.\nError: {e}', color=embed_color)
            embed.set_footer(text=f'{ctx.interaction.user.name}#{ctx.interaction.user.discriminator} - Retry failed.', icon_url=ctx.interaction.user.avatar.url)
            await original_message.edit(embed=embed)

    @stories.command(name='submit', description='Submit your story to the AI.')
    async def submit(self, ctx: discord.ApplicationContext, text: Option(str, 'The text you wish to submit to the AI', required=True)):
        embed = discord.Embed(title='Submitting...', description='Please wait warmly while we submit your story.', color=embed_color)
        embed.set_footer(text=f'{ctx.interaction.user.name}#{ctx.interaction.user.discriminator}', icon_url=ctx.interaction.user.avatar.url)
        await ctx.respond(embed=embed)
        message = await ctx.interaction.original_message()
        try:
            await self.queue.put(self.async_submit(ctx, text, embed))
        except Exception as e:
            embed = discord.Embed(title='Story submission failed.', description=f'An error has occurred while submitting your story.\nError: {e}', color=embed_color)
            await message.edit(embed=embed)
    
    @stories.command(name='continue', description='Continue the last generation by submitting it to the AI.')
    async def continue_(self, ctx: discord.ApplicationContext):
        embed = discord.Embed(title='Continuing...', description='Please wait warmly while we continue your story.', color=embed_color)
        embed.set_footer(text=f'{ctx.interaction.user.name}#{ctx.interaction.user.discriminator}', icon_url=ctx.interaction.user.avatar.url)
        await ctx.respond(embed=embed)
        message = await ctx.interaction.original_message()
        try:
            await self.queue.put(self.async_submit(ctx, None, embed))
        except Exception as e:
            embed = discord.Embed(title='Story continuation failed.', description=f'An error has occurred while continuing your story.\nError: {e}', color=embed_color)
            await message.edit(embed=embed)
    
    @stories.command(name='undo', description='Undo the last action.')
    async def undo(self, ctx: discord.ApplicationContext):
        embed = discord.Embed(title='Undoing...', description='Please wait warmly while we undo your last action.', color=embed_color)
        embed.set_footer(text=f'{ctx.interaction.user.name}#{ctx.interaction.user.discriminator}', icon_url=ctx.interaction.user.avatar.url)
        await ctx.respond(embed=embed)
        message = await ctx.interaction.original_message()
        try:
            id = ctx.interaction.user.id
            await cmd_story_undo(id)

            embed = await self.print_story(id, 768, embed)
            embed.set_footer(text=f'{ctx.interaction.user.name}#{ctx.interaction.user.discriminator} - Successfully undoed the last action.', icon_url=ctx.interaction.user.avatar.url)
            await message.edit(embed=embed)
        except Exception as e:
            embed = discord.Embed(title='Undo failed.', description=f'An error has occurred while undoing your last action.\nError: {e}', color=embed_color)
            await message.edit(embed=embed)
    
    @stories.command(name='retry', description='Retry the last action.')
    async def retry(self, ctx: discord.ApplicationContext):
        embed = discord.Embed(title='Retrying...', description='Please wait warmly while we retry your last action.', color=embed_color)
        embed.set_footer(text=f'{ctx.interaction.user.name}#{ctx.interaction.user.discriminator}', icon_url=ctx.interaction.user.avatar.url)
        await ctx.respond(embed=embed)
        message = await ctx.interaction.original_message()
        try:
            await self.queue.put(self.async_retry(ctx, embed))
        except Exception as e:
            embed = discord.Embed(title='Retry failed.', description=f'An error has occurred while retrying your last action.\nError: {e}', color=embed_color)
            await message.edit(embed=embed)
    
    @stories.command(name='alter', description='Alter the last action.')
    async def alter(self, ctx: discord.ApplicationContext, text: Option(str, 'Replace the last action with new text.')):
        embed = discord.Embed(title='Altering...', description='Please wait warmly while we alter your last action.', color=embed_color)
        embed.set_footer(text=f'{ctx.interaction.user.name}#{ctx.interaction.user.discriminator}', icon_url=ctx.interaction.user.avatar.url)
        await ctx.respond(embed=embed)
        message = await ctx.interaction.original_message()
        try:
            id = ctx.interaction.user.id
            await cmd_story_alter(id, text)

            embed = await self.print_story(id, 768, embed)
            embed.set_footer(text=f'{ctx.interaction.user.name}#{ctx.interaction.user.discriminator} - Successfully altered the last action.', icon_url=ctx.interaction.user.avatar.url)
            await message.edit(embed=embed)
        except Exception as e:
            embed = discord.Embed(title='Alter failed.', description=f'An error has occurred while altering your last action.\nError: {e}', color=embed_color)
            await message.edit(embed=embed)
    
    @stories.command(name='memory', description='Set the memory of the story so the AI can remember it.')
    async def memory(self, ctx: discord.ApplicationContext, text: Option(str, 'The text you wish to set as the memory of the story.')):
        embed = discord.Embed(title='Setting memory...', description='Please wait warmly while we set the memory of the story.', color=embed_color)
        embed.set_footer(text=f'{ctx.interaction.user.name}#{ctx.interaction.user.discriminator}', icon_url=ctx.interaction.user.avatar.url)
        await ctx.respond(embed=embed)
        message = await ctx.interaction.original_message()
        try:
            id = ctx.interaction.user.id
            await cmd_story_memory(id, text)

            embed = await self.print_story(id, 768, embed)
            embed.set_footer(text=f'{ctx.interaction.user.name}#{ctx.interaction.user.discriminator} - Successfully set the memory of the story.', icon_url=ctx.interaction.user.avatar.url)
            await message.edit(embed=embed)
        except Exception as e:
            embed = discord.Embed(title='Setting memory failed.', description=f'An error has occurred while setting the memory of the story.\nError: {e}', color=embed_color)
            await message.edit(embed=embed)
    
    @stories.command(name='authorsnote', description='Set the authors note of the story to add a subtle effect to the AI.')
    async def authorsnote(self, ctx: discord.ApplicationContext, text: Option(str, 'The text you wish to set as the authors note of the story.')):
        embed = discord.Embed(title='Setting authors note...', description='Please wait warmly while we set the authors note of the story.', color=embed_color)
        embed.set_footer(text=f'{ctx.interaction.user.name}#{ctx.interaction.user.discriminator}', icon_url=ctx.interaction.user.avatar.url)
        await ctx.respond(embed=embed)
        message = await ctx.interaction.original_message()
        try:
            id = ctx.interaction.user.id
            await cmd_story_authorsnote(id, text)

            embed = await self.print_story(id, 768, embed)
            embed.set_footer(text=f'{ctx.interaction.user.name}#{ctx.interaction.user.discriminator} - Successfully set the authors note of the story.', icon_url=ctx.interaction.user.avatar.url)
            await message.edit(embed=embed)
        except Exception as e:
            embed = discord.Embed(title='Setting authors note failed.', description=f'An error has occurred while setting the authors note of the story.\nError: {e}', color=embed_color)
            await message.edit(embed=embed)

    # supplemental commands
    @stories.command(name='download', description='Download the selected story.')
    async def download(self, ctx: discord.ApplicationContext):
        embed = discord.Embed(title='Downloading...', description='Please wait warmly while we download your story.', color=embed_color)
        embed.set_footer(text=f'{ctx.interaction.user.name}#{ctx.interaction.user.discriminator}', icon_url=ctx.interaction.user.avatar.url)
        await ctx.respond(embed=embed)
        message = await ctx.interaction.original_message()
        try:
            with StringIO() as f:
                id = ctx.interaction.user.id
                story = await get_current_story(id)
                text = story.raw_txt(False, False, None)
                f.write(text)
                f.seek(0)
                embed.title = 'Done.'
                embed.description = f'See the attached file for your story.'
                embed.set_footer(text=f'{ctx.interaction.user.name}#{ctx.interaction.user.discriminator} - Successfully downloaded the story.', icon_url=ctx.interaction.user.avatar.url)
                await message.edit(embed=embed, file=discord.File(f, filename=f'{story.story_uuid}.txt'))
        except Exception as e:
            embed = discord.Embed(title='Download failed.', description=f'An error has occurred while downloading your story.\nError: {e}', color=embed_color)
            await message.edit(embed=embed)


def setup(bot):
    bot.add_cog(StoryCog(bot))
