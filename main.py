#!/usr/bin/python
import sys
import dateutil.parser
from datetime import datetime
from operate import OperateClient, OperateEntry
from dotenv import dotenv_values
from toggl.TogglPy import Toggl

# Loading the .env file
config = dotenv_values(".env")


def get_date(date_str):
    date = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
    return date.isoformat()+'+00:00'


def get_dates():
    return get_date(sys.argv[1] + " 00:00:00"), get_date(sys.argv[2] + " 23:59:59")


def import_entries(config):
    date_from, date_to = get_dates()
    toggl = Toggl()
    toggl.setAPIKey(config["TOGGL_TOKEN"])
    response = toggl.getDetailedReport({
        "workspace_id": config["TOGGL_WORKSPACE"],
        "since": date_from,
        "until": date_to
    })

    if response['total_count'] > response['per_page']:
        raise Exception("Please select a smaller date interval, as pagination is not supported")

    entries = []
    for element in response["data"]:
        date = dateutil.parser.isoparse(element['start'])
        durationInHours = element['dur'] / (1000*3600)
        entries.append(
            OperateEntry(date, durationInHours, element['client'], element['project'], element['description'])
        )
    return entries


def start_import():
    print("Let's go!")

    # Import from Toggl
    entries = import_entries(config)

    # Export to Operate
    client = OperateClient(config["OPERATE_DOMAIN"], config["OPERATE_EMAIL"], config["OPERATE_PASS"])
    for entry in entries:
        client.add_entry(entry)
    client.submit()


if __name__ == '__main__':
    start_import()

