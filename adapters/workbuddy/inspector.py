"""Public on-demand WorkBuddy memory inspector; no write operations."""
import argparse
import json
import subprocess
from .adapter import WorkBuddyAdapter


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=WorkBuddyAdapter.OPERATIONS)
    parser.add_argument('--task', required=True)
    parser.add_argument('--project', required=True)
    parser.add_argument('--machine', required=True)
    parser.add_argument('--store')
    parser.add_argument('--budget', type=int, default=1000)
    parser.add_argument('--id')
    args = parser.parse_args()
    try:
        result = WorkBuddyAdapter(store=args.store).inspect(
            args.task, args.project, args.machine, args.operation, args.budget, args.id)
    except (ValueError, OSError, subprocess.SubprocessError, KeyError, TypeError):
        parser.exit(2, 'Read-only inspection refused; check operation, store and scope.\n')
    print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == '__main__':
    main()
