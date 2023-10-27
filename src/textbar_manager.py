import json
import os
import math
from abc import ABC, abstractmethod
from datetime import datetime, date, timedelta
from pathlib import Path
from pprint import pprint
from typing import Any, Dict, List

import pytz
import requests


DEBUG = False
# DEBUG = True


class UtilityCalculator(ABC):
    @abstractmethod
    def calculate(self, data: Any) -> Dict[str, str]:
        pass


# 3. DatasourceUpdater with modifications
class DatasourceUpdater(ABC):
    def __init__(self, utility_calculators: List[UtilityCalculator]):
        self.utility_calculators = utility_calculators

    async def update_data(self) -> Dict[str, str]:
        data = self._fetch_data()
        utility_data: dict[str, str] = {}
        for calculator in self.utility_calculators:
            utility_values = calculator.calculate(data)
            utility_data |= utility_values
        return utility_data

    @abstractmethod
    def _fetch_data(self) -> Any:
        pass


# 1. TextbarManager with modifications
class TextbarManager:
    DEFAULT_FILEPATH = (
        "/Users/danthompson/Code/Tools/CLI/toggl_textbar/data/utility_data.json"
    )

    def __init__(self, filepath: str = DEFAULT_FILEPATH) -> None:
        self.filepath = Path(filepath)
        # Ensure the file exists and initialize if not.
        if not self.filepath.exists():
            self.filepath.parent.mkdir(parents=True, exist_ok=True)
            self.filepath.write_text(json.dumps({"live": "true"}), encoding="utf-8")

        contents = self.read_all_data()
        if not contents:
            self._write_to_disk({"live": "true"})

    def write_data(self, utility_name: str, data: str) -> None:
        self.bulk_write_data({utility_name: data})

    def bulk_write_data(self, data: Dict[str, str]) -> None:
        current_data = self.read_all_data()
        if not current_data:
            raise ValueError("No data found on disk.")

        current_data.update(data)
        self._write_to_disk(current_data)

    def read_data(self, utility_name: str, default_if_empty="") -> str:
        return self.read_all_data().get(utility_name, default_if_empty)

    def get_keys(self) -> List[str]:
        return list(self.read_all_data().keys())

    def read_all_data(self) -> Dict[str, str]:
        return json.loads(self.filepath.read_text())

    def remove_key(self, key: str) -> None:
        data = self.read_all_data()
        data.pop(key)
        self._write_to_disk(data)

    def _write_to_disk(self, data: Dict[str, str]) -> None:
        self.filepath.write_text(json.dumps(data))


# 2. TextbarUpdater with modifications
class TextbarUpdater:
    def __init__(self, datasources: List[DatasourceUpdater], manager: TextbarManager):
        self.datasources = datasources
        self.manager = manager

    async def update_all(self) -> None:
        all_data = {}
        for ds in self.datasources:
            data = await ds.update_data()
            all_data.update(data)
        self.manager.bulk_write_data(all_data)


class TogglBaseTimeCalculator(UtilityCalculator):
    @classmethod
    @abstractmethod
    def CRITERIA(cls) -> dict[str, Any]:
        ...

    @abstractmethod
    def fits_criteria(self, entry: dict[str, Any], criteria: Any) -> bool:
        ...

    def calculate(self, data: List[Dict[str, Any]]) -> Dict[str, str]:
        results = {utility: 0 for utility in self.CRITERIA().keys()}
        for entry in data:
            if entry["server_deleted_at"]:
                continue
            for utility, criteria in self.CRITERIA().items():
                if self.fits_criteria(entry, criteria):
                    if entry["stop"]:
                        results[utility] += entry["duration"]
                    else:
                        # If the entry is still running, use the current time
                        # to calculate the duration.
                        now = datetime.now(pytz.utc)
                        start_time = datetime.fromisoformat(entry["start"])
                        results[utility] += math.floor(
                            (now - start_time).total_seconds()
                        )

        result_strs: dict[str, str] = {}
        for utility, duration in results.items():
            hours, remainder = divmod(duration, 3600)
            minutes = remainder // 60
            result_strs[utility] = f"{hours}:{minutes:02}"

        return result_strs


