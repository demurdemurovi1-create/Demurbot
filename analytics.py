import shared_info
import discord
import analytics_commands as ac

commandFuncs = {
    'calls': ac.calls,
    'mostused': ac.mostusedcommands,
    'leastused': ac.leastusedcommands,
    'mostactive': ac.mostactiveusers,
    'servers': ac.servers
}

async def process_text(text, message):
    command = str.lower(text[0])

    if command == 'echo':
        echo_text = " ".join(message.content.split(" ")[1:])
        try:
            prefix = shared_info.serversList[str(message.guild.id)]['prefix']
        except:
            prefix = '-'
        blocked_prefixes = ['-', '!', '/', '.', '?', '$', '%', '>', '<', '`']
        blocked_prefixes.append(prefix)
        for blocked in blocked_prefixes:
            if echo_text.strip().startswith(blocked):
                await message.channel.send("Error: Cannot echo text that looks like a command.")
                return
        echo_text = echo_text.replace("@", "")
        await message.channel.send(echo_text)
        return

    if command in ('addsynergy', 'removesynergy', 'synergylist'):
        import commands as _commands
        import basics
        settings = shared_info.serversList[str(message.guild.id)]
        blocked = settings.setdefault('synergyblocked', [])
        builtin = sorted(shared_info.SYNERGY_COMMANDS)
        if command == 'synergylist':
            await message.channel.send("Blocked when synergy is off: " + ", ".join(f"`{c}`" for c in builtin + blocked))
            return
        if len(text) < 2:
            await message.channel.send(f"Usage: `{command} <command name>`, e.g. `{command} composites`")
            return
        name = str.lower(text[1]).lstrip(settings.get('prefix', '-'))
        if command == 'addsynergy':
            if name not in _commands.commands:
                await message.channel.send(f"`{name}` is not a command.")
            elif name in ('edit', 'addsynergy', 'removesynergy', 'help'):
                await message.channel.send(f"`{name}` can't be blocked.")
            elif name in builtin or name in blocked:
                await message.channel.send(f"`{name}` is already on the block list.")
            else:
                blocked.append(name)
                await basics.save_db(shared_info.serversList)
                state = "off" if str(settings.get('synergy', 'on')).lower() == 'off' else "on"
                await message.channel.send(f"Added `{name}` to the synergy block list. It is blocked whenever synergy is off (currently {state}).")
        else:
            if name in blocked:
                blocked.remove(name)
                await basics.save_db(shared_info.serversList)
                await message.channel.send(f"Removed `{name}` from the synergy block list.")
            else:
                await message.channel.send(f"`{name}` is not on the custom block list (built-in synergy commands can't be removed).")
        return

    commandInfo = {"message": message.content, "guild": message.guild}

    embed = discord.Embed(title="Analytics:")
    embed = commandFuncs[command](embed, message.author, commandInfo)
    embed.set_footer(text=shared_info.embedFooter(message.guild))
    await message.channel.send(embed=embed)
