import discord
from discord.ext import commands
import os
from datetime import datetime, timedelta

intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
intents.members = True
bot = commands.Bot(command_prefix='!', intents=intents)
my_secret = os.environ['BOT_TOKEN']

crota_icon_url = 'https://i.insider.com/5800ec6c52dd73d0018b4e21?width=750&format=jpeg&auto=webp'
default_icon = 'https://i.insider.com/5800ec6c52dd73d0018b4e21?width=750&format=jpeg&auto=webp'

raids = {}
cooldown = {}


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    print(f'Bot is connected to the following guilds:')
    for guild in bot.guilds:
        print(f'- {guild.name} (id: {guild.id})')


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    print(f'Message from {message.author}: {message.content}')
    await bot.process_commands(message)


def get_emoji(guild, name):
    for emoji in guild.emojis:
        if emoji.name == name:
            return emoji
    return None


@bot.command(name='create:raid')
async def create_raid(ctx,
                      raid_name: str = None,
                      raid_day: str = None,
                      raid_time: str = None):
    """Erstellt einen neuen Raid mit dem angegebenen Namen, Zeitpunkt und Tag."""
    if raid_name is None or raid_day is None or raid_time is None:
        missing_params = []
        if raid_name is None:
            missing_params.append('raid_name')
        if raid_day is None:
            missing_params.append('raid_day')
        if raid_time is None:
            missing_params.append('raid_time')

        # Construct the error message
        error_msg = f'Du hast den Parameter {" und ".join(missing_params)} vergessen!'
        example_msg = 'Beispiel: `!create:raid "Vault of Glass" Montag 20`'

        await ctx.send(f'{error_msg}\n{example_msg}')
        return

    if raid_name in raids:
        await ctx.send('Ein Raid mit diesem Namen existiert bereits!')
    else:
        raid_datetime = f"{raid_day} {raid_time}:00 Uhr"
        raids[raid_name] = {"time": raid_datetime, "yes": [], "tentative": []}
        embed = discord.Embed(title=raid_name,
                              description=f"{raid_datetime}\n\n\n")
        if raid_name.lower() == 'crota':
            embed.set_thumbnail(url=crota_icon_url)
        else:
            embed.set_thumbnail(url=default_icon)

        hunter_emoji = get_emoji(ctx.guild, "classhunter")
        warlock_emoji = get_emoji(ctx.guild, "classwarlock")
        titan_emoji = get_emoji(ctx.guild, "classtitan")
        tentative_emoji = get_emoji(ctx.guild, "tentative")
        remove_emoji = get_emoji(ctx.guild, "remove")

        if not hunter_emoji or not warlock_emoji or not titan_emoji or not tentative_emoji or not remove_emoji:
            await ctx.send(
                'Stelle sicher, dass die Emojis mit den Namen classhunter, classwarlock, classtitan, tentative und remove in diesem Server vorhanden sind.'
            )
            return

        embed.add_field(
            name="Klasse wählen",
            value=
            f"{hunter_emoji} Hunter\n{warlock_emoji} Warlock\n{titan_emoji} Titan",
            inline=False)
        message = await ctx.send(embed=embed)

        await message.add_reaction(hunter_emoji)
        await message.add_reaction(warlock_emoji)
        await message.add_reaction(titan_emoji)
        await message.add_reaction(tentative_emoji)
        await message.add_reaction(remove_emoji)


