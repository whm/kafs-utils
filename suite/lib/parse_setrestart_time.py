#
# AFS Server management toolkit: Restart time parser
# -*- coding: utf-8 -*-
#

__copyright__ = """
Copyright (C) 2014 Red Hat, Inc. All Rights Reserved.
Written by David Howells (dhowells@redhat.com)

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public Licence version 2 as
published by the Free Software Foundation.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public Licence for more details.

You should have received a copy of the GNU General Public Licence
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
"""

from exception import AFSArgumentError
import kafs

days = [ "sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday" ]

###############################################################################
#
# Parse the bos setrestart -time argument
#
###############################################################################
def parse_restart_time(switch, params):
    at = kafs.bozo_netKTime()

    time = params[0].strip().lower()
    if time == "":
        raise AFSArgumentError("Empty time string")
    if time == "never":
        at.mask = kafs.KTIME_NEVER
        return at
    if time == "now":
        at.mask = kafs.KTIME_NOW
        return at

    if time.startswith("every "):
        time = time[6:].lstrip()
    elif time.startswith("at "):
        time = time[2:].lstrip()

    if time == "":
        raise AFSArgumentError("Incomplete time string")
    if time[0].isalpha():
        ix = time.find(" ")
        if ix < 3:
            raise AFSArgumentError("Can't extract day name")
        day = time[:ix]
        time = time[ix + 1:].lstrip()
        for i in range(0, 7):
            if days[i].startswith(day):
                at.day = i
                at.mask |= kafs.KTIME_DAY
                break
        else:
            raise AFSArgumentError("Unrecognised day name")

    ix = time.find(" ")
    if ix == -1:
        # 24-hour clock
        clock_type = 24
    else:
        # 12-hour clock
        clock_type = 12
        ampm = time[ix + 1:].lstrip()
        if ampm == "am":
            at.hour = 0
        elif ampm == "pm":
            at.hour = 12
        else:
            raise AFSArgumentError("Expect 'am' or 'pm' in time")
        time = time[0:ix]

    ix = time.find(":")
    if ix == -1:
        raise AFSArgumentError("Expect colon in time")
    if ix <= 0 or ix > 2:
        raise AFSArgumentError("Expect one or two hour digits in time")
    if len(time) - (ix + 1) != 2:
        raise AFSArgumentError("Expect two minute digits in time")

    hour = int(time[0:ix])
    if (clock_type == 12 and (hour < 1 or hour > 12) or
        clock_type == 24 and (hour < 0 or hour > 23)):
        raise AFSArgumentError("Hour {:d} out of range in time".format(hour))
    if clock_type == 12 and hour == 12:
        hour = 0 # 12am maps to 00:00 and 12pm to 12:00
    at.hour += hour

    at.min = int(time[ix + 1:])
    if at.min > 59:
        raise AFSArgumentError("Minute out of range in time")

    at.mask |= kafs.KTIME_HOUR | kafs.KTIME_MIN
    return at
