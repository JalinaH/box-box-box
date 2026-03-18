#!/usr/bin/env python3
"""
Train race simulator coefficients from historical races and freeze them to JSON.

This script optimizes the existing fast simulator formula by tuning coefficients to
maximize validation quality on historical data using exact, pairwise, or hybrid
rank-aware objectives.
The resulting coefficients are saved to solution/frozen_coefficients.json.
"""

import argparse
import copy
import json
import random
from pathlib import Path

TRACKS = ['Bahrain', 'COTA', 'Monaco', 'Monza', 'Silverstone', 'Spa', 'Suzuka']
COMPOUNDS = ['SOFT', 'MEDIUM', 'HARD']


def default_coefficients():
    return {
        'compound_base': {
            'SOFT': -1.0,
            'MEDIUM': 0.0,
            'HARD': 0.8,
        },
        'deg_rate': {
            'SOFT': 0.4,
            'MEDIUM': 0.2,
            'HARD': 0.102,
        },
        'deg_rate_quad': {
            'SOFT': 0.0,
            'MEDIUM': 0.0,
            'HARD': 0.0,
        },
        'temp_a': 24.7,
        'temp_b': 1092.0,
        'temp_compound_mult': {
            'SOFT': 1.0,
            'MEDIUM': 1.0,
            'HARD': 1.0,
        },
        'fresh_tire_warmup': {
            'SOFT': 0.0,
            'MEDIUM': 0.0,
            'HARD': 0.0,
        },
        'track_deg_mult': {
            'Bahrain': {'SOFT': 1.0, 'MEDIUM': 1.0, 'HARD': 1.0},
            'COTA': {'SOFT': 1.0, 'MEDIUM': 1.0, 'HARD': 1.0},
            'Monaco': {'SOFT': 1.0, 'MEDIUM': 1.0, 'HARD': 1.0},
            'Monza': {'SOFT': 1.002, 'MEDIUM': 1.002, 'HARD': 1.002},
            'Silverstone': {'SOFT': 1.0, 'MEDIUM': 1.0, 'HARD': 1.0},
            'Spa': {'SOFT': 0.95, 'MEDIUM': 0.95, 'HARD': 0.92},
            'Suzuka': {'SOFT': 0.99, 'MEDIUM': 1.02, 'HARD': 0.99},
        },
        'track_pit_mult': {
            'Bahrain': 1.0,
            'COTA': 1.0,
            'Monaco': 1.0,
            'Monza': 1.0,
            'Silverstone': 1.0,
            'Spa': 1.0,
            'Suzuka': 0.95,
        },
        'cliff_age': {
            'SOFT': 10,
            'MEDIUM': 20,
            'HARD': 30,
        },
    }


def list_historical_files(repo_root):
    hist_dir = repo_root / 'data' / 'historical_races'
    return sorted(hist_dir.glob('races_*.json'))


def load_historical_races(repo_root, max_files=None, max_races=None):
    files = list_historical_files(repo_root)
    if max_files is not None:
        files = files[:max_files]

    races = []
    for fp in files:
        with open(fp, 'r', encoding='utf-8') as f:
            block = json.load(f)
        races.extend(block)
        if max_races is not None and len(races) >= max_races:
            races = races[:max_races]
            break

    return races


def predict_positions(race_config, strategies, coeffs):
    base = race_config['base_lap_time']
    pit_time = race_config['pit_lane_time']
    total_laps = race_config['total_laps']
    temp = race_config['track_temp']
    track = race_config['track']

    temp_factor = (temp + coeffs['temp_a']) / coeffs['temp_b']
    track_deg_mult = coeffs['track_deg_mult'][track]
    track_pit_mult = coeffs['track_pit_mult'][track]

    results = []

    for idx in range(1, 21):
        strategy = strategies[f'pos{idx}']
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
            effective_age = max(0, tire_age - int(round(coeffs['cliff_age'][current_tire])))
            wear_linear = coeffs['deg_rate'][current_tire] * effective_age
            wear_quad = coeffs['deg_rate_quad'][current_tire] * effective_age * effective_age
            degradation = (
                base
                * temp_factor
                * coeffs['temp_compound_mult'][current_tire]
                * (wear_linear + wear_quad)
                * track_deg_mult[current_tire]
            )

            lap_time = base + coeffs['compound_base'][current_tire] + degradation
            if tire_age == 1:
                lap_time += coeffs['fresh_tire_warmup'][current_tire]
            total_time += lap_time

            if lap in pit_laps:
                total_time += pit_time * track_pit_mult

        results.append((total_time, driver_id))

    results.sort()
    return [driver_id for _, driver_id in results]


def score_exact(races, coeffs):
    correct = 0
    for race in races:
        pred = predict_positions(race['race_config'], race['strategies'], coeffs)
        if pred == race['finishing_positions']:
            correct += 1
    return correct