@bot.event
async def on_reaction_add(reaction, user):
    if user.bot:
        return

    message = reaction.message
    if not message.embeds:
        return

    embed = message.embeds[0]
    raid_name = embed.title

    if raid_name not in raids:
        return

    user_choices = raids[raid_name]
    guild = message.guild

    hunter_emoji = get_emoji(guild, "classhunter")
    warlock_emoji = get_emoji(guild, "classwarlock")
    titan_emoji = get_emoji(guild, "classtitan")
    tentative_emoji = get_emoji(guild, "tentative")
    remove_emoji = get_emoji(guild, "remove")

    current_emoji = str(reaction.emoji)
    if current_emoji not in [
            str(hunter_emoji),
            str(warlock_emoji),
            str(titan_emoji),
            str(tentative_emoji),
            str(remove_emoji)
    ]:
        return

    # Check cooldown for user
    if user.id in cooldown and datetime.now() < cooldown[user.id]:
        await message.remove_reaction(reaction.emoji, user)
        return

    # Set cooldown (2 seconds)
    cooldown[user.id] = datetime.now() + timedelta(seconds=2)

    # Remove user if they react with the "remove" emoji
    if current_emoji == str(remove_emoji):
        removed = False
        for choice in ["yes", "tentative"]:
            for entry in user_choices[
                    choice][:]:  # Make a copy to avoid modification issues
                if user.name in entry:
                    user_choices[choice].remove(entry)
                    removed = True
                    break
            if removed:
                break
    else:
        # Remove previous reaction if user is switching classes
        for choice in ["yes", "tentative"]:
            for entry in user_choices[choice]:
                if user.name in entry:
                    previous_class = entry.split(' ')[0]
                    user_choices[choice].remove(entry)
                    # Remove old reaction
                    for react in message.reactions:
                        if str(react.emoji) == previous_class:
                            async for u in react.users():
                                if u.id == user.id:
                                    await react.remove(user)
                            break
                    break

        # Add user's new reaction
        if current_emoji == str(tentative_emoji):
            user_choices["tentative"].append(f"{current_emoji} {user.name}")
            if len(user_choices["yes"]) > 6:
                moved_player = user_choices["yes"].pop()
                user_choices["tentative"].append(moved_player)
        else:
            user_choices["yes"].append(f"{current_emoji} {user.name}")
            if len(user_choices["yes"]) > 6:
                moved_player = user_choices["yes"].pop()
                user_choices["tentative"].append(moved_player)

    # Update embed
    updated_embed = discord.Embed(
        title=raid_name,
        description=f"{user_choices['time']}\u200b\u200b\u200b\u200b\n\n")
    updated_embed.add_field(name="\u200b", value="\u200b",
                            inline=False)  # Empty field for spacing
    if raid_name.lower() == 'crota':
        updated_embed.set_thumbnail(url=crota_icon_url)
    else:
        updated_embed.set_thumbnail(url=default_icon)

    if user_choices["yes"]:
        updated_embed.add_field(name="Teilnehmer",
                                value=f"{', '.join(user_choices['yes'])}",
                                inline=False)

    if user_choices["tentative"]:
        updated_embed.add_field(
            name="Benched",
            value=f"{', '.join(user_choices['tentative'])}",
            inline=True)

    await message.edit(embed=updated_embed)


@bot.command(name='delete:raid')
async def delete_raid(ctx, raid_name: str):
    """Löscht einen existierenden Raid."""
    if raid_name not in raids:
        await ctx.send('Dieser Raid existiert nicht!')
    else:
        del raids[raid_name]
        await ctx.send(f'Der Raid {raid_name} wurde gelöscht!')


@bot.command(name='list:raids')
async def list_raids(ctx):
    """Listet alle aktiven Raids auf."""
    if not raids:
        await ctx.send('Es gibt keine aktiven Raids.')
    else:
        for raid_name, raid_info in raids.items():
            embed = discord.Embed(title=raid_name,
                                  description=f"{raid_info['time']}\n\n\n")
            if raid_name.lower() == 'crota':
                embed.set_thumbnail(url=crota_icon_url)
            else:
                embed.set_thumbnail(url=default_icon)

            if raid_info["yes"]:
                embed.add_field(name="Teilnehmen",
                                value=f"{', '.join(raid_info['yes'])}",
                                inline=False)

            if raid_info["tentative"]:
                embed.add_field(name="Unsicher",
                                value=f"{', '.join(raid_info['tentative'])}",
                                inline=True)

            await ctx.send(embed=embed)


@bot.command(name='hilfe')
async def help_command(ctx):
    """Zeigt diese Hilfemeldung an."""
    embed = discord.Embed(title="Hilfe",
                          description="Liste der verfügbaren Befehle:")
    embed.add_field(
        name="!create:raid <raid_name> <raid_time>",
        value=
        "Erstellt einen neuen Raid mit dem angegebenen Namen und Zeitpunkt.",
        inline=False)
    embed.add_field(name="!delete:raid <raid_name>",
                    value="Löscht einen existierenden Raid.",
                    inline=False)
    embed.add_field(name="!list:raids",
                    value="Listet alle aktiven Raids auf.",
                    inline=False)
    embed.add_field(name="!hilfe",
                    value="Zeigt diese Hilfemeldung an.",
                    inline=False)
    await ctx.send(embed=embed)


bot.run(my_secret)
