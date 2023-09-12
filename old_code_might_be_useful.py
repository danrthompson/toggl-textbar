from typing import Optional
from datetime import date, datetime, timedelta

import pytz
import numpy as np


def print_ewa(
    ewa_per_day: list[int],
    ewa_index_from_end: Optional[int] = None,
    show_week_time: bool = False,
):
    if ewa_index_from_end:
        ewa = ewa_per_day[-1 * ewa_index_from_end]
        if show_week_time:
            ewa *= 7
        print(f"{ewa // 60}:{ewa % 60:02d}")
        return

    for ewa in ewa_per_day:
        if show_week_time:
            ewa *= 7
        print(f"{ewa // 60}:{ewa % 60:02d}")


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


# ewa: list[int] = get_ewa(project_type, span=7, 30)
