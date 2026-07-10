import argparse
import os
from engine import IdentityEngine
from simulator import start_simulation

def main():
    parser = argparse.ArgumentParser(description="Sherlock Real-Time Candidate Identification Engine")
    parser.add_argument(
        "--scenario", 
        type=str, 
        default="data/scenario_messy_name.json", 
        help="Path to the JSON scenario file"
    )
    parser.add_argument(
        "--speed", 
        type=float, 
        default=5.0, 
        help="Playback speed multiplier (e.g., 5.0 runs 5x faster than real-time)"
    )
    args = parser.parse_args()

    if not os.path.exists(args.scenario):
        print(f"Error: Scenario file not found at '{args.scenario}'")
        return

    # Initialize the engine and start processing the live stream
    engine = IdentityEngine()
    start_simulation(args.scenario, engine, speed_factor=args.speed)

if __name__ == "__main__":
    main()
