import discord
from discord.ext import commands
import os

import asyncio



intents = discord.Intents.default()
bot = commands.Bot(command_prefix='!', intents=intents)

# Your specific voice channel ID
TARGET_VOICE_CHANNEL_ID = 1372629926162993217

@bot.event
async def on_ready():
    print(f'✅ Logged in as: {bot.user.name}')
    print(f'🆔 Bot ID: {bot.user.id}')
    
    # Join the voice channel immediately
    await join_target_channel()
    
    # Start background task
    bot.loop.create_task(maintain_voice_connection())

async def join_target_channel():
    """Join the target voice channel"""
    print(f'🔍 Looking for voice channel ID: {TARGET_VOICE_CHANNEL_ID}')
    
    # Check ALL servers the bot is in
    for guild in bot.guilds:
        print(f'\n📡 Checking server: {guild.name}')
        
        # Try to find the channel in this guild
        voice_channel = guild.get_channel(TARGET_VOICE_CHANNEL_ID)
        
        if voice_channel:
            print(f'✅ Found channel: #{voice_channel.name}')
            print(f'   Guild: {voice_channel.guild.name}')
            
            # Check if already connected in this guild
            if guild.voice_client:
                print(f'⚠️ Already connected in this guild')
                return True
            
            try:
                # Connect to voice
                print(f'🔗 Attempting to connect...')
                vc = await voice_channel.connect(timeout=10.0, reconnect=True)
                
                # Self-deafen and mute
                print(f'🔇 Setting mute/deafen...')
                await vc.guild.change_voice_state(
                    channel=vc.channel,
                    self_mute=True,
                    self_deaf=True
                )
                
                print(f'🎉 Successfully joined and set to silent mode!')
                print(f'   Channel: #{voice_channel.name}')
                print(f'   Server: {voice_channel.guild.name}')
                print(f'   Muted: {vc.self_mute}')
                print(f'   Deafened: {vc.self_deaf}')
                return True
                
            except Exception as e:
                print(f'❌ Error connecting: {type(e).__name__}: {e}')
                return False
    
    print(f'❌ Could not find voice channel!')
    return False

async def maintain_voice_connection():
    """Keep the voice connection alive"""
    await bot.wait_until_ready()
    
    # Track connection attempts
    connection_attempts = 0
    max_attempts = 5
    
    while not bot.is_closed():
        try:
            # Check if bot is connected
            connected = False
            for guild in bot.guilds:
                voice_client = guild.voice_client
                if voice_client and voice_client.is_connected():
                    connected = True
                    
                    # Ensure muted and deafened
                    if not voice_client.self_deaf or not voice_client.self_mute:
                        await voice_client.guild.change_voice_state(
                            channel=voice_client.channel,
                            self_mute=True,
                            self_deaf=True
                        )
                        print(f'🔧 Fixed mute/deafen state')
                    break
            
            # If not connected, try to reconnect
            if not connected:
                connection_attempts += 1
                print(f'🔌 Connection lost, attempting to reconnect ({connection_attempts}/{max_attempts})...')
                
                if connection_attempts <= max_attempts:
                    success = await join_target_channel()
                    if success:
                        connection_attempts = 0  # Reset on success
                else:
                    print(f'⚠️ Max reconnection attempts reached. Waiting...')
                    connection_attempts = 0
            
            # Wait before checking again
            await asyncio.sleep(10)
            
        except Exception as e:
            print(f'⚠️ Error in maintainer: {type(e).__name__}: {e}')
            await asyncio.sleep(30)

# Run the bot
if __name__ == "__main__":
        bot.run("MTQzNTAzNzgwODkwNDM3MjI2NA.GGyVpv.6TWfTlFPqcFdHVxdu-pwB5DnEdDRpDedq-WiZU")
