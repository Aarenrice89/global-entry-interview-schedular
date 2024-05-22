import logging
import sys
import time
from datetime import datetime, timedelta
from typing import Any

import requests
from twilio.rest import Client

logger = logging.getLogger(__name__)

# Idea and details located here. I just added SMS capability
# https://packetlife.net/blog/2019/aug/7/apis-real-life-snagging-global-entry-interview/

# API URL
APPOINTMENTS_URL = "https://ttp.cbp.dhs.gov/schedulerapi/slots?orderBy=soonest&limit=1&locationId={}&minimum=1"

# List of Global Entry locations
LOCATION_IDS = {"LAX": 5180}

# How often to check in seconds
TIME_WAIT = 3600

# Number of days in the future to look for appointments
DAYS_OUT = 120

# Twilio account details
TWILIO_ACCOUNT_SID = ""
TWILIO_AUTH_TOKEN = ""

# From number has to be purchased first in the Twilio console
# To number has to be verified if on a trial account
TEXT_FROM_NUMBER = "+"
TEXT_TO_NUMBER = "+"

# Dates
now = datetime.now()
future_date = now + timedelta(days=DAYS_OUT)


def send_text(
    to_number: str, from_number: str, message: str, sid: str, token: str
) -> str:
    client = Client(sid, token)

    message = client.messages.create(
        to=to_number,
        from_=from_number,
        body=message,
    )
    return message.sid


def check_appointments(airport_id: int) -> list[dict[str, Any]]:
    url = APPOINTMENTS_URL.format(airport_id)
    response = requests.get(url)
    response.raise_for_status()
    return response.json()


def appointments_in_timeframe(
    now: datetime, future_date: datetime, appointment_date: datetime
) -> bool:
    if now <= appointment_date <= future_date:
        return True
    return False


try:
    while True:
        for city, id in LOCATION_IDS.items():
            try:
                appointments = check_appointments(id)
            except Exception as e:
                logger.warning(
                    f"Could not retrieve appointments from API for city: '{city}'"
                )
                appointments = []
            if appointments:
                appointment_date = datetime.strptime(
                    appointments[0]["startTimestamp"], r"%Y-%m-%dT%H:%M"
                )
                if appointments_in_timeframe(now, future_date, appointment_date):
                    message = f"{city}: Found an appointment at {appointments[0]['startTimestamp']}!"
                    try:
                        sms_sid = send_text(
                            TEXT_TO_NUMBER,
                            TEXT_FROM_NUMBER,
                            message,
                            TWILIO_ACCOUNT_SID,
                            TWILIO_AUTH_TOKEN,
                        )
                        logger.info(f"Sent text successfully! {sms_sid}")
                    except Exception as e:
                        logger.warning(
                            f"Error while sending sms through Twilio: {str(e)}"
                        )
                else:
                    logger.info(
                        f"{city}: No appointments during the next {DAYS_OUT} days."
                    )
            else:
                logger.info(f"{city}: No appointments during the next {DAYS_OUT} days.")
            time.sleep(1)
        time.sleep(TIME_WAIT)
except KeyboardInterrupt:
    logger.warning("Keyboard interrupt, exiting.")
    sys.exit(0)
