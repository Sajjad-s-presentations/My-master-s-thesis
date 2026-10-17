from decimal import Decimal
from src.signed_benaloh import Benaloh, ClientSigner, SignedBenalohServer, create_client_submission, \
    fingerprint_public_key
import time
import random
from dataclasses import replace
import statistics
import csv
import os
from datetime import datetime


def generate_test_data(num_clients, bits, r=10_000_019):
    """Generate test data with given number of clients"""
    benaloh = Benaloh(bits=bits, r=r)
    public = benaloh.keygen()
    server = SignedBenalohServer(benaloh)

    # Generate random clients with different weights
    clients = []
    for i in range(num_clients):
        client_id = f"client-{i + 1:03d}"
        signer = ClientSigner(client_id)
        # Random value between 0 and 1 with 4 decimals
        value = f"{random.uniform(0.1, 0.99):.4f}"
        weight = random.randint(1, 5)
        clients.append((signer, value, weight))

    return benaloh, server, clients


def run_test_configuration(bits, num_clients, iterations=100):
    """Run test for a specific configuration and return timing results"""
    r = 10_000_019
    results = {
        'setup_times': [],
        'registration_times': [],
        'encryption_times': [],
        'aggregation_times': [],
        'decryption_times': [],
        'total_times': []
    }

    for iteration in range(iterations):
        start_total = time.time()

        # Setup phase
        start_setup = time.time()
        benaloh = Benaloh(bits=bits, r=r)
        public = benaloh.keygen()
        server = SignedBenalohServer(benaloh)

        # Generate clients
        clients = []
        for i in range(num_clients):
            client_id = f"client-{i + 1:03d}"
            signer = ClientSigner(client_id)
            value = f"{random.uniform(0.1, 0.99):.4f}"
            weight = random.randint(1, 5)
            clients.append((signer, value, weight))
        setup_time = time.time() - start_setup
        results['setup_times'].append(setup_time)

        # Registration phase
        start_reg = time.time()
        for signer, _, _ in clients:
            server.register_client(signer.client_id, signer.export_public_key())
        reg_time = time.time() - start_reg
        results['registration_times'].append(reg_time)

        # Encryption phase
        start_enc = time.time()
        round_id = f"round-{iteration:04d}"
        envelopes = [
            create_client_submission(benaloh, signer, value, weight, round_id)
            for signer, value, weight in clients
        ]
        enc_time = time.time() - start_enc
        results['encryption_times'].append(enc_time)

        # Aggregation phase
        start_agg = time.time()
        aggregate, total_weight, count = server.accept_and_aggregate(envelopes, round_id)
        agg_time = time.time() - start_agg
        results['aggregation_times'].append(agg_time)

        # Decryption phase
        start_dec = time.time()
        result = server.decrypt_weighted_average(aggregate, total_weight)
        dec_time = time.time() - start_dec
        results['decryption_times'].append(dec_time)

        total_time = time.time() - start_total
        results['total_times'].append(total_time)

    return results


