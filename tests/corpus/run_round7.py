#!/usr/bin/env python3
"""Run Round 7 Identity Drift corpus."""
from round7_identity_drift import run
import argparse, sys
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="https://api.sgraal.com")
    parser.add_argument("--key", default="sg_demo_playground")
    args = parser.parse_args()
    sys.exit(0 if run(args.url, args.key) else 1)
