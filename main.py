from keep_alive import keep_alive

keep_alive()

import discord
from discord.ext import commands
import requests
from bs4 import BeautifulSoup
import asyncio
import os

TOKEN = os.getenv("DISCORD_BOT_TOKEN")
CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID"))
ANNOUNCEMENT_CHANNEL_ID = os.getenv("DISCORD_ANNOUNCEMENT_CHANNEL_ID")
if ANNOUNCEMENT_CHANNEL_ID:
    ANNOUNCEMENT_CHANNEL_ID = int(ANNOUNCEMENT_CHANNEL_ID)
else:
    ANNOUNCEMENT_CHANNEL_ID = None

# Items to monitor for announcements
MONITORED_ITEMS = [
    "Ember Lily",
    "Bug Egg", 
    "Mythical Egg",
    "Beanstalk",
    "Master Sprinkler",
    "Lightning Rod",
    "Legendary Egg",
    "Advanced Sprinkler"
]

intents = discord.Intents.default()
bot = commands.Bot(command_prefix='!', intents=intents)

last_stock = ""

async def fetch_stock():
    url = "https://vulcanvalues.com/grow-a-garden/stock"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    print(f"Response status: {response.status_code}")
    print(f"Page title: {soup.title.text if soup.title else 'No title'}")

    stock_sections = {}
    current_header = None

    # Try multiple selectors to find the content
    # First try .py-2 container
    py2_elements = soup.select('.py-2 > *')
    print(f"Found {len(py2_elements)} elements in .py-2 containers")

    # If that doesn't work, try looking for h2 and ul elements directly
    if len(py2_elements) == 0 or not any(el.name == 'h2' for el in py2_elements):
        print("Trying alternative selectors...")
        all_h2 = soup.find_all('h2')
        all_ul = soup.find_all('ul')
        print(f"Found {len(all_h2)} h2 elements and {len(all_ul)} ul elements")

        # Look for h2 elements followed by ul elements
        for h2 in all_h2:
            header_text = h2.text.strip()
            stock_sections[header_text] = []
            print(f"Found header: {header_text}")

            # Find the next ul after this h2
            next_element = h2.find_next_sibling()
            while next_element:
                if next_element.name == 'ul':
                    items = [f"• {li.text.strip()}" for li in next_element.find_all('li')]
                    stock_sections[header_text].extend(items)
                    print(f"Added {len(items)} items to {header_text}")
                    break
                elif next_element.name == 'h2':
                    break
                next_element = next_element.find_next_sibling()
    else:
        # Use the original method
        for element in py2_elements:
            if element.name == 'h2':
                current_header = element.text.strip()
                stock_sections[current_header] = []
                print(f"Found header: {current_header}")
            elif element.name == 'ul' and current_header:
                items = [f"• {li.text.strip()}" for li in element.select('li')]
                stock_sections[current_header].extend(items)
                print(f"Added {len(items)} items to {current_header}")

    print(f"Total sections found: {len(stock_sections)}")

    # Format everything
    output = []
    for section, items in stock_sections.items():
        if items:  # Only add sections that have items
            output.append(f"__**{section}**__")  # Discord header (bold + underline)
            output.extend(items)
            output.append("")  # Space between sections

    result = "\n".join(output).strip()
    return result if result else "No stock data found on the website."

def check_monitored_items(stock_text):
    """Check if any monitored items are in stock and return them"""
    items_in_stock = []
    for item in MONITORED_ITEMS:
        if item in stock_text:
            items_in_stock.append(item)
    return items_in_stock


async def check_stock_loop():
    global last_stock
    await bot.wait_until_ready()
    channel = bot.get_channel(CHANNEL_ID)
    announcement_channel = bot.get_channel(ANNOUNCEMENT_CHANNEL_ID) if ANNOUNCEMENT_CHANNEL_ID else None

    while not bot.is_closed():
        try:
            print("Checking stock...")
            current_stock = await fetch_stock()
            print(f"Current stock length: {len(current_stock)} characters")
            print(f"Last stock length: {len(last_stock)} characters")

            # Check for monitored items
            items_in_stock = check_monitored_items(current_stock)
            if items_in_stock and announcement_channel:
                for item in items_in_stock:
                    await announcement_channel.send(f"🚨 **{item}** is now in stock! 🚨")
                    print(f"Announced: {item} is in stock")
            elif items_in_stock:
                print(f"Items in stock but no announcement channel configured: {items_in_stock}")

            if current_stock != last_stock:
                print("Stock changed! Sending message...")
                await channel.send(f"🌱 **New Stock (Grow a Garden)**\n\n{current_stock}")
                last_stock = current_stock
                print("Message sent successfully!")
            else:
                print("No stock changes detected.")
        except Exception as e:
            print(f"Error checking stock: {e}")
            import traceback
            traceback.print_exc()
        await asyncio.sleep(240)

@bot.tree.command(name="stock", description="Get the current stock from Grow a Garden")
async def stock_command(interaction: discord.Interaction):
    try:
        await interaction.response.defer()
        print("Stock command triggered - fetching fresh data...")
        current_stock = await fetch_stock()

        if current_stock and current_stock != "No stock data found on the website.":
            await interaction.followup.send(f"🌱 **Current Stock (Grow a Garden)**\n\n{current_stock}")
        else:
            await interaction.followup.send("❌ No stock data available at the moment. The website might be down or the structure has changed.")
    except Exception as e:
        print(f"Error in stock command: {e}")
        import traceback
        traceback.print_exc()
        await interaction.followup.send("❌ Error fetching stock data. Please try again later.")

@bot.tree.command(name="test_announcement", description="Test the announcement channel")
async def test_announcement(interaction: discord.Interaction):
    try:
        if not ANNOUNCEMENT_CHANNEL_ID:
            await interaction.response.send_message("❌ Announcement channel ID not configured. Please set DISCORD_ANNOUNCEMENT_CHANNEL_ID environment variable.", ephemeral=True)
            return

        announcement_channel = bot.get_channel(ANNOUNCEMENT_CHANNEL_ID)
        if not announcement_channel:
            await interaction.response.send_message(f"❌ Could not find announcement channel with ID: {ANNOUNCEMENT_CHANNEL_ID}", ephemeral=True)
            return

        await announcement_channel.send("🧪 **Test message** - Announcement channel is working! 🧪")
        await interaction.response.send_message(f"✅ Test message sent to announcement channel: {announcement_channel.name}", ephemeral=True)

    except Exception as e:
        print(f"Error in test_announcement command: {e}")
        await interaction.response.send_message(f"❌ Error sending test message: {str(e)}", ephemeral=True)

@bot.event
async def on_ready():
    global last_stock
    print(f"✅ Logged in as {bot.user.name}")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

    # Get initial stock and send it
    channel = bot.get_channel(CHANNEL_ID)
    try:
        initial_stock = await fetch_stock()
        if initial_stock:

            await channel.send(f"🌱 **Bot Started - Current Stock (Grow a Garden)**\n\n{initial_stock}")
            last_stock = initial_stock
            print("Initial stock sent!")
        else:
            print("No initial stock data found")
    except Exception as e:
        print(f"Error sending initial stock: {e}")

    # Start the stock checking loop after the bot is ready
    bot.loop.create_task(check_stock_loop())

# Run the bot
bot.run(TOKEN)
