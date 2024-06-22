import discord
from discord.ext import commands
from discord.ext import tasks
from datetime import datetime, timedelta, timezone
import pytz

class genshin(commands.Cog):
    """Genshin Utility Cog"""
    def __init__(self, client):

        self.client        = client
        self.reminder_pool = []
        self.finished_pool = []
        self.cache_seconds = 0
        self.cache_mins    = 0
        self.cache_hours   = 0

        ###########################
        ### MODULE CONFIG START ###
        ###########################

        ## Timezone Config
        # Basepoint for calculating UTC Time Offset, if offsets are malfunctioning you may need to tune the hour & minute in this calculation.
        self.server_reset_time = datetime(year=2024, month=6 , day=4 , hour=4, minute=0, tzinfo=pytz.utc)

        ## Timezone Offsets
        # Adjust these values to align Local Time to UTC Time.
        self.reset_hour_utc = 9    # Offset in hours
        self.reset_minute_utc = 0  # Offset in minutes

        ## Channel Config
        self.announcement_channel_id = 1130016915293753354  # Channel ID for announcements
        self.announce_reset_loop = True # Announce in "announcement_channel_id" when the server resets.

        ## Default Reminder Pool
        # This will retain users to remind past unexpected reloads.
        # MULTIPLE USERS: [175182469656477696, 485898213422006313]
        # SINGLE USER:    [175182469656477696]
        # NO USERS:       []
        self.default_pool = []

        ## Status Config
        self.reset_loop_status = True   # Adds the reset time in status.

        ## Locale Variables, These are purely cosmetic for lets say if you wanted to use this module to time Honkai StarRail instead of Genshin Impact.
        self.GameName = "Genshin"
        self.ServerRegion = "NA"

        # Console output for developers.
        self.debug = False

        ########################
        ### MODULE CONFIG END ##
        ########################


    def func_reset_time_utc(self, current_time_utc):
        return datetime(
            current_time_utc.year,
            current_time_utc.month,
            current_time_utc.day,
            self.reset_hour_utc,
            self.reset_minute_utc,
            tzinfo=timezone.utc
        )


    async def set_status(self):
        current_time_utc = datetime.now(timezone.utc)
        reset_time_utc = self.func_reset_time_utc(current_time_utc)
        if current_time_utc.hour >= self.reset_hour_utc:
            reset_time_utc += timedelta(days=1)
        time_until_reset = reset_time_utc - current_time_utc
        await self.client.change_presence(status=discord.Status.dnd, activity=discord.Game(f"{self.ServerRegion} {time_until_reset.seconds // 3600}H {(time_until_reset.seconds // 60) % 60}M"))


    @tasks.loop(minutes=1)
    async def reset_loop(self):
        current_time_utc = datetime.now(timezone.utc)
        reset_time_utc = self.func_reset_time_utc(current_time_utc)
        if current_time_utc.hour >= self.reset_hour_utc:
            reset_time_utc += timedelta(days=1)
        time_until_reset = reset_time_utc - current_time_utc
        self.cache_hours = time_until_reset.seconds // 3600
        self.cache_mins = (time_until_reset.seconds // 60) % 60
        self.cache_seconds = time_until_reset.seconds % 60
        if self.reset_loop_status:
            await self.client.change_presence(status=discord.Status.dnd, activity=discord.Game(f"{self.ServerRegion} {self.cache_hours}H {self.cache_mins}M"))
        if current_time_utc.hour == self.reset_hour_utc and current_time_utc.minute == self.reset_minute_utc:
            self.finished_pool = []
            if self.announce_reset_loop:
                await self.client.get_channel(self.announcement_channel_id).send(f"{self.GameName} {self.ServerRegion} server has reset <t:{int((datetime.now(timezone.utc).timestamp()))}:R>.")
        if self.debug:print(f"Querying Reset time, Result: {self.cache_hours}H {self.cache_mins}M {self.cache_seconds}S")


    @tasks.loop(minutes=60)
    async def reminder_loop(self):
        try:
            if self.debug:print("Preparing to remind users to do their dailies.")
            if self.reminder_pool == []:
                if self.debug:print("There was none in the reminders pool, skipping.")
                return
            else:
                for user in self.reminder_pool:
                    if user in self.finished_pool:
                        if self.debug:print(f"{user} Already marked their dailies as done.")
                    else:
                        if self.debug:print(f"Reminding {user} to do dailies.")
                        dm_channel = await self.client.get_user(user).create_dm()
                        await dm_channel.send(f"Make sure to do your dailies today!\nYou have {self.cache_hours} Hours and {self.cache_mins} Mins to do them :)")
        except Exception as e:
            if self.debug:print(f'{type(e).__name__} - {e}')


    @commands.command()
    async def rtime(self, ctx):
        """Responds with the Reset timer"""
        current_time_utc = datetime.now(timezone.utc)
        reset_time_utc = self.func_reset_time_utc(current_time_utc)
        if current_time_utc.hour >= self.reset_hour_utc:
            reset_time_utc += timedelta(days=1)
        time_until_reset = reset_time_utc - current_time_utc
        reset_unix_timestamp = int((current_time_utc + time_until_reset).timestamp())
        await ctx.send(f"{self.GameName} {self.ServerRegion} will reset in {time_until_reset.seconds // 3600} hours {(time_until_reset.seconds // 60) % 60} minutes and {time_until_reset.seconds % 60} seconds.\nOr about <t:{reset_unix_timestamp}:R>")


    @commands.command(aliases=['remindme'])
    async def reminders(self, ctx):
        """Add Yourself to the reminders pool."""
        if ctx.author.id in self.reminder_pool:
            await ctx.reply("You are already a part of the reminders pool.")
        else:
            self.reminder_pool.append(ctx.author.id)
            if self.debug:print(f"{ctx.author.id} added themselves to the reminders pool.")
            await ctx.reply("You are now part of the reminders pool.")


    @commands.command(aliases=['stop', 'quiet'])
    async def shutup(self, ctx):
        """Remove yourself from the reminders pool."""
        if ctx.author.id in self.reminder_pool:
            self.reminder_pool.remove("ctx.author.id")
            if self.debug:print(f"{ctx.author.id} removed themselves from the reminders pool.")
            await ctx.reply("You are no longer part of the reminders pool.")
        else:
            await ctx.reply("You were never part of the reminders pool.")


    @commands.command(aliases=['finished', 'completed'])
    async def done(self, ctx):
        """Mark your dailies as complete."""
        if ctx.author.id in self.finished_pool:
            await ctx.reply("You have already finished your dailies.")
        else:
            self.finished_pool.append(ctx.author.id)
            await ctx.reply("Congratulations, You will be reminded again after the reset :)")


    @commands.Cog.listener()
    async def on_ready(self):
        await self.set_status()
        self.reset_loop.start()
        self.reminder_loop.start()


    def cog_unload(self):
        self.us_reset_loop.cancel()
        self.reset_loop_status_task.cancel()


async def setup(client):
    await client.add_cog(genshin(client))