def save_results_to_csv(results_by_config, filename=None):
    """Save performance results to CSV file"""
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"benaloh_performance_results_{timestamp}.csv"

    # Create results directory if it doesn't exist
    os.makedirs("results", exist_ok=True)
    filepath = os.path.join("results", filename)

    with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = [
            'bits', 'num_clients', 'phase',
            'avg_time_ms', 'std_time_ms', 'min_time_ms', 'max_time_ms', 'median_time_ms'
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for config_key, results in results_by_config.items():
            bits, num_clients = config_key

            for phase, times in results.items():
                if not times:  # Skip empty lists
                    continue

                avg_time = statistics.mean(times) * 1000
                std_time = statistics.stdev(times) * 1000 if len(times) > 1 else 0
                min_time = min(times) * 1000
                max_time = max(times) * 1000
                median_time = statistics.median(times) * 1000

                writer.writerow({
                    'bits': bits,
                    'num_clients': num_clients,
                    'phase': phase.replace('_times', ''),
                    'avg_time_ms': round(avg_time, 4),
                    'std_time_ms': round(std_time, 4),
                    'min_time_ms': round(min_time, 4),
                    'max_time_ms': round(max_time, 4),
                    'median_time_ms': round(median_time, 4)
                })

    print(f"\nResults saved to: {filepath}")
    return filepath


def save_summary_to_csv(results_by_config, filename=None):
    """Save summary comparison results to CSV file"""
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"benaloh_summary_results_{timestamp}.csv"

    # Create results directory if it doesn't exist
    os.makedirs("results", exist_ok=True)
    filepath = os.path.join("results", filename)

    # Define all phases and statistics
    phases = ['total', 'setup', 'registration', 'encryption', 'aggregation', 'decryption']
    stats = ['avg', 'std', 'min', 'max', 'median']

    # Build fieldnames dynamically
    fieldnames = ['bits', 'num_clients']
    for phase in phases:
        for stat in stats:
            fieldnames.append(f'{phase}_{stat}_ms')

    with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for config_key, results in results_by_config.items():
            bits, num_clients = config_key

            # Initialize summary with config values
            summary = {'bits': bits, 'num_clients': num_clients}

            # Calculate summary statistics for each phase
            for phase, times in results.items():
                if not times:  # Skip empty lists
                    continue

                phase_name = phase.replace('_times', '')

                try:
                    avg_time = statistics.mean(times) * 1000
                    std_time = statistics.stdev(times) * 1000 if len(times) > 1 else 0
                    min_time = min(times) * 1000
                    max_time = max(times) * 1000
                    median_time = statistics.median(times) * 1000

                    summary[f'{phase_name}_avg_ms'] = round(avg_time, 4)
                    summary[f'{phase_name}_std_ms'] = round(std_time, 4)
                    summary[f'{phase_name}_min_ms'] = round(min_time, 4)
                    summary[f'{phase_name}_max_ms'] = round(max_time, 4)
                    summary[f'{phase_name}_median_ms'] = round(median_time, 4)
                except statistics.StatisticsError:
                    # Handle case where there's only one data point
                    continue

            # Ensure all expected fields exist in summary
            for field in fieldnames:
                if field not in summary:
                    summary[field] = 0

            writer.writerow(summary)

    print(f"Summary saved to: {filepath}")
    return filepath


def print_report(results_by_config):
    """Print detailed report of timing results"""
    print("\n" + "=" * 80)
    print("PERFORMANCE REPORT")
    print("=" * 80)

    for config_key, results in results_by_config.items():
        bits, num_clients = config_key
        total_iterations = len(next(iter(results.values())))
        print(f"\n--- Configuration: {bits}-bit, {num_clients} clients ({total_iterations} iterations) ---")

        for phase, times in results.items():
            if not times:
                continue

            phase_display = phase.upper().replace('_', ' ').replace('TIMES', 'TIME')
            avg_time = statistics.mean(times) * 1000
            std_time = statistics.stdev(times) * 1000 if len(times) > 1 else 0
            min_time = min(times) * 1000
            max_time = max(times) * 1000
            median_time = statistics.median(times) * 1000

            print(f"\n{phase_display}:")
            print(f"  Average: {avg_time:.4f} ms")
            print(f"  Std Dev: {std_time:.4f} ms")
            print(f"  Min:     {min_time:.4f} ms")
            print(f"  Max:     {max_time:.4f} ms")
            print(f"  Median:  {median_time:.4f} ms")

    print("\n" + "=" * 80)
    print("SUMMARY COMPARISON")
    print("=" * 80)

    print(
        f"\n{'Configuration':<25} {'Total (ms)':<15} {'Encryption (ms)':<18} {'Aggregation (ms)':<18} {'Setup (ms)':<15}")
    print("-" * 95)

    for config_key, results in results_by_config.items():
        bits, num_clients = config_key

        # Safely get values with defaults
        total_times = results.get('total_times', [0])
        enc_times = results.get('encryption_times', [0])
        agg_times = results.get('aggregation_times', [0])
        setup_times = results.get('setup_times', [0])

        total_avg = statistics.mean(total_times) * 1000 if total_times else 0
        enc_avg = statistics.mean(enc_times) * 1000 if enc_times else 0
        agg_avg = statistics.mean(agg_times) * 1000 if agg_times else 0
        setup_avg = statistics.mean(setup_times) * 1000 if setup_times else 0

        print(
            f"{bits}-bit, {num_clients} clients  {total_avg:>10.2f}     {enc_avg:>12.2f}          {agg_avg:>12.2f}          {setup_avg:>10.2f}")


def run_demo_verification():
    """Run the original demo verification with tamper detection"""
    print("\n" + "=" * 80)
    print("ORIGINAL DEMO VERIFICATION")
    print("=" * 80)

    try:
        benaloh = Benaloh(bits=256, r=10_000_019)
        public = benaloh.keygen()
        server = SignedBenalohServer(benaloh)

        clients = [
            (ClientSigner("client-001"), "0.7000", 1),
            (ClientSigner("client-002"), "0.8500", 2),
            (ClientSigner("client-003"), "0.9000", 1),
        ]

        for signer, _, _ in clients:
            server.register_client(signer.client_id, signer.export_public_key())
            print(f"registered {signer.client_id}: key={fingerprint_public_key(signer.export_public_key())[:16]}...")

        round_id = "round-2026-08-23-001"
        envelopes = [
            create_client_submission(benaloh, signer, value, weight, round_id)
            for signer, value, weight in clients
        ]

        aggregate, total_weight, count = server.accept_and_aggregate(envelopes, round_id)
        result = server.decrypt_weighted_average(aggregate, total_weight)

        expected = (
                           Decimal("0.7000") * 1
                           + Decimal("0.8500") * 2
                           + Decimal("0.9000") * 1
                   ) / Decimal(total_weight)

        print("\nVerification Results:")
        print(f"  Accepted clients: {count}")
        print(f"  Total weight: {total_weight}")
        print(f"  Weighted average: {result}")
        print(f"  Expected: {expected}")
        print(f"  Match: {'✓' if result == expected else '✗'}")

        # Demonstrate tamper detection before acceptance
        print("\nTamper Detection Test:")
        tampered = envelopes[0]
        tampered = replace(tampered, weight=99)
        fresh_server = SignedBenalohServer(benaloh)
        fresh_server.register_client(clients[0][0].client_id, clients[0][0].export_public_key())

        try:
            fresh_server.verify(tampered, round_id)
            print("  Tamper test: FAILED - Tampered submission was accepted!")
        except ValueError as exc:
            print(f"  Tamper test: PASSED - {exc}")

    except Exception as e:
        print(f"Demo verification failed: {e}")


def main():
    """Main function to run all performance tests and demonstrations"""

    # Test configurations
    configs = [
        (256, 100),
        (256, 200),
        (256, 300),
        (512, 100),
        (512, 200),
        (512, 300),
        (1024, 100),
        (1024, 200),
        (1024, 300),
    ]

    iterations = 100
    results_by_config = {}

    print("=" * 80)
    print("BENALOH SIGNCRYPTION PERFORMANCE TESTING")
    print("=" * 80)
    print(f"\nTesting {len(configs)} configurations with {iterations} iterations each")
    print("This may take several minutes...")

    # Run performance tests
    for idx, (bits, num_clients) in enumerate(configs, 1):
        print(f"\n[{idx}/{len(configs)}] Testing: {bits}-bit, {num_clients} clients...")
        start_time = time.time()

        try:
            results = run_test_configuration(bits, num_clients, iterations)
            results_by_config[(bits, num_clients)] = results

            elapsed = time.time() - start_time
            print(f"  Completed in {elapsed:.2f} seconds")
        except Exception as e:
            print(f"  ERROR: Failed to run test - {e}")
            continue

    if not results_by_config:
        print("\nNo tests completed successfully. Exiting.")
        return

    # Print detailed report
    print_report(results_by_config)

    # Save results to CSV
    print("\n" + "=" * 80)
    print("SAVING RESULTS TO CSV")
    print("=" * 80)

    # Create results directory
    os.makedirs("results", exist_ok=True)

    # Save detailed results
    detailed_csv = save_results_to_csv(results_by_config)

    # Save summary results
    summary_csv = save_summary_to_csv(results_by_config)

    print(f"\nCSV files saved in 'results' directory:")
    print(f"  - Detailed results: {detailed_csv}")
    print(f"  - Summary results: {summary_csv}")

    # Run demo verification
    run_demo_verification()

    print("\n" + "=" * 80)
    print("TESTING COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()