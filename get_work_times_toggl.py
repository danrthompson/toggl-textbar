import json
import os
from urllib.parse import urlencode
from typing import Optional
from datetime import date, datetime, timedelta

import click
import requests
import numpy as np
import pytz

# AI Thinking learning 186181594
# investments 187316243
# special work projects 188326563
# work planning 188079427
# AI Project implementation 189390036

# work med prod 186193242
# thinking discussing 187041688
# tooling 186181587

# personal chores 188045536
# routines 187633817
# chores 186676441
# SP cleaning room 188537695
# exercise 186944059

# mindless 187986408

# Lucid 192004302
# Distracted 191810114

TOOLING_PROJECT_IDS = [186181587, 191810114, 192965458, 192945502]
WORK_PROJECT_IDS = [
    192815981,
    186181594,
    188079427,
    187316243,
    188326563,
    189390036,
    191499108,
    192004302,
    192815956,
]

CONFIG_DICT = {
    "tooling": {
        "project_ids": TOOLING_PROJECT_IDS,
        "today": "/Users/danthompson/Code/Tools/CLI/toggl textbar/data/opt_tooling_time_today.txt",
        "last_week": "/Users/danthompson/Code/Tools/CLI/toggl textbar/data/opt_tooling_time_last_week.txt",
        "ewa": "/Users/danthompson/Code/Tools/CLI/toggl textbar/data/opt_ewa.txt",
    },
    "work": {
        "project_ids": WORK_PROJECT_IDS,
        "today": "/Users/danthompson/Code/Tools/CLI/toggl textbar/data/total_work_time_today.txt",
        "last_week": "/Users/danthompson/Code/Tools/CLI/toggl textbar/data/total_work_time_last_week.txt",
        "ewa": "/Users/danthompson/Code/Tools/CLI/toggl textbar/data/work_ewa.txt",
    },
    "all": {
        "project_ids": TOOLING_PROJECT_IDS + WORK_PROJECT_IDS,
        "today": "/Users/danthompson/Code/Tools/CLI/toggl textbar/data/total_time_today.txt",
        "last_week": "/Users/danthompson/Code/Tools/CLI/toggl textbar/data/total_time_last_week.txt",
        "ewa": "/Users/danthompson/Code/Tools/CLI/toggl textbar/data/total_ewa.txt",
    },
}


PROJECT_TYPES = list(CONFIG_DICT.keys())
TIME_OPTIONS = ["today", "last_week"]

DATE_FORMAT = "%Y-%m-%d"


def get_time_entry_total_time(start_date, project_ids, end_date=None) -> int:
    if end_date is None:
        end_date = datetime.now().strftime(DATE_FORMAT)
    url = "https://api.track.toggl.com/reports/api/v3/workspace/397836/summary/time_entries"
    headers = {"Content-Type": "application/json"}
    auth = (os.environ.get("TOGGL_API_KEY"), "api_token")
    payload = {
        "start_date": start_date,
        "end_date": end_date,
        "project_ids": project_ids,
    }

    response = requests.post(url, headers=headers, auth=auth, json=payload)
    response_json = response.json()
    subgroups = (group["sub_groups"] for group in response_json["groups"])
    nested_subgroups = (subgroup for subgroup in subgroups for subgroup in subgroup)
    total_seconds: int = sum(subgroup["seconds"] for subgroup in nested_subgroups)
    return total_seconds // 60


def get_current_time_entry(project_ids):
    url = "https://api.track.toggl.com/api/v9/me/time_entries/current"
    headers = {"Content-Type": "application/json"}
    auth = (os.environ.get("TOGGL_API_KEY"), "api_token")

    response = requests.get(url, headers=headers, auth=auth)
    response_json = response.json()
    if (
        not response_json
        or "start" not in response_json
        or "project_id" not in response_json
        or response_json["project_id"] not in project_ids
    ):
        return None

    return response_json["start"]


def get_time_from_current_time_entry(project_ids):
    start_time_str = get_current_time_entry(project_ids)
    if not start_time_str:
        return 0

    start_time = datetime.strptime(start_time_str, "%Y-%m-%dT%H:%M:%S%z")

    return int((datetime.now(start_time.tzinfo) - start_time).total_seconds() / 60)


def write_total_time(file_name, total_mins):
    with open(file_name, "w") as f:
        f.write(str(total_mins))


