# events.py

from datetime import datetime, timedelta
import re

import discord
from discord.ext import commands

from database import errors, reminders, users
from resources import exceptions, functions, logs, strings


class HorseFestivalCog(commands.Cog):
    """Cog that contains the horse festival detection commands"""
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """Runs when a message is sent in a channel."""

        if not message.embeds:
            message_content = message.content
            search_strings = [
                'you have not reached the end of this stage', #English
                'aún no has llegado al final de esta etapa', #Spanish
                'você ainda não chegou ao fim desta etapa', #Portuguese
            ]
            if any(search_string in message_content.lower() for search_string in search_strings):
                user_id = user_name = None
                user = await functions.get_interaction_user(message)
                if user is not None:
                    user_command = '`/hf megarace action: start`'
                else:
                    user_command = '`rpg hf megarace start`'
                    if message.mentions:
                        user = message.mentions[0]
                    else:
                        await functions.add_warning_reaction(message)
                        await errors.log_error('Couldn\'t find a user command for the megarace start message.', message)
                        return
                try:
                    user_settings: users.User = await users.get_user(user.id)
                except exceptions.FirstTimeUserError:
                    return
                if not user_settings.bot_enabled or not user_settings.alert_megarace.enabled: return
                search_patterns = [
                    r'be there in \*\*(.+?)\*\*', #English
                    r'allí en \*\*(.+?)\*\*', #Spanish
                    r'lá em \*\*(.+?)\*\*', #Portuguese
                ]
                timestring_match = await functions.get_match_from_patterns(search_patterns, message_content.lower())
                if not timestring_match:
                    await functions.add_warning_reaction(message)
                    await errors.log_error('Timestring not found in megarace start message.', message)
                    return
                timestring = timestring_match.group(1)
                time_left = await functions.calculate_time_left_from_timestring(message, timestring)
                if time_left.total_seconds() == 0: return
                reminder_message = user_settings.alert_megarace.message.replace('{command}', user_command)
                reminder: reminders.Reminder = (
                    await reminders.insert_user_reminder(user.id, 'megarace', time_left,
                                                         message.channel.id, reminder_message)
                )
                await functions.add_reminder_reaction(message, reminder, user_settings)

            search_strings = [
                'you are now in the list of pending players for a tournament', #English
                'you are now in the list of pending players for a tournament', #Spanish, MISSING
                'you are now in the list of pending players for a tournament', #Portuguese, MISSING
            ]
            if any(search_string in message_content.lower() for search_string in search_strings):
                user_id = user_name = None
                user = await functions.get_interaction_user(message)
                if user is not None:
                    user_command = '`/hf minirace`'
                else:
                    user_command = '`rpg hf minirace`'
                    if message.mentions:
                        user = message.mentions[0]
                    else:
                        await functions.add_warning_reaction(message)
                        await errors.log_error('Couldn\'t find a user command for the minirace message.', message)
                        return
                if user is None:
                    await functions.add_warning_reaction(message)
                    await errors.log_error('User not found in minirace message.', message)
                    return
                try:
                    user_settings: users.User = await users.get_user(user.id)
                except exceptions.FirstTimeUserError:
                    return
                if not user_settings.bot_enabled or not user_settings.alert_minirace.enabled: return
                current_time = datetime.utcnow().replace(microsecond=0)
                midnight_today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
                end_time = midnight_today + timedelta(days=1, minutes=6)
                time_left = end_time - current_time
                reminder_message = user_settings.alert_minirace.message.replace('{command}', user_command)
                reminder: reminders.Reminder = (
                    await reminders.insert_user_reminder(user.id, 'minirace', time_left,
                                                         message.channel.id, reminder_message)
                )
                await functions.add_reminder_reaction(message, reminder, user_settings)

            search_strings = [
                'started riding!', #English
                'started riding!', #Spanish, MISSING
                'started riding!', #Portuguese, MISSING
            ]
            if any(search_string in message_content.lower() for search_string in search_strings):
                user_id = user_name = None
                user = await functions.get_interaction_user(message)
                if user is not None:
                    user_command = '`/hf minirace`'
                else:
                    user_command = '`rpg hf minirace`'
                    user_name_match = re.search(strings.REGEX_NAME_FROM_MESSAGE_START, message_content)
                    if user_name_match:
                        user_name = await functions.encode_text(user_name_match.group(1))
                    else:
                        await functions.add_warning_reaction(message)
                        await errors.log_error('User not found in farm event non-slash message.', message)
                        return
                    user = await functions.get_guild_member_by_name(message.guild, user_name)
                if user is None:
                    await functions.add_warning_reaction(message)
                    await errors.log_error('User not found in minirace message.', message)
                    return
                try:
                    user_settings: users.User = await users.get_user(user.id)
                except exceptions.FirstTimeUserError:
                    return
                if not user_settings.bot_enabled or not user_settings.alert_minirace.enabled: return
                current_time = datetime.utcnow().replace(microsecond=0)
                midnight_today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
                end_time = midnight_today + timedelta(days=1, minutes=6)
                time_left = end_time - current_time
                reminder_message = user_settings.alert_minirace.message.replace('{command}', user_command)
                reminder: reminders.Reminder = (
                    await reminders.insert_user_reminder(user.id, 'minirace', time_left,
                                                         message.channel.id, reminder_message)
                )
                await functions.add_reminder_reaction(message, reminder, user_settings)

        if message.embeds:
            embed: discord.Embed = message.embeds[0]
            message_field0_name = message_field1_name = message_field0_value = message_field1_value = message_author = ''
            message_description = ''
            if embed.description: message_description = str(embed.description)
            if embed.author:
                message_author = str(embed.author.name)
                icon_url = embed.author.icon_url
            if embed.fields:
                message_field0_name = embed.fields[0].name
                message_field0_value = embed.fields[0].value
            if len(embed.fields) > 1:
                message_field1_name = embed.fields[1].name
                message_field1_value = embed.fields[1].value

            search_strings = [
                'total time', #English
                'tiempo total', #Spanish
                'tempo total', #Portuguese
            ]
            if (any(search_string in message_field1_name.lower() for search_string in search_strings)
                and 'megarace' in message_author.lower()):
                user_id = user_name = None
                user = await functions.get_interaction_user(message)
                if user is not None:
                    user_command = '`/hf megarace action: start`'
                else:
                    user_command = '`rpg hf megarace start`'
                    user_id_match = re.search(strings.REGEX_USER_ID_FROM_ICON_URL, icon_url)
                    if user_id_match:
                        user_id = int(user_id_match.group(1))
                    else:
                        user_name_match = re.search(strings.REGEX_USERNAME_FROM_EMBED_AUTHOR, message_author)
                        if user_name_match:
                            user_name = await functions.encode_text(user_name_match.group(1))
                        else:
                            await functions.add_warning_reaction(message)
                            await errors.log_error('User name not found in megarace message.', message)
                            return
                    if user_id is not None:
                        try:
                            user = await message.guild.fetch_member(user_id)
                        except:
                            pass
                    else:
                        user = await functions.get_guild_member_by_name(message.guild, user_name)
                if user is None:
                    await functions.add_warning_reaction(message)
                    await errors.log_error('User not found in megarace message.', message)
                    return
                try:
                    user_settings: users.User = await users.get_user(user.id)
                except exceptions.FirstTimeUserError:
                    return
                if not user_settings.bot_enabled or not user_settings.alert_megarace.enabled: return
                search_patterns = [
                    r' \*\*(.+?)\*\* ', #English, Spanish, Portuguese
                ]
                timestring_match = await functions.get_match_from_patterns(search_patterns, message_field1_value.lower())
                if not timestring_match:
                    await functions.add_warning_reaction(message)
                    await errors.log_error('Timestring not found in megarace message.', message)
                    return
                timestring = timestring_match.group(1)
                time_left = await functions.calculate_time_left_from_timestring(message, timestring)
                reminder_message = user_settings.alert_megarace.message.replace('{command}', user_command)
                reminder: reminders.Reminder = (
                    await reminders.insert_user_reminder(user.id, 'megarace', time_left,
                                                         message.channel.id, reminder_message)
                )
                await functions.add_reminder_reaction(message, reminder, user_settings)

            search_strings = [
                'you can join megarace every week', #English
                'puedes entrar a la megacarrera cada semana', #Spanish
                'você pode entrar na mega corrida toda semana', #Portuguese
            ]
            search_strings_completed = [
                'megarace completed', #English
                'megacarrera completada', #Spanish
                'megacorrida completa', #Portuguese
            ]
            if (any(search_string in message_description.lower() for search_string in search_strings)
                and not any(search_string in message_field0_value.lower() for search_string in search_strings_completed)):
                user_id = user_name = None
                user = await functions.get_interaction_user(message)
                if user is not None:
                    user_command = '`/hf megarace action: start`'
                else:
                    user_command = '`rpg hf megarace start`'
                    user_command_message, _ = (
                        await functions.get_message_from_channel_history(message.channel, r"^rpg\s+(?:hf\b|horsefestival\b)\s+megarace\b")
                    )
                    if user_command_message is None:
                        await functions.add_warning_reaction(message)
                        await errors.log_error('Couldn\'t find a user command for the megarace message.', message)
                        return
                    user = user_command_message.author
                try:
                    user_settings: users.User = await users.get_user(user.id)
                except exceptions.FirstTimeUserError:
                    return
                if not user_settings.bot_enabled or not user_settings.alert_megarace.enabled: return
                search_patterns = [
                    r'time remaining\*\*: (.+?)\n', #English
                    r'ti?empo restante\*\*: (.+?)\n', #Spanish, Portuguese
                ]
                timestring_match = await functions.get_match_from_patterns(search_patterns, message_field0_value.lower())
                if not timestring_match:
                    await functions.add_warning_reaction(message)
                    await errors.log_error('Timestring not found in megarace overview message.', message)
                    return
                timestring = timestring_match.group(1)
                if timestring in ('0d 0h 0m 0s', '0h 0m 0s'): return
                time_left = await functions.calculate_time_left_from_timestring(message, timestring)
                reminder_message = user_settings.alert_megarace.message.replace('{command}', user_command)
                reminder: reminders.Reminder = (
                    await reminders.insert_user_reminder(user.id, 'megarace', time_left,
                                                         message.channel.id, reminder_message)
                )
                await functions.add_reminder_reaction(message, reminder, user_settings)

            search_strings = [
                'passes through the boost', #English
            ]
            if any(search_string in message_field0_name.lower() for search_string in search_strings):
                user_id = user_name = None
                user = await functions.get_interaction_user(message)
                if user is not None:
                    user_command = '`/hf megarace action: start`'
                else:
                    user_command = '`rpg hf megarace start`'
                    user_name_match = re.search(strings.REGEX_NAME_FROM_MESSAGE_START, message_field0_name)
                    if user_name_match:
                        user_name = await functions.encode_text(user_name_match.group(1))
                    else:
                        await functions.add_warning_reaction(message)
                        await errors.log_error('User not found in megarace boost message.', message)
                        return
                    user = await functions.get_guild_member_by_name(message.guild, user_name)
                if user is None:
                    await functions.add_warning_reaction(message)
                    await errors.log_error('User not found in megarace boost message.', message)
                    return
                try:
                    user_settings: users.User = await users.get_user(user.id)
                except exceptions.FirstTimeUserError:
                    return
                if not user_settings.bot_enabled or not user_settings.alert_megarace.enabled: return
                search_patterns = [
                    r'(?:increased|reduced)__: \*\*(.+?)\*\*', #English
                ]
                timestring_match = await functions.get_match_from_patterns(search_patterns, message_field0_value.lower())
                if not timestring_match:
                    await functions.add_warning_reaction(message)
                    await errors.log_error('Timestring not found in megarace boost message.', message)
                    return
                timestring = timestring_match.group(1)
                logs.logger.info(f'Megarace: Timestring {timestring} found.')
                time_left = await functions.calculate_time_left_from_timestring(message, timestring)
                logs.logger.info(f'Megarace: Time left: {time_left}.')
                try:
                    reminder: reminders.Reminder = await reminders.get_user_reminder(user.id, 'megarace')
                except exceptions.NoDataFoundError:
                    logs.logger.info(f'Megarace: No active reminder found, exiting.')
                    return
                search_strings_increased = [
                    'stage time increased', #English
                ]
                search_strings_reduced = [
                    'stage time reduced', #English
                ]
                if any(search_string in message_field0_value.lower() for search_string in search_strings_increased):
                    new_end_time = reminder.end_time + time_left
                    logs.logger.info(f'Megarace: Time increased, new end time: {new_end_time}.')
                elif any(search_string in message_field0_value.lower() for search_string in search_strings_reduced):
                    new_end_time = reminder.end_time - time_left
                    logs.logger.info(f'Megarace: Time reduced, new end time: {new_end_time}.')
                logs.logger.info(f'Megarace: Reminder old end time: {reminder.end_time}.')
                await reminder.update(end_time=new_end_time)
                logs.logger.info(f'Megarace: Reminder updated, new end time: {reminder.end_time}.')
                await functions.add_reminder_reaction(message, reminder, user_settings)

            # Megarace helper
            if '— megarace' in message_author.lower():
                user_name = user_id = None
                user = await functions.get_interaction_user(message)
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
                            await errors.log_error('User not found in megarace message for megarace helper.', message)
                            return
                    if user_id is not None:
                        user = await message.guild.fetch_member(user_id)
                    else:
                        user = await functions.get_guild_member_by_name(message.guild, user_name)
                if user is None:
                    await functions.add_warning_reaction(message)
                    await errors.log_error('User not found in megarace helper message.', message)
                    return
                try:
                    user_settings: users.User = await users.get_user(user.id)
                except exceptions.FirstTimeUserError:
                    return
                if not user_settings.bot_enabled or not user_settings.megarace_helper_enabled: return
                answer = await functions.get_megarace_answer(message)
                if answer is None: return
                if user_settings.dnd_mode_enabled:
                    await message.reply(answer)
                else:
                    answer = f'{answer} {user.mention}' if user_settings.ping_after_message else f'{user.mention} {answer}'
                    await message.reply(answer)

            # Minirace embed
            if '— minirace' in message_author.lower():
                user_name = user_id = None
                user = await functions.get_interaction_user(message)
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
                            await errors.log_error('User not found in minirace embed.', message)
                            return
                    if user_id is not None:
                        user = await message.guild.fetch_member(user_id)
                    else:
                        user = await functions.get_guild_member_by_name(message.guild, user_name)
                if user is None:
                    await functions.add_warning_reaction(message)
                    await errors.log_error('User not found in minirace embed.', message)
                    return
                try:
                    user_settings: users.User = await users.get_user(user.id)
                except exceptions.FirstTimeUserError:
                    return
                if not user_settings.bot_enabled or not user_settings.alert_minirace.enabled: return
                current_time = datetime.utcnow().replace(microsecond=0)
                midnight_today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
                end_time = midnight_today + timedelta(days=1, minutes=6)
                time_left = end_time - current_time
                reminder_message = user_settings.alert_minirace.message.replace('{command}', user_command)
                reminder: reminders.Reminder = (
                    await reminders.insert_user_reminder(user.id, 'minirace', time_left,
                                                         message.channel.id, reminder_message)
                )
                await functions.add_reminder_reaction(message, reminder, user_settings)


# Initialization
def setup(bot):
    bot.add_cog(HorseFestivalCog(bot))