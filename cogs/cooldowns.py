# cooldowns.py

import re

import discord
from discord.ext import commands
from datetime import timedelta

from database import errors, reminders, users
from resources import emojis, exceptions, functions, settings, strings


class CooldownsCog(commands.Cog):
    """Cog that contains the cooldowns detection commands"""
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message_edit(self, message_before: discord.Message, message_after: discord.Message) -> None:
        """Runs when a message is edited in a channel."""
        await self.on_message(message_after)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """Runs when a message is sent in a channel."""
        if message.author.id != settings.EPIC_RPG_ID: return

        if not message.embeds: return
        embed: discord.Embed = message.embeds[0]
        message_author = message_footer = message_fields = icon_url = ''
        if embed.author:
            message_author = str(embed.author.name)
            icon_url = embed.author.icon_url
        for field in embed.fields:
            message_fields = f'{message_fields}\n{str(field.value)}'.strip()
        if embed.footer: message_footer = str(embed.footer.text)

        # Cooldown
        search_strings = [
            'check the short version of this command', #English
            'revisa la versión más corta de este comando', #Spanish
            'verifique a versão curta deste comando', #Portuguese
        ]
        if any(search_string in message_footer.lower() for search_string in search_strings):
            user_id = user_name = None
            user = await functions.get_interaction_user(message)
            slash_command = True if user is not None else False
            if user is None:
                user_id_match = re.search(strings.REGEX_USER_ID_FROM_ICON_URL, icon_url)
                if user_id_match:
                    user_id = int(user_id_match.group(1))
                else:
                    user_name_match = re.search(strings.REGEX_USERNAME_FROM_EMBED_AUTHOR, message_author)
                    if user_name_match:
                        user_name = await functions.encode_text(user_name_match.group(1))
                    else:
                        await functions.add_warning_reaction(message)
                        await errors.log_error('User not found in cooldown message.', message)
                        return
                if user_id is not None:
                    user = await message.guild.fetch_member(user_id)
                else:
                    user = await functions.get_guild_member_by_name(message.guild, user_name)
            if user is None:
                await functions.add_warning_reaction(message)
                await errors.log_error('User not found in cooldowns message.', message)
                return
            try:
                user_settings: users.User = await users.get_user(user.id)
            except exceptions.FirstTimeUserError:
                return
            if not user_settings.bot_enabled: return
            cooldowns = []
            ready_commands = []
            if user_settings.alert_daily.enabled:
                daily_match = re.search(r"daily`\*\* \(\*\*(.+?)\*\*", message_fields.lower())
                if daily_match:
                    daily_timestring = daily_match.group(1)
                    if slash_command:
                        user_command = await functions.get_slash_command(user_settings, 'daily')
                    else:
                        user_command = '`rpg daily`'
                    daily_message = user_settings.alert_daily.message.replace('{command}', user_command)
                    cooldowns.append(['daily', daily_timestring.lower(), daily_message])
                else:
                    ready_commands.append('daily')
            if user_settings.alert_weekly.enabled:
                weekly_match = re.search(r"weekly`\*\* \(\*\*(.+?)\*\*", message_fields.lower())
                if weekly_match:
                    weekly_timestring = weekly_match.group(1)
                    if slash_command:
                        user_command = await functions.get_slash_command(user_settings, 'weekly')
                    else:
                        user_command = '`rpg daily`'
                    weekly_message = user_settings.alert_weekly.message.replace('{command}', user_command)
                    cooldowns.append(['weekly', weekly_timestring.lower(), weekly_message])
                else:
                    ready_commands.append('weekly')
            if user_settings.alert_lootbox.enabled:
                lb_match = re.search(r"lootbox`\*\* \(\*\*(.+?)\*\*", message_fields.lower())
                if lb_match:
                    lootbox_name = '[lootbox]'
                    if user_settings.last_lootbox != '':
                        lootbox_name = f'{user_settings.last_lootbox} lootbox'
                    if slash_command:
                        user_command = await functions.get_slash_command(user_settings, 'buy')
                        user_command = f"{user_command} `item: {lootbox_name}`"
                    else:
                        user_command = f'`rpg buy {lootbox_name}`'
                    lb_timestring = lb_match.group(1)
                    lb_message = user_settings.alert_lootbox.message.replace('{command}', user_command)
                    cooldowns.append(['lootbox', lb_timestring.lower(), lb_message])
                else:
                    ready_commands.append('lootbox')
            if user_settings.alert_hunt.enabled:
                hunt_match = re.search(r'hunt(?: hardmode)?`\*\* \(\*\*(.+?)\*\*', message_fields.lower())
                if hunt_match:
                    if user_settings.last_hunt_mode != '':
                        if slash_command:
                            user_command = await functions.get_slash_command(user_settings, 'hunt')
                            user_command = f"{user_command} `mode: {user_settings.last_hunt_mode}`"
                        else:
                            user_command = f'`rpg hunt {user_settings.last_hunt_mode}`'
                    else:
                        if 'hardmode' in hunt_match.group(0):
                            if slash_command:
                                user_command = await functions.get_slash_command(user_settings, 'hunt')
                                user_command = f"{user_command} `mode: hardmode`"
                            else:
                                user_command = '`rpg hunt hardmode`'
                        else:
                            if slash_command:
                                user_command = await functions.get_slash_command(user_settings, 'hunt')
                            else:
                                user_command = '`rpg hunt`'
                    hunt_timestring = hunt_match.group(1)
                    if ('together' in user_settings.last_hunt_mode
                        and user_settings.partner_donor_tier < user_settings.user_donor_tier):
                        time_left = await functions.calculate_time_left_from_timestring(message, hunt_timestring.lower())
                        partner_donor_tier = 3 if user_settings.partner_donor_tier > 3 else user_settings.partner_donor_tier
                        user_donor_tier = 3 if user_settings.user_donor_tier > 3 else user_settings.user_donor_tier
                        time_difference = ((60 * settings.DONOR_COOLDOWNS[partner_donor_tier])
                                        - (60 * settings.DONOR_COOLDOWNS[user_donor_tier]))
                        time_left_seconds = time_left.total_seconds() + time_difference
                        hunt_timestring = await functions.parse_timedelta_to_timestring(timedelta(seconds=time_left_seconds))
                    hunt_message = user_settings.alert_hunt.message.replace('{command}', user_command)
                    cooldowns.append(['hunt', hunt_timestring.lower(), hunt_message])
                else:
                    ready_commands.append('hunt')
            if user_settings.alert_adventure.enabled:
                adv_match = re.search(r'adventure(?: hardmode)?`\*\* \(\*\*(.+?)\*\*', message_fields.lower())
                if adv_match:
                    if user_settings.last_adventure_mode != '':
                        if slash_command:
                            user_command = await functions.get_slash_command(user_settings, 'adventure')
                            user_command = f"{user_command} `mode: {user_settings.last_adventure_mode}`"
                        else:
                            user_command = f'`rpg adventure {user_settings.last_adventure_mode}`'
                    else:
                        if 'hardmode' in adv_match.group(0):
                            if slash_command:
                                user_command = await functions.get_slash_command(user_settings, 'adventure')
                                user_command = f"{user_command} `mode: hardmode`"
                            else:
                                user_command = '`rpg adventure hardmode`'
                        else:
                            if slash_command:
                                user_command = await functions.get_slash_command(user_settings, 'adventure')
                            else:
                                user_command = '`rpg adventure`'
                    adv_timestring = adv_match.group(1)
                    adv_message = user_settings.alert_adventure.message.replace('{command}', user_command)
                    cooldowns.append(['adventure', adv_timestring.lower(), adv_message])
                else:
                    ready_commands.append('adventure')
            if user_settings.alert_training.enabled:
                tr_match = re.search(r"raining`\*\* \(\*\*(.+?)\*\*", message_fields.lower())
                if tr_match:
                    if slash_command:
                        user_command = await functions.get_slash_command(user_settings, user_settings.last_training_command)
                    else:
                        user_command = f'`rpg {user_settings.last_training_command}`'
                    tr_timestring = tr_match.group(1)
                    tr_message = user_settings.alert_training.message.replace('{command}', user_command)
                    cooldowns.append(['training', tr_timestring.lower(), tr_message])
                else:
                    ready_commands.append('training')
            if user_settings.alert_quest.enabled:
                quest_match = re.search(r"quest`\*\* \(\*\*(.+?)\*\*", message_fields.lower())
                if quest_match:
                    if slash_command:
                        user_command = await functions.get_slash_command(user_settings, user_settings.last_quest_command)
                    else:
                        user_command = f'`rpg {user_settings.last_quest_command}`'
                    quest_timestring = quest_match.group(1)
                    quest_message = user_settings.alert_quest.message.replace('{command}', user_command)
                    cooldowns.append(['quest', quest_timestring.lower(), quest_message])
                else:
                    ready_commands.append('quest')
            if user_settings.alert_duel.enabled:
                duel_match = re.search(r"duel`\*\* \(\*\*(.+?)\*\*", message_fields.lower())
                if duel_match:
                    duel_timestring = duel_match.group(1)
                    if slash_command:
                        user_command = await functions.get_slash_command(user_settings, 'duel')
                    else:
                        user_command = '`rpg duel`'
                    duel_message = user_settings.alert_duel.message.replace('{command}', user_command)
                    cooldowns.append(['duel', duel_timestring.lower(), duel_message])
                else:
                    ready_commands.append('duel')
            if user_settings.alert_arena.enabled:
                arena_match = re.search(r"rena`\*\* \(\*\*(.+?)\*\*", message_fields.lower())
                if arena_match:
                    arena_timestring = arena_match.group(1)
                    if slash_command:
                        user_command = await functions.get_slash_command(user_settings, 'arena')
                    else:
                        user_command = '`rpg arena`'
                    arena_message = user_settings.alert_arena.message.replace('{command}', user_command)
                    cooldowns.append(['arena', arena_timestring.lower(), arena_message])
                else:
                    ready_commands.append('arena')
            if user_settings.alert_dungeon_miniboss.enabled:
                dungmb_match = re.search(r"boss`\*\* \(\*\*(.+?)\*\*", message_fields.lower())
                if dungmb_match:
                    dungmb_timestring = dungmb_match.group(1)
                    if slash_command:
                        command_dungeon = await functions.get_slash_command(user_settings, 'dungeon')
                        command_miniboss = await functions.get_slash_command(user_settings, 'miniboss')
                        user_command = f"{command_dungeon} or {command_miniboss}"
                    else:
                        user_command = '`rpg dungeon` or `rpg miniboss`'
                    dungmb_message = user_settings.alert_dungeon_miniboss.message.replace('{command}', user_command)
                    cooldowns.append(['dungeon-miniboss', dungmb_timestring.lower(), dungmb_message])
                else:
                    ready_commands.append('dungeon-miniboss')
            if user_settings.alert_horse_breed.enabled:
                horse_match = re.search(r"race`\*\* \(\*\*(.+?)\*\*", message_fields.lower())
                if horse_match:
                    horse_timestring = horse_match.group(1)
                    if slash_command:
                        command_breed = await functions.get_slash_command(user_settings, 'horse breeding')
                        command_race = await functions.get_slash_command(user_settings, 'horse race')
                        user_command = f"{command_breed} or {command_race}"
                    else:
                        user_command = '`rpg horse breed` or `rpg horse race`'
                    horse_message = user_settings.alert_horse_breed.message.replace('{command}', user_command)
                    cooldowns.append(['horse', horse_timestring.lower(), horse_message])
                else:
                    ready_commands.append('horse')
            if user_settings.alert_vote.enabled:
                vote_match = re.search(r"vote`\*\* \(\*\*(.+?)\*\*", message_fields.lower())
                if vote_match:
                    vote_timestring = vote_match.group(1)
                    if slash_command:
                        user_command = await functions.get_slash_command(user_settings, 'vote')
                    else:
                        user_command = '`rpg vote`'
                    vote_message = user_settings.alert_vote.message.replace('{command}', user_command)
                    cooldowns.append(['vote', vote_timestring.lower(), vote_message])
                else:
                    ready_commands.append('vote')
            if user_settings.alert_farm.enabled:
                farm_match = re.search(r"farm`\*\* \(\*\*(.+?)\*\*", message_fields.lower())
                if farm_match:
                    farm_timestring = farm_match.group(1)
                    if slash_command:
                        user_command = await functions.get_slash_command(user_settings, 'farm')
                        if user_settings.last_farm_seed != '':
                            user_command = f'{user_command} `seed: {user_settings.last_farm_seed}`'
                    else:
                        user_command = 'rpg farm'
                        if user_settings.last_farm_seed != '':
                            user_command = f'{user_command} {user_settings.last_farm_seed}'
                        user_command = f'`{user_command}`'
                    farm_message = user_settings.alert_farm.message.replace('{command}', user_command)
                    cooldowns.append(['farm', farm_timestring.lower(), farm_message])
                else:
                    ready_commands.append('farm')
            if user_settings.alert_work.enabled:
                search_patterns = [
                    r'mine`\*\* \(\*\*(.+?)\*\*',
                    r'pickaxe`\*\* \(\*\*(.+?)\*\*',
                    r'drill`\*\* \(\*\*(.+?)\*\*',
                    r'dynamite`\*\* \(\*\*(.+?)\*\*',
                ]
                work_match = await functions.get_match_from_patterns(search_patterns, message_fields.lower())
                if work_match:
                    if user_settings.last_work_command != '':
                        if slash_command:
                            user_command = await functions.get_slash_command(user_settings, user_settings.last_work_command)
                        else:
                            user_command = f'`rpg {user_settings.last_work_command}`'
                    else:
                        user_command = 'work command'
                    work_timestring = work_match.group(1)
                    work_message = user_settings.alert_work.message.replace('{command}', user_command)
                    cooldowns.append(['work', work_timestring.lower(), work_message])
                else:
                    ready_commands.append('work')
            for cooldown in cooldowns:
                cd_activity = cooldown[0]
                cd_timestring = cooldown[1]
                cd_message = cooldown[2]
                time_left = await functions.calculate_time_left_from_timestring(message, cd_timestring)
                if time_left.total_seconds() > 0:
                    reminder: reminders.Reminder = (
                        await reminders.insert_user_reminder(user.id, cd_activity, time_left,
                                                            message.channel.id, cd_message, overwrite_message=False)
                    )
                    if not reminder.record_exists:
                        await message.channel.send(strings.MSG_ERROR)
                        return
            for activity in ready_commands:
                try:
                    reminder: reminders.Reminder = await reminders.get_user_reminder(user.id, activity)
                except exceptions.NoDataFoundError:
                    continue
                await reminder.delete()
                if reminder.record_exists:
                    await functions.add_warning_reaction(message)
                    await errors.log_error(f'Had an error deleting the reminder with activity "{activity}".', message)
            if user_settings.reactions_enabled: await message.add_reaction(emojis.NAVI)

        # Ready
        search_strings = [
            'check the long version of this command', #English
            'revisa la versión más larga de este comando', #Spanish
            'verifique a versão longa deste comando', #Portuguese
        ]
        if any(search_string in message_footer.lower() for search_string in search_strings):
            user_id = user_name = None
            user = await functions.get_interaction_user(message)
            slash_command = True if user is not None else False
            if user is None:
                user_id_match = re.search(strings.REGEX_USER_ID_FROM_ICON_URL, icon_url)
                if user_id_match:
                    user_id = int(user_id_match.group(1))
                else:
                    user_name_match = re.search(strings.REGEX_USERNAME_FROM_EMBED_AUTHOR, message_author)
                    if user_name_match:
                        user_name = await functions.encode_text(user_name_match.group(1))
                    else:
                        await functions.add_warning_reaction(message)
                        await errors.log_error('User not found in ready message.', message)
                        return
                if user_id is not None:
                    user = await message.guild.fetch_member(user_id)
                else:
                    user = await functions.get_guild_member_by_name(message.guild, user_name)
            if user is None:
                await functions.add_warning_reaction(message)
                await errors.log_error('User not found in ready message.', message)
                return
            try:
                user_settings: users.User = await users.get_user(user.id)
            except exceptions.FirstTimeUserError:
                return
            if not user_settings.bot_enabled: return
            ready_commands = []
            if user_settings.alert_daily.enabled and 'daily`**' in message_fields.lower():
                ready_commands.append('daily')
            if user_settings.alert_weekly.enabled and 'weekly`**' in message_fields.lower():
                ready_commands.append('weekly')
            if user_settings.alert_lootbox.enabled and 'lootbox`**' in message_fields.lower():
                ready_commands.append('lootbox')
            if user_settings.alert_hunt.enabled:
                hunt_match = re.search(r'hunt(?: hardmode)?`\*\*', message_fields.lower())
                if hunt_match: ready_commands.append('hunt')
            if user_settings.alert_adventure.enabled:
                adv_match = re.search(r'adventure(?: hardmode)?`\*\*', message_fields.lower())
                if adv_match: ready_commands.append('adventure')
            if user_settings.alert_training.enabled and 'raining`**' in message_fields.lower():
                ready_commands.append('training')
            if user_settings.alert_quest.enabled and 'quest`**' in message_fields.lower():
                ready_commands.append('quest')
            if user_settings.alert_duel.enabled and 'duel`**' in message_fields.lower():
                ready_commands.append('duel')
            if user_settings.alert_arena.enabled and 'rena`**' in message_fields.lower():
                ready_commands.append('arena')
            if user_settings.alert_dungeon_miniboss.enabled and 'boss`**' in message_fields.lower():
                ready_commands.append('dungeon-miniboss')
            if user_settings.alert_horse_breed.enabled and 'race`**' in message_fields.lower():
                ready_commands.append('horse')
            if user_settings.alert_vote.enabled and 'vote`**' in message_fields.lower():
                ready_commands.append('vote')
            if user_settings.alert_farm.enabled and 'farm`**' in message_fields.lower():
                ready_commands.append('farm')
            if user_settings.alert_work.enabled:
                search_strings_work = [
                    r'mine`**',
                    r'pickaxe`**',
                    r'drill`**',
                    r'dynamite`**',
                ]
                if any(search_string in message_fields.lower() for search_string in search_strings_work):
                    ready_commands.append('work')
            for activity in ready_commands:
                try:
                    reminder: reminders.Reminder = await reminders.get_user_reminder(user.id, activity)
                except exceptions.NoDataFoundError:
                    continue
                await reminder.delete()
                if reminder.record_exists:
                    await functions.add_warning_reaction(message)
                    await errors.log_error(f'Had an error deleting the reminder with activity "{activity}".', message)
            if user_settings.reactions_enabled: await message.add_reaction(emojis.NAVI)


# Initialization
def setup(bot):
    bot.add_cog(CooldownsCog(bot))