#!/usr/bin/env python3
"""
Box Box Box - F1 Race Simulator
Full clean common model: one global formula, no regime branching.
"""

import json
import os
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

DEG_RATE_QUAD = {
    'SOFT': 0.0,
    'MEDIUM': 0.0,
    'HARD': 0.0,
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

TEMP_COMPOUND_MULT = {
    'SOFT': 1.0,
    'MEDIUM': 1.0,
    'HARD': 1.0,
}

FRESH_TIRE_WARMUP = {
    'SOFT': 0.0,
    'MEDIUM': 0.0,
    'HARD': 0.0,
}

TRACK_COMPOUND_BASE_ADD = {
    'Bahrain': {'SOFT': 0.0, 'MEDIUM': 0.0, 'HARD': 0.0},
    'COTA': {'SOFT': 0.0, 'MEDIUM': 0.0, 'HARD': 0.0},
    'Monaco': {'SOFT': 0.0, 'MEDIUM': 0.0, 'HARD': 0.0},
    'Monza': {'SOFT': 0.0, 'MEDIUM': 0.0, 'HARD': 0.0},
    'Silverstone': {'SOFT': 0.0, 'MEDIUM': 0.0, 'HARD': 0.0},
    'Spa': {'SOFT': 0.0, 'MEDIUM': 0.0, 'HARD': 0.0},
    'Suzuka': {'SOFT': 0.0, 'MEDIUM': 0.0, 'HARD': 0.0},
}

TRACK_CLIFF_ADD = {
    'Bahrain': {'SOFT': 0, 'MEDIUM': 0, 'HARD': 0},
    'COTA': {'SOFT': 0, 'MEDIUM': 0, 'HARD': 0},
    'Monaco': {'SOFT': 0, 'MEDIUM': 0, 'HARD': 0},
    'Monza': {'SOFT': 0, 'MEDIUM': 0, 'HARD': 0},
    'Silverstone': {'SOFT': 0, 'MEDIUM': 0, 'HARD': 0},
    'Spa': {'SOFT': 0, 'MEDIUM': 0, 'HARD': 0},
    'Suzuka': {'SOFT': 0, 'MEDIUM': 0, 'HARD': 0},
}


def copy_map(data):
    return json.loads(json.dumps(data))


def default_coefficients():
    return {
        'compound_base': COMPOUND_BASE,
        'deg_rate': DEG_RATE,
        'deg_rate_quad': DEG_RATE_QUAD,
        'temp_a': TEMP_A,
        'temp_b': TEMP_B,
        'temp_compound_mult': TEMP_COMPOUND_MULT,
        'fresh_tire_warmup': FRESH_TIRE_WARMUP,
        'track_compound_base_add': TRACK_COMPOUND_BASE_ADD,
        'track_cliff_add': TRACK_CLIFF_ADD,
        'track_deg_mult': TRACK_DEG_MULT,
        'track_pit_mult': TRACK_PIT_MULT,
        'cliff_age': CLIFF_AGE,
    }


def load_frozen_coefficients():
    coeffs = default_coefficients()
    script_dir = os.path.dirname(os.path.abspath(__file__))
    frozen_path = os.path.join(script_dir, 'frozen_coefficients.json')

    try:
        with open(frozen_path, 'r', encoding='utf-8') as f:
            payload = json.load(f)

        required_keys = {
            'compound_base',
            'deg_rate',
            'temp_a',
            'temp_b',
            'track_deg_mult',
            'track_pit_mult',
            'cliff_age',
        }

        if not required_keys.issubset(payload.keys()):
            return coeffs

        # Keep simulator resilient to malformed files: only accept complete structures.
        for compound in ('SOFT', 'MEDIUM', 'HARD'):
            if compound not in payload['compound_base']:
                return coeffs
            if compound not in payload['deg_rate']:
                return coeffs
            if compound not in payload['cliff_age']:
                return coeffs

        # Backward-compatible fill for newly introduced optional keys.
        if 'deg_rate_quad' not in payload:
            payload['deg_rate_quad'] = copy_map(DEG_RATE_QUAD)
        if 'temp_compound_mult' not in payload:
            payload['temp_compound_mult'] = copy_map(TEMP_COMPOUND_MULT)
        if 'fresh_tire_warmup' not in payload:
            payload['fresh_tire_warmup'] = copy_map(FRESH_TIRE_WARMUP)
        if 'track_compound_base_add' not in payload:
            payload['track_compound_base_add'] = copy_map(TRACK_COMPOUND_BASE_ADD)
        if 'track_cliff_add' not in payload:
            payload['track_cliff_add'] = copy_map(TRACK_CLIFF_ADD)

        for compound in ('SOFT', 'MEDIUM', 'HARD'):
            if compound not in payload['deg_rate_quad']:
                payload['deg_rate_quad'][compound] = DEG_RATE_QUAD[compound]
            if compound not in payload['temp_compound_mult']:
                payload['temp_compound_mult'][compound] = TEMP_COMPOUND_MULT[compound]
            if compound not in payload['fresh_tire_warmup']:
                payload['fresh_tire_warmup'][compound] = FRESH_TIRE_WARMUP[compound]

        for track in TRACK_DEG_MULT:
            if track not in payload['track_deg_mult']:
                return coeffs
            if track not in payload['track_pit_mult']:
                return coeffs
            if track not in payload['track_compound_base_add']:
                payload['track_compound_base_add'][track] = copy_map(TRACK_COMPOUND_BASE_ADD[track])
            if track not in payload['track_cliff_add']:
                payload['track_cliff_add'][track] = copy_map(TRACK_CLIFF_ADD[track])
            for compound in ('SOFT', 'MEDIUM', 'HARD'):
                if compound not in payload['track_deg_mult'][track]:
                    return coeffs
                if compound not in payload['track_compound_base_add'][track]:
                    payload['track_compound_base_add'][track][compound] = TRACK_COMPOUND_BASE_ADD[track][compound]
                if compound not in payload['track_cliff_add'][track]:
                    payload['track_cliff_add'][track][compound] = TRACK_CLIFF_ADD[track][compound]

        return payload
    except (FileNotFoundError, json.JSONDecodeError, OSError, TypeError):
        return coeffs


COEFFICIENTS = load_frozen_coefficients()


def simulate_race(race_config, strategies):
    base = race_config['base_lap_time']
    pit_time = race_config['pit_lane_time']
    total_laps = race_config['total_laps']
    temp = race_config['track_temp']
    track = race_config['track']

    temp_factor = (temp + COEFFICIENTS['temp_a']) / COEFFICIENTS['temp_b']
    track_deg_mult = COEFFICIENTS['track_deg_mult'][track]
    track_pit_mult = COEFFICIENTS['track_pit_mult'][track]
    track_base_add = COEFFICIENTS['track_compound_base_add'][track]
    track_cliff_add = COEFFICIENTS['track_cliff_add'][track]

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
            cliff_age = COEFFICIENTS['cliff_age'][current_tire] + track_cliff_add[current_tire]
            effective_age = max(0, tire_age - cliff_age)
            wear_linear = COEFFICIENTS['deg_rate'][current_tire] * effective_age
            wear_quad = COEFFICIENTS['deg_rate_quad'][current_tire] * effective_age * effective_age
            degradation = (
                base
                * temp_factor
                * COEFFICIENTS['temp_compound_mult'][current_tire]
                * (wear_linear + wear_quad)
                * track_deg_mult[current_tire]
            )

            lap_time = (
                base
                + COEFFICIENTS['compound_base'][current_tire]
                + track_base_add[current_tire]
                + degradation
            )
            if tire_age == 1:
                lap_time += COEFFICIENTS['fresh_tire_warmup'][current_tire]
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
