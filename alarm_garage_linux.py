#!/usr/bin/python

import os
import traceback
from time import sleep
from datetime import date
from datetime import datetime
from influxdb import InfluxDBClient
from dateutil.parser import parse
from dateutil.tz import tzutc, tzlocal
from dateutil.relativedelta import *

# InfluxDB query sample
# SELECT value FROM "DOOR_SENSOR" WHERE "DOOR_NUM" = '3' AND "DOMAIN" = 'PROD' ORDER BY ASC LIMIT 60

# CONSTS - INFLUXDB
INFLUXDB_HOST = "127.0.0.1"
INFLUXDB_DB = "foobar"
MEASUREMENT = "DOOR_SENSOR"
TAG_KEY_SENSOR = "DOOR_NUM"
TAG_KEY_DOMAIN = "DOMAIN"
# the following should be used by the caller of methods defined here
TAG_VAL_DOMAIN_PROD = "PROD"
TAG_VAL_DOMAIN_TEST = "TEST"
TAG_VAL_DOMAIN_PROD = "PROD"

SENSOR_STATUS_CODE_CLOSE = 0
SENSOR_STATUS_CODE_OPEN = 1
# door number 0 used for testing
FRIDGE_DOOR_NUMBER = "1"
FREEZER_DOOR_NUMBER = "2"
GARAGE_DOOR_NUMBER = "3"

# "sleep" time starts at 7:30pm and ends at 6:45am
# therefore, awake time is 6:45am to 7:30pm
AWAKE_START_HOUR = 6
AWAKE_START_MINUTE = 45
AWAKE_END_HOUR = 19
AWAKE_END_MINUTE = 30

POLL_INTERVAL_SECONDS = 60

GARAGE_DOOR_ALARM_MP3_PATH = '/home/foobar/esp8266/alarm/garage_door_open.mp3'

def get_state_str(val):
    if val == SENSOR_STATUS_CODE_OPEN:
        return 'OPEN'
    return 'CLOSED'

def sound_alarm(val, within_sleep):
    if within_sleep and val == SENSOR_STATUS_CODE_OPEN:
        return True
    return False


def get_current_garage_door_state():
    query = 'SELECT value FROM "{}" WHERE "{}" = \'{}\' AND "{}" = \'{}\' ORDER BY DESC LIMIT {}'.format(
        MEASUREMENT, TAG_KEY_SENSOR, GARAGE_DOOR_NUMBER, TAG_KEY_DOMAIN, TAG_VAL_DOMAIN_PROD, 1)

    print query

    client = InfluxDBClient(host=INFLUXDB_HOST, port=8086, database=INFLUXDB_DB, verify_ssl=False)
    result = client.query(query)
    print "Errors: {}  \n".format(result.error)
    return result


def during_awake(ts_local):
    today = date.today()
    ts_today = datetime(year=today.year, month=today.month, day=today.day, tzinfo=tzlocal())

    #print 'ts_today: {} ; TZ today: {} \n'.format(ts_today, ts_today.tzinfo)
    
    ts_awake_start = ts_today + relativedelta(hour=AWAKE_START_HOUR, minute=AWAKE_START_MINUTE)
    ts_awake_end = ts_today + relativedelta(hour=AWAKE_END_HOUR, minute=AWAKE_END_MINUTE)
    
    print "Today: {} \nts_awake_start: {} \nts_sleep_end: {} \n".format(ts_today, ts_awake_start, ts_awake_end)

    if ts_local>=ts_awake_start and ts_local<=ts_awake_end:
        return True
        
    return False


def main():
    done = False
    while not done:
        print '\n********** Entering Loop **********\n'
        try:
            result = get_current_garage_door_state()
            if result.error is not None:
                print 'Crap. Got an error from the DB. WTF? \n'
                raise result.error

            points = list(result.get_points(measurement=MEASUREMENT))
            if len(points) <= 0:
                raise 'Did not get any data back from DB'
                
            p = points[0]
            
            ts_utc = parse(p['time'])
            ts_local = ts_utc.astimezone(tzlocal())
            within_sleep = not during_awake(ts_local)
            val = p['value']            
            state = get_state_str(val)
            ring_alarm = sound_alarm(val, within_sleep)
            
            print 'Time as Local: {} \nDoor State: {} \nDuring Sleep Hours: {} \nRing Alarm: {}'.format(
                ts_local, state, within_sleep, ring_alarm)
            
            if ring_alarm:
                #print 'Debug: playing sound file now'
                os.system('mpg321 {}'.format(GARAGE_DOOR_ALARM_MP3_PATH))
                #print 'Debug: done playing sound file'

        except:
            print '\nWell... that did not go well...\n'
            traceback.print_exc()

        print '********** Processed Data. Sleeping... **********\n'
        
        # fail-safe to drop out of the loop 
        #done = True
        
        sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__": 
    main()
