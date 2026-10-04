"""Public read-only Codex context inspector."""
import argparse
import json
import subprocess
from .adapter import CodexAdapter

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('operation',choices=['retrieve','smart-retrieve','inject','why','explain'])
    p.add_argument('--task',required=True);p.add_argument('--project');p.add_argument('--machine',required=True)
    p.add_argument('--store');p.add_argument('--budget',type=int,default=1000);p.add_argument('--id')
    a=p.parse_args()
    try:
        value=CodexAdapter(store=a.store).inspect(a.task,a.project,a.machine,a.operation,a.budget,a.id)
    except (ValueError, OSError, subprocess.SubprocessError):
        p.exit(2,'Read-only inspection refused; check operation and scope.\n')
    print(json.dumps(value,ensure_ascii=True,indent=2))

if __name__=='__main__':main()