def score_topk(races, coeffs, k=5):
    hits = 0
    total = 0
    for race in races:
        pred = predict_positions(race['race_config'], race['strategies'], coeffs)
        exp = race['finishing_positions']
        for i in range(k):
            if pred[i] == exp[i]:
                hits += 1
            total += 1
    return hits / max(1, total)


def score_pairwise(races, coeffs):
    correct = 0
    total = 0

    for race in races:
        pred = predict_positions(race['race_config'], race['strategies'], coeffs)
        exp = race['finishing_positions']

        pred_rank = {driver_id: idx for idx, driver_id in enumerate(pred)}
        exp_rank = {driver_id: idx for idx, driver_id in enumerate(exp)}

        for i in range(len(exp)):
            di = exp[i]
            for j in range(i + 1, len(exp)):
                dj = exp[j]
                total += 1
                if pred_rank[di] < pred_rank[dj]:
                    correct += 1

    return correct / max(1, total)


def evaluate_metrics(races, coeffs):
    exact = score_exact(races, coeffs)
    top5 = score_topk(races, coeffs, k=5)
    pairwise = score_pairwise(races, coeffs)
    return {
        'exact': exact,
        'top5': top5,
        'pairwise': pairwise,
    }


def objective_value(metrics, total_races, objective):
    exact_rate = metrics['exact'] / max(1, total_races)

    if objective == 'exact':
        return (metrics['exact'], metrics['top5'], metrics['pairwise'])

    if objective == 'pairwise':
        return (metrics['pairwise'], metrics['top5'], metrics['exact'])

    # Hybrid balances full-order hits with robust ranking quality.
    hybrid = (2.0 * exact_rate) + (1.25 * metrics['pairwise']) + (0.5 * metrics['top5'])
    return (hybrid, metrics['exact'], metrics['pairwise'], metrics['top5'])


def mutate(coeffs, rng):
    out = copy.deepcopy(coeffs)

    if rng.random() < 0.65:
        c = rng.choice(COMPOUNDS)
        out['compound_base'][c] += rng.uniform(-0.12, 0.12)

    if rng.random() < 0.75:
        c = rng.choice(COMPOUNDS)
        out['deg_rate'][c] += rng.uniform(-0.02, 0.02)

    if rng.random() < 0.75:
        c = rng.choice(COMPOUNDS)
        out['deg_rate_quad'][c] += rng.uniform(-0.0015, 0.0015)

    if rng.random() < 0.45:
        c = rng.choice(COMPOUNDS)
        out['cliff_age'][c] += rng.randint(-2, 2)

    if rng.random() < 0.35:
        out['temp_a'] += rng.uniform(-2.5, 2.5)

    if rng.random() < 0.35:
        out['temp_b'] += rng.uniform(-30.0, 30.0)

    if rng.random() < 0.6:
        c = rng.choice(COMPOUNDS)
        out['temp_compound_mult'][c] += rng.uniform(-0.08, 0.08)

    if rng.random() < 0.65:
        c = rng.choice(COMPOUNDS)
        out['fresh_tire_warmup'][c] += rng.uniform(-0.08, 0.08)

    if rng.random() < 0.6:
        t = rng.choice(TRACKS)
        c = rng.choice(COMPOUNDS)
        out['track_deg_mult'][t][c] += rng.uniform(-0.03, 0.03)

    if rng.random() < 0.35:
        t = rng.choice(TRACKS)
        out['track_pit_mult'][t] += rng.uniform(-0.03, 0.03)

    # Bounds keep the search in sane physics-like ranges.
    out['deg_rate']['SOFT'] = min(0.8, max(0.05, out['deg_rate']['SOFT']))
    out['deg_rate']['MEDIUM'] = min(0.6, max(0.03, out['deg_rate']['MEDIUM']))
    out['deg_rate']['HARD'] = min(0.45, max(0.01, out['deg_rate']['HARD']))
    out['deg_rate_quad']['SOFT'] = min(0.012, max(-0.002, out['deg_rate_quad']['SOFT']))
    out['deg_rate_quad']['MEDIUM'] = min(0.010, max(-0.002, out['deg_rate_quad']['MEDIUM']))
    out['deg_rate_quad']['HARD'] = min(0.008, max(-0.002, out['deg_rate_quad']['HARD']))

    out['cliff_age']['SOFT'] = int(min(20, max(4, round(out['cliff_age']['SOFT']))))
    out['cliff_age']['MEDIUM'] = int(min(35, max(8, round(out['cliff_age']['MEDIUM']))))
    out['cliff_age']['HARD'] = int(min(45, max(10, round(out['cliff_age']['HARD']))))

    out['temp_b'] = max(400.0, out['temp_b'])
    for c in COMPOUNDS:
        out['temp_compound_mult'][c] = min(1.5, max(0.6, out['temp_compound_mult'][c]))
        out['fresh_tire_warmup'][c] = min(1.2, max(-1.2, out['fresh_tire_warmup'][c]))

    for t in TRACKS:
        out['track_pit_mult'][t] = min(1.15, max(0.85, out['track_pit_mult'][t]))
        for c in COMPOUNDS:
            out['track_deg_mult'][t][c] = min(1.25, max(0.75, out['track_deg_mult'][t][c]))

    return out


