#!/usr/bin/python3
# -*- coding:utf-8 -*-
# Project: http://cloudedbats.org, https://github.com/cloudedbats
# Copyright (c) 2020-present Arnold Andreasson
# License: MIT License (see LICENSE.txt or http://opensource.org/licenses/mit).

import asyncio
import datetime
import wurb_rec

class WurbScheduler(object):
    """ """

    def __init__(self, wurb_manager):
        """ """
        self.wurb_manager = wurb_manager
        self.wurb_settings = wurb_manager.wurb_settings
        self.wurb_logging = wurb_manager.wurb_logging
        self.main_loop_task = None
        self.solartime = wurb_rec.SolarTime()
        self.solartime_lookup_dict = {}

    async def startup(self):
        """ """
        self.main_loop_task = asyncio.create_task(self.main_loop())

    async def shutdown(self):
        """ """
        if self.main_loop_task:
            self.main_loop_task.cancel()

    async def main_loop(self):
        """ """
        try:
            while True:
                try:
                    await asyncio.sleep(10)
                    rec_mode = self.wurb_settings.get_setting("rec_mode")
                    if rec_mode == "rec-mode-on":
                        await self.wurb_manager.start_rec()
                    if rec_mode == "rec-mode-off":
                        await self.wurb_manager.stop_rec()
                    if rec_mode == "rec-mode-scheduler":
                        await self.check_scheduler()
                except asyncio.CancelledError:
                    # print("DEBUG: ", "Scheduler main loop cancelled.")
                    break
        except Exception as e:
            # print("EXCEPTION: Scheduler main loop: ", e)
            # Logging error.
            message = "Scheduler main loop: " + str(e)
            self.wurb_manager.wurb_logging.error(message, short_message=message)
        finally:
            # print("DEBUG: Scheduler main loop terminated.")
            pass

    async def check_scheduler(self):
        """ """
        location_dict = self.wurb_settings.get_location_dict()
        latitude = float(location_dict.get("latitude_dd", "0.0"))
        longitude = float(location_dict.get("longitude_dd", "0.0"))
        if (latitude == 0.0) or (longitude == 0.0):
            await self.wurb_manager.stop_rec()
            return

        date_local = datetime.datetime.now().date()

        solartime_dict = self.solartime.sun_utc(date_local, latitude, longitude)
        sunset_utc = solartime_dict["sunset"]
        sunrise_utc = solartime_dict["sunrise"]
        sunset_local = solartime_dict["sunset"].astimezone()
        sunrise_local = solartime_dict["sunrise"].astimezone()

        print("")
        print("Sunset: ", sunset_local)
        print("Sunrise: ", sunrise_local)

        now_local = datetime.datetime.now().astimezone()
        start_local = sunset_local - datetime.timedelta(minutes=15)
        stop_local = sunrise_local + datetime.timedelta(minutes=15)

        print("Time now: ", now_local)
        print("Start time: ", start_local)
        print("Stop time: ", stop_local)
        print("")

        if start_local == stop_local:
            # Always off.
            await self.wurb_manager.stop_rec()
        if start_local < stop_local:
            # Same day.
            if (start_local < now_local) and (now_local < stop_local):
                await self.wurb_manager.start_rec()
            else:
                await self.wurb_manager.stop_rec()
        else:
            # Different days.
            start_local_new = start_local
            stop_local_new = stop_local
            # Prepare.
            if now_local < stop_local:
                start_local_new = start_local - datetime.timedelta(days=1)
            if now_local > stop_local:
                stop_local_new = stop_local + datetime.timedelta(days=1)
            # Check.
            if (start_local_new < now_local) and (now_local < stop_local_new):
                await self.wurb_manager.start_rec()
            else:
                await self.wurb_manager.stop_rec()