class TogglProjectTimeCalculator(TogglBaseTimeCalculator):
    @classmethod
    def CRITERIA(cls) -> dict[str, dict[str, list[int]]]:
        return {
            "today_work": {
                "project_ids": [
                    187316243,
                    192815981,
                    195792173,
                    192815956,
                    189390036,
                    186181594,
                ],
            },
        }

    def fits_criteria(self, entry: dict[str, Any], criteria: Any) -> bool:
        if DEBUG:
            pprint(entry)
        try:
            project_id = int(entry["project_id"])
        except ValueError:
            project_id = None
        return project_id in criteria["project_ids"]


class TogglTagTimeCalculator(TogglBaseTimeCalculator):
    # TAGS_TO_ID = {
    #     "1_1_time_bad_distraction": "14637787",
    #     "1_2_time_med_distraction": "14637945",
    #     "1_3_time_break": "14680995",
    #     "1_4_time_tasks_or_chores": "14680996",
    #     "1_5_scheduling_timeblocking": "14700153",
    #     "1_6_time_work_planning": "14654293",
    #     "1_7_time_work": "14637788",
    # }
    @classmethod
    def CRITERIA(cls) -> dict[str, Any]:
        return {
            "today_work": {
                "start_days_ago": 0,
                "tags": ["1_7_time_work"],
            },
            "today_wps": {
                "start_days_ago": 0,
                "tags": [
                    "1_6_time_work_planning",
                    "1_5_scheduling_timeblocking",
                    "1_7_time_work",
                ],
            },
            "today_wpsc": {
                "start_days_ago": 0,
                "tags": [
                    "1_4_time_tasks_or_chores",
                    "1_6_time_work_planning",
                    "1_5_scheduling_timeblocking",
                    "1_7_time_work",
                ],
            },
            "today_distraction": {
                "start_days_ago": 0,
                "tags": ["1_2_time_med_distraction"],
            },
            "today_opt": {
                "start_days_ago": 0,
                "tags": ["1_1_time_bad_distraction"],
            },
            "today_total_distraction": {
                "start_days_ago": 0,
                "tags": [
                    "1_1_time_bad_distraction",
                    "1_2_time_med_distraction",
                ],
            },
            "today_breaks": {
                "start_days_ago": 0,
                "tags": [
                    "1_3_time_break",
                ],
            },
        }

    def fits_criteria(self, entry: dict[str, Any], criteria: dict[str, Any]) -> bool:
        return any(tag in entry["tags"] for tag in criteria["tags"])


class TogglUpdater(DatasourceUpdater):
    def _fetch_data(self) -> list[dict[str, Any]]:
        api_key = os.environ.get("TOGGL_API_KEY")
        if not api_key:
            raise ValueError("No Toggl API key found.")

        # Get the current date and time in the Eastern timezone
        eastern = pytz.timezone("US/Eastern")
        now = datetime.now(eastern)

        # Set the time to 12:00am
        start_time = now.replace(hour=0, minute=0, second=0, microsecond=0)

        # Convert the datetime object to a UNIX timestamp and then to an integer
        start_timestamp = int(start_time.timestamp())

        # Add the start parameter to the URL with the UNIX timestamp
        url = f"https://api.track.toggl.com/api/v9/me/time_entries?since={start_timestamp}"

        headers = {"Content-Type": "application/json"}
        auth: tuple[str, str] = (api_key, "api_token")
        response = requests.get(url, headers=headers, auth=auth)

        if not response.ok:
            raise ValueError(
                f"Error fetching data from Toggl. Status code: {response.status_code}. Response: {response.text}"
            )

        entries = response.json()
        valid_entries = []
        # validate entries
        for entry in entries:
            entry_start_time = datetime.fromisoformat(entry["start"])
            if entry_start_time < start_time:
                continue
            valid_entries.append(entry)
        if DEBUG:
            pprint(valid_entries)
        return valid_entries


async def update_all():
    print("starting update all")
    textbar_manager = TextbarManager()
    print(f"Current data: {textbar_manager.read_all_data()}")
    project_calculator = TogglProjectTimeCalculator()
    toggl_updater = TogglUpdater([project_calculator])
    textbar_updater = TextbarUpdater([toggl_updater], textbar_manager)
    await textbar_updater.update_all()
    print(f"Finished update. New data: {textbar_manager.read_all_data()}")


def print_value(key: str) -> str:
    textbar_manager = TextbarManager()
    return textbar_manager.read_data(key)
