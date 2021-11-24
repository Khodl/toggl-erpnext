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


def get_page(config, date_from, date_to, entries=[], page=1):
    toggl = Toggl()
    toggl.setAPIKey(config["TOGGL_TOKEN"])
    response = toggl.getDetailedReport({
        "workspace_id": config["TOGGL_WORKSPACE"],
        "since": date_from,
        "until": date_to,
        "page": page
    })

    for element in response["data"]:
        date = dateutil.parser.isoparse(element['start'])
        durationInHours = element['dur'] / (1000 * 3600)
        if element['project'] == None or element['client'] == None:
            print("Entry without project or client:", element)
            sys.exit()
        entries.append(
            OperateEntry(date, durationInHours, element['client'], element['project'], element['description'])
        )

    if response['total_count'] > len(entries):
        return get_page(config, date_from, date_to, entries, page+1)

    return entries


def import_entries(config):
    date_from, date_to = get_dates()
    return get_page(config, date_from, date_to)


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

