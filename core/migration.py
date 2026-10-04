"""Serialized, journaled store moves through the public Memory Gate."""
import copy
import json
import os
from pathlib import Path
from contextlib import contextmanager
import time

def marker(path):
    return Path(str(path) + '.move-journal.json')

def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = Path(str(path) + '.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    os.replace(temp, path)

@contextmanager
def journal_lock(authority):
    lock = Path(str(authority) + '.lock')
    lock.parent.mkdir(parents=True, exist_ok=True)
    with lock.open('a+b') as handle:
        if not lock.stat().st_size:
            handle.write(b'0');handle.flush()
        deadline = time.monotonic() + 10
        while True:
            try:
                handle.seek(0)
                if os.name == 'nt':
                    import msvcrt
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError:
                if time.monotonic() >= deadline:
                    raise ValueError('Migration busy; retry after writer completes')
                time.sleep(0.05)
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == 'nt':
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle, fcntl.LOCK_UN)

def repair(authority):
    if not authority.exists():
        return
    journal = json.loads(authority.read_text(encoding='utf-8'))
    if not journal.get('committed'):
        atomic_json(journal['target'], journal['target_before'])
        atomic_json(journal['source'], journal['source_before'])
    for name in (journal['target'], journal['source']):
        marker(name).unlink(missing_ok=True)

def recover(path):
    pointer = marker(Path(path).resolve())
    if not pointer.exists():
        return
    try:
        entry = json.loads(pointer.read_text(encoding='utf-8'))
    except FileNotFoundError:
        return
    authority = Path(entry['journal'])
    with journal_lock(authority):
        if authority.exists():
            repair(authority)
        else:
            pointer.unlink(missing_ok=True)

def move_record(source_path, target_path, record_id, agent_scope=None, source_agent=None):
    from core.engine import Memory, now
    source, target = Memory(source_path), Memory(target_path)
    source.path, target.path = source.path.resolve(), target.path.resolve()
    if source.path == target.path:
        raise ValueError('Stores must differ')
    before_source, before_target = source.load(), target.load()
    old = next(r for r in before_source['records'] if r['id'] == record_id)
    if old['status'] != 'ACTIVE' or source.expired(old):
        raise ValueError('Only live ACTIVE records can move')
    if any(r['id'] == record_id for r in before_target['records']):
        raise ValueError('Destination already has this ID')
    new = copy.deepcopy(old)
    if agent_scope is not None:
        new['agent_scope'] = list(agent_scope)
    if source_agent is not None:
        if source_agent not in new['agent_scope']:
            raise ValueError('Source agent must be explicitly allowed')
        new['metadata']['source_agent'] = source_agent
    if any(new['metadata'].get(k) for k in ('derived_from','consolidates','supplements')):
        raise ValueError('Derived records require separate relationship review')
    candidate = dict(new, confirmed=True)
    verdict = target.evaluate(candidate, before_target)
    if verdict['decision'] != 'ACCEPT':
        return verdict
    authority = marker(source.path)
    journal = dict(journal=str(authority), source=str(source.path), target=str(target.path),
                   source_before=before_source, target_before=before_target, committed=False)
    with journal_lock(authority):
        atomic_json(authority, journal)
        try:
            atomic_json(marker(target.path), {'journal': str(authority)})
            destination = copy.deepcopy(before_target)
            staged = copy.deepcopy(new)
            staged['status'] = 'RETIRED'
            destination['records'].append(staged)
            destination['audit'].extend(copy.deepcopy(e) for e in before_source['audit'] if record_id in e['memory_ids'])
            target.audit(destination, 'MOVE_IN', [record_id], 'Explicit cross-store move', old['source_type'])
            target.save(destination)
            origin = copy.deepcopy(before_source)
            retired = next(r for r in origin['records'] if r['id'] == record_id)
            retired.update(status='RETIRED', updated_at=now())
            source.audit(origin, 'MOVE_OUT', [record_id], 'Explicit cross-store move', old['source_type'])
            source.save(origin)
            destination['records'][-1] = new
            target.save(destination)
            journal['committed'] = True
            atomic_json(authority, journal)
        except BaseException:
            repair(authority)
            raise
        repair(authority)
    return dict(decision='ACCEPT', record=new, moved_id=record_id)
