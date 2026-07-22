"""Timeline primitives and builders."""

from dataclasses import dataclass
from datetime import date

from .person import PersonProfile


@dataclass(slots=True)
class TimelineYear:
    """Annual timeline bucket with key computed attributes."""

    year: int
    start_date: date
    end_date: date
    inflation_index: float
    ages_at_year_end: dict[str, int]


def age_on_date(date_of_birth: date, as_of_date: date) -> int:
    """Return age in completed years at a specific date."""
    years = as_of_date.year - date_of_birth.year
    before_birthday = (as_of_date.month, as_of_date.day) < (
        date_of_birth.month,
        date_of_birth.day,
    )
    return years - int(before_birthday)


def build_yearly_timeline(
    people: list[PersonProfile],
    start_year: int,
    end_year: int,
    inflation_rate: float,
) -> list[TimelineYear]:
    """Create yearly timeline rows from start_year through end_year inclusive."""
    if end_year < start_year:
        raise ValueError("end_year must be greater than or equal to start_year")

    timeline: list[TimelineYear] = []
    inflation_index = 1.0

    for year in range(start_year, end_year + 1):
        year_end = date(year, 12, 31)
        ages = {
            person.name: age_on_date(person.date_of_birth, year_end)
            for person in people
        }

        timeline.append(
            TimelineYear(
                year=year,
                start_date=date(year, 1, 1),
                end_date=year_end,
                inflation_index=inflation_index,
                ages_at_year_end=ages,
            )
        )
        inflation_index *= 1 + inflation_rate

    return timeline