def write_ewa(file_name: str, ewa_per_day: list[int]) -> None:
    with open(file_name, "w") as f:
        json.dump(ewa_per_day, f)


def get_project_ids_and_file_name(project_type, file_type):
    project = CONFIG_DICT[project_type]
    project_ids = project["project_ids"]
    file_name = project[file_type]
    return project_ids, file_name


def get_last_week_and_today_time(time: str, project_type: str):
    project_ids, file_name = get_project_ids_and_file_name(project_type, time)

    current_time = get_time_from_current_time_entry(project_ids)

    if time == "today":
        start_date = datetime.now().strftime(DATE_FORMAT)
    else:
        start_date = (datetime.now() - timedelta(days=6)).strftime(DATE_FORMAT)

    total_time_except_current: int = get_time_entry_total_time(start_date, project_ids)
    total_mins = current_time + total_time_except_current

    write_total_time(file_name, total_mins)
    return total_mins


def echo_time_formatted(total_time):
    click.echo(f"{total_time // 60}:{total_time % 60:02d}")


def print_ewa(
    ewa_per_day: list[int],
    ewa_index_from_end: Optional[int] = None,
    show_week_time: bool = False,
):
    if ewa_index_from_end:
        ewa = ewa_per_day[-1 * ewa_index_from_end]
        if show_week_time:
            ewa *= 7
        click.echo(f"{ewa // 60}:{ewa % 60:02d}")
        return

    for ewa in ewa_per_day:
        if show_week_time:
            ewa *= 7
        click.echo(f"{ewa // 60}:{ewa % 60:02d}")


def get_total_time_from_file(project_type, file_type):
    _, file_name = get_project_ids_and_file_name(project_type, file_type)
    with open(file_name, "r") as f:
        total_time = int(f.read())

    return total_time


def get_total_time_from_ewa(project_type, file_type) -> list[int]:
    _, file_name = get_project_ids_and_file_name(project_type, file_type)
    with open(file_name, "r") as f:
        ewa_per_day = json.load(f)

    return ewa_per_day


def numpy_ewma_vectorized_v2(data, window):
    data = np.array(data)
    alpha = 2 / (window + 1.0)
    alpha_rev = 1 - alpha
    n = data.shape[0]

    pows = alpha_rev ** (np.arange(n + 1))

    scale_arr = 1 / pows[:-1]
    offset = data[0] * pows[1:]
    pw0 = alpha * alpha_rev ** (n - 1)

    mult = data * pw0 * scale_arr
    cumsums = mult.cumsum()
    res = offset + cumsums * scale_arr[::-1]
    return res.round().astype(int).tolist()


def get_time_entries(
    end_date: Optional[datetime] = None, num_days: int = 30
) -> list[dict]:
    if not end_date:
        end_date = datetime.now() + timedelta(days=1)
    start_date_str = (end_date - timedelta(days=num_days)).strftime(DATE_FORMAT)

    end_date_str = end_date.strftime(DATE_FORMAT)
    endpoint = "https://api.track.toggl.com/api/v9/me/time_entries"
    headers = {"Content-Type": "application/json"}
    auth = (os.environ["TOGGL_API_KEY"], "api_token")
    payload = {
        "start_date": start_date_str,
        "end_date": end_date_str,
    }
    query_string = urlencode(payload)
    url = f"{endpoint}?{query_string}"

    response = requests.get(url, headers=headers, auth=auth, timeout=10)
    return response.json()


def get_mins_worked_per_day(
    entries: list[dict],
    project_ids: Optional[set[int]] = None,
    end_date: Optional[date] = None,
    num_days: int = 30,
) -> list[int]:
    if not end_date:
        end_date = date.today()
    start_date: date = end_date - timedelta(days=num_days)

    # filter out time entries that are not in the specified project ids
    if project_ids:
        entries = [entry for entry in entries if entry["pid"] in project_ids]

    # Define NYC timezone
    nyc_timezone = pytz.timezone("America/New_York")

    # Initialize dictionary to store total mins worked per day
    mins_per_day: dict[date, float] = {}

    # Loop through each time entry
    for entry in entries:
        # Convert start and end times to datetime objects in UTC timezone
        start_time: datetime = datetime.strptime(entry["start"], "%Y-%m-%dT%H:%M:%S%z")
        if entry["stop"] is not None:
            end_time: datetime = datetime.strptime(entry["stop"], "%Y-%m-%dT%H:%M:%S%z")
        else:
            end_time = datetime.now(pytz.utc)

        # Convert start and end times to NYC timezone
        start_time_nyc: datetime = start_time.astimezone(nyc_timezone)

        # Determine the day that the time entry took place on, in NYC timezone
        day_nyc: date = start_time_nyc.date()

        # If the day is within the specified range, add the duration to the total mins for that day
        if start_date <= day_nyc <= end_date:
            duration: float = (end_time - start_time).total_seconds() / 60
            if day_nyc not in mins_per_day:
                mins_per_day[day_nyc] = duration
            else:
                mins_per_day[day_nyc] += duration

    # Generate list of mins worked per day, with 0 mins for days with no time entries
    mins_worked_per_day: list[int] = []
    current_day: date = start_date
    while current_day <= end_date:
        if current_day in mins_per_day:
            mins_worked_per_day.append(int(mins_per_day[current_day]))
        else:
            mins_worked_per_day.append(0)
        current_day += timedelta(days=1)

    return mins_worked_per_day


