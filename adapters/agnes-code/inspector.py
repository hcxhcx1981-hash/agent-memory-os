"""Read-only, project/machine-scoped entry for the existing Agnes Code adapter."""
import argparse
import json
import subprocess
from pathlib import Path
from .adapter import AgnesCodeAdapter


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('operation',choices=['inject','retrieve','smart-retrieve','why','explain'])
    p.add_argument('--task',required=True);p.add_argument('--project',required=True)
    p.add_argument('--machine',required=True);p.add_argument('--budget',type=int,default=500)
    p.add_argument('--store');p.add_argument('--id')
    a=p.parse_args()
    try:
        result=AgnesCodeAdapter(Path(__file__).resolve().parents[2],a.store).inspect(
            a.task,a.project,a.machine,a.operation,a.budget,a.id)
    except (ValueError,OSError,subprocess.SubprocessError,KeyError,TypeError):
        p.exit(2,'Read-only inspection refused; check store, scope and operation.\n')
    print(json.dumps(result,ensure_ascii=True,indent=2))


if __name__=='__main__':main()
