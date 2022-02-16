# dev.py
"""Internal dev commands"""

import asyncio
from datetime import datetime, timedelta
import importlib
import sys

import discord
from discord.ext import commands

from database import cooldowns, reminders
from resources import emojis, strings


class DevCog(commands.Cog):
    """Cog class containing internal dev commands"""
    def __init__(self, bot):
        self.bot = bot

    @commands.group(invoke_without_command=True)
    @commands.is_owner()
    @commands.bot_has_permissions(send_messages=True)
    async def dev(self, ctx: commands.Context) -> None:
        """Dev command group"""
        if ctx.prefix.lower() == 'rpg ': return
        subcommands = ''
        for command in self.bot.walk_commands():
            if isinstance(command, commands.Group):
                if command.qualified_name == 'dev':
                    for subcommand in command.walk_commands():
                        if subcommand.parents[0] == command:
                            aliases = f'`{subcommand.qualified_name}`'
                            for alias in subcommand.aliases:
                                aliases = f'{aliases}, `{alias}`'
                            subcommands = f'{subcommands}{emojis.BP} {aliases}\n'
        await ctx.reply(f'Available dev commands:\n{subcommands}')

    @dev.group(name='event-reduction', aliases=('er',), invoke_without_command=True)
    @commands.bot_has_permissions(send_messages=True)
    async def dev_event_reduction(self, ctx: commands.Context, *args: str) -> None:
        """Sets event reductions of activities"""
        def check(m: discord.Message) -> bool:
            return m.author == ctx.author and m.channel == ctx.channel
        prefix = ctx.prefix
        if prefix.lower() == 'rpg ': return
        if not ctx.author.id in (285399610032390146, 619879176316649482, 552563486740447263):
            await ctx.reply('You are not allowed to use this command.')
            return
        syntax = strings.MSG_SYNTAX.format(syntax=f'{ctx.prefix}{ctx.command.qualified_name} [activity] [reduction in %]')
        activity_list = 'Possible activities:'
        for activity in strings.ACTIVITIES_WITH_COOLDOWN:
            activity_list = f'{activity_list}\n{emojis.BP} `{activity}`'
        if not args or len(args) != 2:
            all_cooldowns = await cooldowns.get_all_cooldowns()
            message = 'Current event reductions:'
            for cooldown in all_cooldowns:
                cooldown_message = (
                    f'{emojis.BP} {cooldown.activity}: {cooldown.event_reduction}% '
                    f'({cooldown.actual_cooldown():,}s)'
                )
                message = f'{message}\n**{cooldown_message}**' if cooldown.event_reduction > 0 else f'{message}\n{cooldown_message}'
            message = f'{message}\n\n{syntax}'
            await ctx.reply(message)
            return
        activity = args[0].lower()
        reduction = args[1].lower().replace('%','')
        try:
            reduction = float(reduction)
        except:
            try:
                reduction = float(activity)
                activity = args[1]
            except:
                await ctx.reply(f'{syntax}\n\n{activity_list}')
                return
        if not 0 <= reduction <= 99:
            await ctx.reply(f'**{ctx.author.name}**, a reduction of **{reduction}%** doesn\'t make much sense, does it.')
            return
        if activity in strings.ACTIVITIES_ALIASES:
            activity = strings.ACTIVITIES_ALIASES[activity]
        if activity not in strings.ACTIVITIES_WITH_COOLDOWN:
            await ctx.reply(f'**{ctx.author.name}**, couldn\'t find activity `{activity}`.')
            return
        await ctx.reply(
            f'**{ctx.author.name}**, this will change the event reduction of activity `{activity}` to '
            f'**{reduction}%**. Continue? [`yes/no`]'
        )
        try:
            answer = await self.bot.wait_for('message', check=check, timeout=30)
        except asyncio.TimeoutError:
            await ctx.send(f'**{ctx.author.name}**, you didn\'t answer in time.')
        if not answer.content.lower() in ['yes','y']:
            await ctx.send('Aborted')
            return
        cooldown: cooldowns.Cooldown = await cooldowns.get_cooldown(activity)
        await cooldown.update(event_reduction=reduction)
        if cooldown.event_reduction == reduction:
            await ctx.reply(
                f'Changed event reduction for activity `{cooldown.activity}` to **{cooldown.event_reduction}%**.'
            )

    @dev_event_reduction.command(name='reset')
    @commands.bot_has_permissions(send_messages=True)
    async def dev_event_reduction_reset(self, ctx: commands.Context) -> None:
        """Resets event reductions of all activities"""
        def check(m: discord.Message) -> bool:
            return m.author == ctx.author and m.channel == ctx.channel
        if ctx.prefix.lower() == 'rpg ': return
        if not ctx.author.id in (285399610032390146, 619879176316649482, 552563486740447263):
            await ctx.reply('You are not allowed to use this command.')
            return
        await ctx.reply(
            f'**{ctx.author.name}**, this will change **all** event reductions to **0.0%**. Continue? [`yes/no`]'
        )
        try:
            answer = await self.bot.wait_for('message', check=check, timeout=30)
        except asyncio.TimeoutError as error:
            await ctx.send(f'**{ctx.author.name}**, you didn\'t answer in time.')
        if not answer.content.lower() in ['yes','y']:
            await ctx.send('Aborted')
            return
        all_cooldowns = await cooldowns.get_all_cooldowns()
        for cooldown in all_cooldowns:
            await cooldown.update(event_reduction=0.0)
        await ctx.reply(f'All event reductions have been reset.')

    @dev.command(name='cooldown-setup', aliases=('cd-setup',))
    @commands.bot_has_permissions(send_messages=True, read_message_history=True)
    async def cooldown_setup(self, ctx: commands.Context, *args: str) -> None:
        """Sets base cooldowns of all activities"""
        def check(m: discord.Message) -> bool:
            return m.author == ctx.author and m.channel == ctx.channel

        prefix = ctx.prefix
        if prefix.lower() == 'rpg ': return
        if not ctx.author.id in (285399610032390146, 619879176316649482):
            await ctx.reply('You are not allowed to use this command.')
            return
        syntax = strings.MSG_SYNTAX.format(syntax=f'{ctx.prefix}{ctx.command.qualified_name} [activity] [seconds]')
        activity_list = 'Possible activities:'
        for activity in strings.ACTIVITIES_WITH_COOLDOWN:
            activity_list = f'{activity_list}\n{emojis.BP} `{activity}`'
        if not args or len(args) != 2:
            all_cooldowns = await cooldowns.get_all_cooldowns()
            message = 'Current base cooldowns:'
            for cooldown in all_cooldowns:
                message = f'{message}\n{emojis.BP} {cooldown.activity}: {cooldown.base_cooldown}s'
            message = f'{message}\n\n{syntax}'
            await ctx.reply(message)
            return
        activity = args[0].lower()
        new_cooldown = args[1]
        if new_cooldown.isnumeric():
            new_cooldown = int(new_cooldown)
        else:
            if activity.isnumeric():
                new_cooldown = int(activity)
                activity = args[1]
        if activity in strings.ACTIVITIES_ALIASES:
            activity = strings.ACTIVITIES_ALIASES[activity]
        if activity not in strings.ACTIVITIES_WITH_COOLDOWN:
            await ctx.reply(f'**{ctx.author.name}**, couldn\'t find activity `{activity}`.')
            return
        await ctx.reply(
            f'**{ctx.author.name}**, this will change the base cooldown (before donor reduction) of activity '
            f'`{activity}` to **{new_cooldown:,}** seconds. Continue? [`yes/no`]'
        )
        try:
            answer = await self.bot.wait_for('message', check=check, timeout=30)
        except asyncio.TimeoutError as error:
            await ctx.send(f'**{ctx.author.name}**, you didn\'t answer in time.')
        if not answer.content.lower() in ['yes','y']:
            await ctx.send('Aborted')
            return
        cooldown: cooldowns.Cooldown = await cooldowns.get_cooldown(activity)
        await cooldown.update(cooldown=new_cooldown)
        if cooldown.base_cooldown == new_cooldown:
            await ctx.reply(
                f'Changed event reduction for activity `{cooldown.activity}` to '
                f'**{cooldown.base_cooldown}s**.'
            )
        else:
            await ctx.reply(strings.MSG_ERROR)

    @dev.command()
    @commands.is_owner()
    @commands.bot_has_permissions(send_messages=True, read_message_history=True)
    async def sleepy(self, ctx: commands.Context, seconds: int) -> None:
        """Sleepy potion test command"""
        if ctx.prefix.lower() == 'rpg ': return
        await reminders.reduce_reminder_time(ctx.author.id, timedelta(seconds=seconds))
        await ctx.reply('Done.')

    @dev.command()
    @commands.is_owner()
    @commands.bot_has_permissions(send_messages=True, read_message_history=True)
    async def shutdown(self, ctx: commands.Context) -> None:
        """Shut down the bot"""
        def check(m: discord.Message) -> bool:
            return m.author == ctx.author and m.channel == ctx.channel
        prefix = ctx.prefix
        if prefix.lower() == 'rpg ': return
        await ctx.reply(f'**{ctx.author.name}**, are you **SURE**? `[yes/no]`')
        try:
            answer = await self.bot.wait_for('message', check=check, timeout=30)
        except asyncio.TimeOutError:
            await ctx.send(f'**{ctx.author.name}**, you didn\'t answer in time.')
        if answer.content.lower() in ['yes','y']:
            await ctx.send('Shutting down.')
            await self.bot.close()
        else:
            await ctx.send('Phew, was afraid there for a second.')

    @dev.command(aliases=('unload','reload',))
    @commands.is_owner()
    @commands.bot_has_permissions(send_messages=True)
    async def load(self, ctx: commands.Context, *args: str) -> None:
        """Loads/unloads cogs and reloads cogs or modules"""
        action = ctx.invoked_with
        message_syntax = f'The syntax is `{ctx.prefix}dev {action} [name(s)]`'
        if ctx.prefix.lower() == 'rpg ': return
        if not args:
            await ctx.send(message_syntax)
            return
        args = [arg.lower() for arg in args]
        actions = []
        for mod_or_cog in args:
            name_found = False
            if not 'cogs.' in mod_or_cog:
                cog_name = f'cogs.{mod_or_cog}'
            try:
                if action == 'load':
                    cog_status = self.bot.load_extension(cog_name)
                elif action == 'reload':
                    cog_status = self.bot.reload_extension(cog_name)
                else:
                    cog_status = self.bot.unload_extension(cog_name)
            except:
                cog_status = 'Error'
            if cog_status is None:
                actions.append(f'+ Extension \'{cog_name}\' {action}ed.')
                name_found = True
            if not name_found:
                if action == 'reload':
                    for module_name in sys.modules.copy():
                        if mod_or_cog == module_name:
                            module = sys.modules.get(module_name)
                            if module is not None:
                                importlib.reload(module)
                                actions.append(f'+ Module \'{module_name}\' reloaded.')
                                name_found = True
            if not name_found:
                if action == 'reload':
                    actions.append(f'- No cog with the name \'{mod_or_cog}\' found or cog not loaded.')
                else:
                    actions.append(f'- No cog with the name \'{mod_or_cog}\' found or cog already {action}ed.')

        message = ''
        for action in actions:
            message = f'{message}\n{action}'
        await ctx.send(f'```diff\n{message}\n```')

    # Enable/disable commands
    @dev.command(aliases=('disable',))
    @commands.is_owner()
    @commands.bot_has_permissions(send_messages=True)
    async def enable(self, ctx: commands.Context, *args: str) -> None:
        if ctx.prefix.lower() == 'rpg ': return
        action = ctx.invoked_with
        if args:
            command = ''
            for arg in args:
                command = f'{command} {arg}'
            command = self.bot.get_command(command)
            if command is None:
                await ctx.reply(
                    'No command with that name found.'
                    )
            elif ctx.command == command:
                await ctx.reply(
                    f'You can not {action} this command.'
                    )
            else:
                if action == 'enable':
                    command.enabled = True
                else:
                    command.enabled = False
                await ctx.reply(
                    f'Command {command.qualified_name} {action}d.'
                    )
        else:
            await ctx.reply(
                f'Syntax is `{ctx.prefix}{ctx.command} [command]`'
                )

    # Convert timestring to iso format
    @dev.command(aliases=('ts',))
    @commands.is_owner()
    @commands.bot_has_permissions(send_messages=True)
    async def timestamp(self, ctx: commands.Context, timestamp: int) -> None:
        if ctx.prefix.lower() == 'rpg ': return
        await ctx.send(datetime.fromtimestamp(timestamp).isoformat(sep=' '))

    # List servers
    @dev.command()
    @commands.is_owner()
    @commands.bot_has_permissions(send_messages=True)
    async def servers(self, ctx: commands.Context) -> None:
        if ctx.prefix.lower() == 'rpg ': return
        server_list = ''
        for guild in self.bot.guilds:
            server_list = f'{server_list}\n{emojis.BP} {guild.name}'
        await ctx.send(server_list)

    # Test command
    @dev.command()
    @commands.is_owner()
    @commands.bot_has_permissions(send_messages=True)
    async def test(self, ctx: commands.Context) -> None:
        if ctx.prefix.lower() == 'rpg ': return
        import re
        from database import users
        from resources import exceptions
        message_field_name = '<:catpet:703150997517893692> SUDDENLY, A **DRAGON** TIER **II** IS APPROACHING **Miruel**'
        message_field_value = ':heart: **Happiness:** 12\n:taco: **Hunger:** 64'
        user_name = user = None
        try:
            user_name = re.search("APPROACHING \*\*(.+?)\*\*", message_field_name).group(1)
            user_name = user_name.encode('unicode-escape',errors='ignore').decode('ASCII').replace('\\','')
        except Exception as error:
            await ctx.message.add_reaction(emojis.WARNING)
            #await errors.log_error(error)
            return
        for member in ctx.guild.members:
            member_name = member.name.encode('unicode-escape',errors='ignore').decode('ASCII').replace('\\','')
            if member_name == user_name:
                user = member
                break
        if user is None:
            await ctx.message.add_reaction(emojis.WARNING)
            #await errors.log_error(f'User not found in pet catch message: {message}')
            return
        try:
            user_settings: users.User = await users.get_user(user.id)
        except exceptions.FirstTimeUserError:
            return
        if not user_settings.bot_enabled or not user_settings.pet_helper_enabled: return
        try:
            happiness = re.search("Happiness:\*\* (.+?)\\n", message_field_value).group(1)
            happiness = int(happiness)
            hunger = re.search("Hunger:\*\* (.+?)$", message_field_value).group(1)
            hunger = int(hunger)
        except Exception as error:
            await ctx.message.add_reaction(emojis.WARNING)
            #await errors.log_error(error)
            return
        feeds = hunger // 20
        hunger_rest = hunger % 20
        if hunger_rest >= 10:
            feeds += 1
            hunger_rest = hunger_rest - 18
            if hunger_rest < 0: hunger_rest = 0
        happiness_missing = (hunger_rest + 85) - happiness
        pats = happiness_missing // 10
        happiness_rest = happiness_missing % 10
        if happiness_rest > 5: pats += 1
        if feeds + pats > 6: pats = 6 - feeds
        hunger_remaining_min = hunger - (feeds * 22)
        if hunger_remaining_min < 0: hunger_remaining_min = 0
        hunger_remaining_max = hunger - (feeds * 18)
        if hunger_remaining_max < 0: hunger_remaining_max = 0
        happiness_remaining_min = happiness + (pats * 8)
        if happiness_remaining_min < 0: happiness_remaining_min = 0
        happiness_remaining_max = happiness + (pats * 12)
        if happiness_remaining_max < 0: happiness_remaining_max = 0
        difference_best = happiness_remaining_max - hunger_remaining_min
        difference_worst = happiness_remaining_min - hunger_remaining_max
        chance_min = 100 / 85 * difference_worst
        chance_max = 100 / 85 * difference_best
        if chance_min > 100: chance_min = 100
        if chance_max > 100: chance_max = 100

        commands = ''
        for x in range(0, feeds):
            commands = f'{commands} feed'
        for x in range(0, pats):
            commands = f'{commands} pat'
        embed = discord.Embed(
            description = f'`{commands.upper().strip()}`'
        )
        #embed.add_field(name='COMMANDS', value=f'```{commands.upper().strip()}```', inline=False)
        embed.set_footer(text=f'Catch chance: {chance_min:.2f} - {chance_max:.2f}%')
        await ctx.reply(embed=embed)


def setup(bot):
    bot.add_cog(DevCog(bot))