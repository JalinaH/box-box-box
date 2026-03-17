#!/usr/bin/env python3
"""
Box Box Box - F1 Race Simulator
Full clean common model: one global formula, no regime branching.
"""

import json
import sys


COMPOUND_BASE = {
    'SOFT': -1.0,
    'MEDIUM': 0.0,
    'HARD': 0.8,
}

DEG_RATE = {
    'SOFT': 0.4,
    'MEDIUM': 0.2,
    'HARD': 0.102,
}

TEMP_A = 24.7
TEMP_B = 1092.0

TRACK_DEG_MULT = {
    'Bahrain': {'SOFT': 1.0, 'MEDIUM': 1.0, 'HARD': 1.0},
    'COTA': {'SOFT': 1.0, 'MEDIUM': 1.0, 'HARD': 1.0},
    'Monaco': {'SOFT': 1.0, 'MEDIUM': 1.0, 'HARD': 1.0},
    'Monza': {'SOFT': 1.002, 'MEDIUM': 1.002, 'HARD': 1.002},
    'Silverstone': {'SOFT': 1.0, 'MEDIUM': 1.0, 'HARD': 1.0},
    'Spa': {'SOFT': 0.95, 'MEDIUM': 0.95, 'HARD': 0.92},
    'Suzuka': {'SOFT': 0.99, 'MEDIUM': 1.02, 'HARD': 0.99},
}

TRACK_PIT_MULT = {
    'Bahrain': 1.0,
    'COTA': 1.0,
    'Monaco': 1.0,
    'Monza': 1.0,
    'Silverstone': 1.0,
    'Spa': 1.0,
    'Suzuka': 0.95,
}

CLIFF_AGE = {
    'SOFT': 10,
    'MEDIUM': 20,
    'HARD': 30,
}


def simulate_race(race_config, strategies):
    base = race_config['base_lap_time']
    pit_time = race_config['pit_lane_time']
    total_laps = race_config['total_laps']
    temp = race_config['track_temp']
    track = race_config['track']

    temp_factor = (temp + TEMP_A) / TEMP_B
    track_deg_mult = TRACK_DEG_MULT[track]
    track_pit_mult = TRACK_PIT_MULT[track]

    results = []

    for pos_key in [f'pos{i}' for i in range(1, 21)]:
        strategy = strategies[pos_key]
        driver_id = strategy['driver_id']
        pit_laps = {ps['lap']: ps['to_tire'] for ps in strategy['pit_stops']}

        current_tire = strategy['starting_tire']
        tire_age = 0
        total_time = 0.0

        for lap in range(1, total_laps + 1):
            if (lap - 1) in pit_laps:
                current_tire = pit_laps[lap - 1]
                tire_age = 0

            tire_age += 1
            effective_age = max(0, tire_age - CLIFF_AGE[current_tire])
            degradation = (
                base
                * temp_factor
                * DEG_RATE[current_tire]
                * effective_age
                * track_deg_mult[current_tire]
            )

            lap_time = base + COMPOUND_BASE[current_tire] + degradation
            total_time += lap_time

            if lap in pit_laps:
                total_time += pit_time * track_pit_mult

        results.append((total_time, driver_id))

    results.sort()
    return [driver_id for _, driver_id in results]


def main():
    test_case = json.load(sys.stdin)
    race_id = test_case['race_id']
    race_config = test_case['race_config']
    strategies = test_case['strategies']

    finishing_positions = simulate_race(race_config, strategies)

    output = {
        'race_id': race_id,
        'finishing_positions': finishing_positions,
    }
    print(json.dumps(output))


if __name__ == '__main__':
    main()
