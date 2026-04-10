#!/usr/bin/env python3
"""Run Round 5 Multi-model Consensus Poisoning corpus."""
from round5_consensus_poisoning import run
import argparse, sys
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="https://api.sgraal.com")
    parser.add_argument("--key", default="sg_demo_playground")
    args = parser.parse_args()
    sys.exit(0 if run(args.url, args.key) else 1)
