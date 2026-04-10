#!/usr/bin/env python3
"""Run Round 6 Memory Time Attack corpus."""
import argparse
import sys

from round6_memory_time_attack import run

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run Round 6 Memory Time Attack corpus"
    )
    parser.add_argument("--url", default="https://api.sgraal.com")
    parser.add_argument("--key", default="sg_demo_playground")
    args = parser.parse_args()
    ok = run(args.url, args.key)
    sys.exit(0 if ok else 1)
