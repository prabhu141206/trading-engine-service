from datetime import datetime

from candle.candle_scheduler import CandleScheduler
from candle.candle_timeframe import CandleTimeframe


def test_next_five_minute_boundary():

    scheduler = CandleScheduler(
        timeframe=CandleTimeframe.FIVE_MINUTES,
        on_boundary=lambda interval_start: None,
    )

    current_time = datetime(
        2026,
        8,
        17,
        10,
        17,
        32,
    )

    boundary = scheduler.get_next_boundary(
        current_time
    )

    assert boundary == datetime(
        2026,
        8,
        17,
        10,
        20,
    )


def test_boundary_when_already_at_exact_boundary():

    scheduler = CandleScheduler(
        timeframe=CandleTimeframe.FIVE_MINUTES,
        on_boundary=lambda interval_start: None,
    )

    current_time = datetime(
        2026,
        8,
        17,
        10,
        20,
        0,
    )

    boundary = scheduler.get_next_boundary(
        current_time
    )

    assert boundary == datetime(
        2026,
        8,
        17,
        10,
        25,
    )


def test_boundary_crossing_hour():

    scheduler = CandleScheduler(
        timeframe=CandleTimeframe.FIVE_MINUTES,
        on_boundary=lambda interval_start: None,
    )

    current_time = datetime(
        2026,
        8,
        17,
        10,
        58,
        30,
    )

    boundary = scheduler.get_next_boundary(
        current_time
    )

    assert boundary == datetime(
        2026,
        8,
        17,
        11,
        0,
    )


def test_get_interval_start():

    scheduler = CandleScheduler(
        timeframe=CandleTimeframe.FIVE_MINUTES,
        on_boundary=lambda interval_start: None,
    )

    boundary = datetime(
        2026,
        8,
        17,
        10,
        20,
    )

    interval_start = scheduler.get_interval_start(
        boundary
    )

    assert interval_start == datetime(
        2026,
        8,
        17,
        10,
        15,
    )



def test_boundary_triggers_callback():

    received_intervals = []

    def callback(interval_start):
        received_intervals.append(interval_start)

    scheduler = CandleScheduler(
        timeframe=CandleTimeframe.FIVE_MINUTES,
        on_boundary=callback,
    )

    boundary = datetime(
        2026,
        8,
        17,
        10,
        20,
    )

    scheduler.trigger_boundary(boundary)

    assert received_intervals == [
        datetime(
            2026,
            8,
            17,
            10,
            15,
        )
    ]


def test_run_once_triggers_completed_interval():

    received_intervals = []

    def callback(interval_start):
        received_intervals.append(interval_start)

    scheduler = CandleScheduler(
        timeframe=CandleTimeframe.FIVE_MINUTES,
        on_boundary=callback,
    )

    scheduler.run_once(
        datetime(
            2026,
            8,
            17,
            10,
            17,
            30,
        )
    )

    assert received_intervals == [
        datetime(
            2026,
            8,
            17,
            10,
            15,
        )
    ]