def get_ewa(project_type: str, span: int, num_days: int) -> list[int]:
    project_ids, file_name = get_project_ids_and_file_name(project_type, "ewa")
    time_entries = get_time_entries(num_days=num_days)
    mins_worked_per_day = get_mins_worked_per_day(
        time_entries, project_ids=project_ids, num_days=num_days
    )
    ewa_per_day = numpy_ewma_vectorized_v2(mins_worked_per_day, window=span)
    write_ewa(file_name, ewa_per_day)
    return ewa_per_day


@click.group()
def cli():
    pass


@cli.command()
@click.option("--project-type", type=click.Choice(PROJECT_TYPES), default="work")
@click.option("--span", type=int, default=7)
@click.option("--num-days", type=int, default=30)
@click.option("--ewa-index-from-end", type=int, default=None)
@click.option(
    "--echo", is_flag=True, show_default=True, default=False, help="Print result"
)
def fetch_ewa(
    project_type: str, span: int, num_days: int, ewa_index_from_end, echo
) -> None:
    ewa: list[int] = get_ewa(project_type, span, num_days)
    if echo:
        click.echo(f"Project type: {project_type}, Num days: {num_days}, Span: {span}")
        print_ewa(ewa, ewa_index_from_end)


@cli.command()
@click.option("--project-type", type=click.Choice(PROJECT_TYPES), default="work")
@click.option("--ewa-index-from-end", type=int, default=None)
@click.option(
    "--show-week-time",
    is_flag=True,
    show_default=True,
    default=False,
    help="Show ewa time converted to per-week time",
)
def echo_ewa(project_type: str, ewa_index_from_end, show_week_time) -> None:
    ewa: list[int] = get_total_time_from_ewa(project_type, "ewa")
    print_ewa(ewa, ewa_index_from_end, show_week_time)


@cli.command()
@click.option("--time", type=click.Choice(TIME_OPTIONS), default=None)
@click.option("--project-type", type=click.Choice(PROJECT_TYPES), default=None)
@click.option(
    "--echo", is_flag=True, show_default=True, default=False, help="Print result"
)
def fetch_time(time, project_type, echo):
    times = [time] if time is not None else TIME_OPTIONS
    project_types = [project_type] if project_type is not None else PROJECT_TYPES
    for project_type in project_types:
        for time in times:
            total_time = get_last_week_and_today_time(time, project_type)
            if echo:
                click.echo(f"Project type: {project_type}, time: {time}")
                echo_time_formatted(total_time)


@cli.command()
@click.option("--time", type=click.Choice(TIME_OPTIONS), required=True)
@click.option("--project-type", type=click.Choice(PROJECT_TYPES), required=True)
@click.option(
    "--show-week-time",
    is_flag=True,
    show_default=True,
    default=False,
    help="Show ewa time converted to per-week time",
)
def get_echo_time(time, project_type, show_week_time):
    total_time = get_total_time_from_file(project_type, time)
    if show_week_time:
        total_time *= 7
    echo_time_formatted(total_time)


@cli.command()
@click.option("--time", type=click.Choice(TIME_OPTIONS), required=True)
@click.option("--project-type", type=click.Choice(PROJECT_TYPES), required=True)
def get_ratio(time, project_type):
    total_time = get_total_time_from_file("all", time)

    project_time = get_total_time_from_file(project_type, time)

    click.echo(f"{int(project_time * 100 / total_time)}")


if __name__ == "__main__":
    cli()
