#!/usr/bin/env python3
"""
Box Box Box - F1 Race Simulator
Uses cliff-based degradation with temp/100 scaling.
"""

import json
import sys


def simulate_race(race_config, strategies):
    base = race_config['base_lap_time']
    pit_time = race_config['pit_lane_time']
    total_laps = race_config['total_laps']
    temp = race_config['track_temp']
    
    # Temperature scales degradation
    temp_factor = temp / 100.0
    
    compound_base = {'SOFT': -1.52, 'MEDIUM': 0.0, 'HARD': 1.30}
    deg_rate = {'SOFT': 0.315, 'MEDIUM': 0.0495, 'HARD': 0.0}
    cliff = {'SOFT': 5, 'MEDIUM': 4, 'HARD': 2}
    
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
            effective_age = max(0, tire_age - cliff[current_tire])
            degradation = deg_rate[current_tire] * effective_age * temp_factor
            
            lap_time = base + compound_base[current_tire] + degradation
            total_time += lap_time
            
            if lap in pit_laps:
                total_time += pit_time
        
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
        'finishing_positions': finishing_positions
    }
    print(json.dumps(output))


if __name__ == '__main__':
    main()
