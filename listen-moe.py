import asyncio
import json
from mpv import MPV
from pypresence import AioPresence
import websockets
import datetime
from zoneinfo import ZoneInfo
from os import getlogin, path

# Get CLIENT_ID from client-id.txt
if not path.exists("client-id.txt"):
    exit("Please make a client-id.txt file and put your discord client id in it.\n Instructions on how to do it: https://support-dev.discord.com/hc/en-us/articles/21204493235991-How-Can-Users-Discover-and-Play-My-Activity#h_01J8JK19X28EMARCNKRGW7J579")
with open("client-id.txt", "r") as f:
    DISCORD_CLIENT_ID = f.read()

# Constants
LISTEN_MOE_STREAM_URL = "https://listen.moe/stream"
WEBSOCKET_URL = "wss://listen.moe/gateway_v2"

async def send_ws(ws, data):
    """Send data through the WebSocket."""
    json_data = json.dumps(data)
    await ws.send(json_data)

async def _send_pings(ws, interval=45):
    """Send periodic pings to keep the WebSocket connection alive."""
    while True:
        await asyncio.sleep(interval)
        msg = {'op': 9}
        await send_ws(ws, msg)

async def fetch_song_info(rpc):
    """Fetch song info via WebSocket and update Discord RPC."""
    player = MPV()
    player.play(LISTEN_MOE_STREAM_URL)
    
    async with websockets.connect(WEBSOCKET_URL) as ws:
        last_song = None
        
        while True:
            data = json.loads(await ws.recv())
            
            if data['op'] == 0:  # Hello packet
                heartbeat = data['d']['heartbeat'] / 1000
                asyncio.create_task(_send_pings(ws, heartbeat))
            elif data['op'] == 1:  # Event packet
                song_data = data['d']
                song = song_data.get('song', {})
                title = song.get('title', "Unknown")
                artists = ", ".join(artist.get("name") for artist in song.get('artists', []))
                start = datetime.datetime.strptime(song_data["startTime"], '%Y-%m-%dT%H:%M:%S.%fZ')
                start = start.replace(tzinfo=ZoneInfo("UTC"))
                current_song = f"{title} by {artists}" if artists else title

                if current_song != last_song:
                    print(f"Now playing: {current_song}")
                    await rpc.update(
						state=f"Listening to {current_song}",
						large_image="listen-moe",
                        large_text="https://listen.moe/",
                        small_image="github",
                        small_text="github.com/Parsa-GP/listen-moe-rpc",
                        start=int(start.timestamp()),
					)
                    last_song = current_song

async def main():
    # Initialize Discord RPC
    rpc = AioPresence(DISCORD_CLIENT_ID)
    await rpc.connect()
    print("Discord Rich Presence connected.")

    try:
        await fetch_song_info(rpc)
    except KeyboardInterrupt:
        print("Stopping the music...")
    finally:
        await rpc.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"Have a good day, {getlogin()}-san!")