def split_train_valid(races, valid_fraction, seed):
    rng = random.Random(seed)
    shuffled = list(races)
    rng.shuffle(shuffled)

    valid_size = max(1, int(len(shuffled) * valid_fraction))
    valid = shuffled[:valid_size]
    train = shuffled[valid_size:]

    if not train:
        train = valid

    return train, valid


def fit_coefficients(races, iterations, valid_fraction, seed, objective):
    train_races, valid_races = split_train_valid(races, valid_fraction, seed)

    rng = random.Random(seed)
    best = default_coefficients()
    current = copy.deepcopy(best)

    best_val_metrics = evaluate_metrics(valid_races, best)
    current_val_metrics = dict(best_val_metrics)
    best_obj = objective_value(best_val_metrics, len(valid_races), objective)
    current_obj = best_obj

    print(
        f'baseline objective={objective} '
        f'valid_exact={best_val_metrics["exact"]}/{len(valid_races)} '
        f'valid_top5={best_val_metrics["top5"]:.4f} '
        f'valid_pairwise={best_val_metrics["pairwise"]:.4f}'
    )

    for step in range(1, iterations + 1):
        candidate = mutate(current, rng)

        cand_val_metrics = evaluate_metrics(valid_races, candidate)
        cand_obj = objective_value(cand_val_metrics, len(valid_races), objective)

        better = cand_obj > current_obj

        if better:
            current = candidate
            current_val_metrics = cand_val_metrics
            current_obj = cand_obj

            is_global_best = cand_obj > best_obj
            if is_global_best:
                best = copy.deepcopy(candidate)
                best_val_metrics = dict(cand_val_metrics)
                best_obj = cand_obj
                print(
                    f'step={step} new_best objective={objective} '
                    f'valid_exact={best_val_metrics["exact"]}/{len(valid_races)} '
                    f'valid_top5={best_val_metrics["top5"]:.4f} '
                    f'valid_pairwise={best_val_metrics["pairwise"]:.4f}'
                )

        if step % 500 == 0:
            print(
                f'step={step} current_exact={current_val_metrics["exact"]}/{len(valid_races)} '
                f'current_top5={current_val_metrics["top5"]:.4f} '
                f'current_pairwise={current_val_metrics["pairwise"]:.4f}'
            )

    train_metrics = evaluate_metrics(train_races, best)

    print(
        f'final train_exact={train_metrics["exact"]}/{len(train_races)} '
        f'train_top5={train_metrics["top5"]:.4f} '
        f'train_pairwise={train_metrics["pairwise"]:.4f}'
    )
    print(
        f'final valid_exact={best_val_metrics["exact"]}/{len(valid_races)} '
        f'valid_top5={best_val_metrics["top5"]:.4f} '
        f'valid_pairwise={best_val_metrics["pairwise"]:.4f}'
    )

    return best


def parse_args():
    parser = argparse.ArgumentParser(description='Train and freeze simulator coefficients.')
    parser.add_argument(
        '--output',
        default='solution/frozen_coefficients.json',
        help='Output JSON path for frozen coefficients.',
    )
    parser.add_argument(
        '--max-files',
        type=int,
        default=None,
        help='Optional cap on number of historical files to load.',
    )
    parser.add_argument(
        '--max-races',
        type=int,
        default=None,
        help='Optional cap on number of historical races to load.',
    )
    parser.add_argument(
        '--iterations',
        type=int,
        default=4000,
        help='Number of random-search optimization steps.',
    )
    parser.add_argument(
        '--valid-fraction',
        type=float,
        default=0.15,
        help='Validation split fraction in (0, 1).',
    )
    parser.add_argument(
        '--seed',
        type=int,
        default=42,
        help='Random seed.',
    )
    parser.add_argument(
        '--objective',
        choices=['exact', 'pairwise', 'hybrid'],
        default='hybrid',
        help='Optimization objective for model selection.',
    )
    return parser.parse_args()


def main():
    args = parse_args()

    if not (0.0 < args.valid_fraction < 1.0):
        raise ValueError('--valid-fraction must be between 0 and 1')

    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent

    races = load_historical_races(
        repo_root,
        max_files=args.max_files,
        max_races=args.max_races,
    )

    if not races:
        raise RuntimeError('No historical races found for training.')

    print(f'loaded_races={len(races)}')

    coeffs = fit_coefficients(
        races,
        iterations=args.iterations,
        valid_fraction=args.valid_fraction,
        seed=args.seed,
        objective=args.objective,
    )

    output_path = (repo_root / args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(coeffs, f, indent=2, sort_keys=True)
        f.write('\n')

    print(f'wrote_coefficients={output_path}')


if __name__ == '__main__':
    main()
