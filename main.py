import discord

TOKEN = "MTQzNTAzNzgwODkwNDM3MjI2NA.GGyVpv.6TWfTlFPqcFdHVxdu-pwB5DnEdDRpDedq-WiZU"
VOICE_CHANNEL_ID = 1372629926162993217

class Bot(discord.Client):
    async def on_ready(self):
        print(f"{self.user} connected")
        channel = self.get_channel(VOICE_CHANNEL_ID)
        if channel:
            vc = await channel.connect()
            await vc.guild.change_voice_state(channel=vc.channel, self_mute=True, self_deaf=True)

intents = discord.Intents.all()
bot = Bot(intents=intents)
bot.run(TOKEN)
