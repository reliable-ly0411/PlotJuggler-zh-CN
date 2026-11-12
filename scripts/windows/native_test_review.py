#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Validate per-suite safety review and conservative CTest selection closure.

This module reads evidence and plans; it never launches discovery or tests.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import stat


class ReviewError(Exception):
    """Review evidence or CTest selection cannot establish a safe run."""


UNRUN = {'platform_not_applicable', 'condition_missing', 'safety_unreviewed', 'disabled'}


def digest(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(part)
    return value.hexdigest()


def properties(test):
    values = {}
    for prop in test.get('properties', []):
        if not isinstance(prop, dict) or not isinstance(prop.get('name'), str) or 'value' not in prop:
            raise ReviewError('malformed CTest property')
        if prop['name'] in values:
            raise ReviewError('duplicate CTest property')
        values[prop['name']] = prop['value']
    return values


def indexed(discovery):
    if not isinstance(discovery, dict) or discovery.get('kind') != 'ctestInfo' or not isinstance(discovery.get('tests'), list):
        raise ReviewError('invalid full CTest discovery')
    result = {}
    for test in discovery['tests']:
        if not isinstance(test, dict) or not isinstance(test.get('name'), str) or not test['name'] or '\n' in test['name'] or '\r' in test['name']:
            raise ReviewError('invalid CTest case name')
        if test['name'] in result:
            raise ReviewError('duplicate CTest case name')
        result[test['name']] = (test, properties(test))
    if not result:
        raise ReviewError('empty CTest discovery')
    return result


def as_names(value):
    if isinstance(value, str):
        return [value]
    if isinstance(value, list) and all(isinstance(x, str) and x for x in value):
        return value
    raise ReviewError('invalid CTest dependency or fixture value')


def selection_closure(discovery, chosen):
    """Include all declared DEPENDS and fixture setup/cleanup recursively."""
    tests = indexed(discovery)
    chosen = set(chosen)
    if not chosen or not chosen <= tests.keys():
        raise ReviewError('empty or unknown CTest selection')
    setup, cleanup = {}, {}
    for name, (_, props) in tests.items():
        for field, target in (('FIXTURES_SETUP', setup), ('FIXTURES_CLEANUP', cleanup)):
            if field in props:
                for fixture in as_names(props[field]):
                    target.setdefault(fixture, set()).add(name)
    closed, queue = set(chosen), list(chosen)
    while queue:
        name = queue.pop()
        props = tests[name][1]
        additional = set(as_names(props['DEPENDS'])) if 'DEPENDS' in props else set()
        for fixture in as_names(props['FIXTURES_REQUIRED']) if 'FIXTURES_REQUIRED' in props else []:
            handlers = setup.get(fixture, set()) | cleanup.get(fixture, set())
            if not handlers:
                raise ReviewError('required CTest fixture has no registered setup or cleanup: ' + fixture)
            additional.update(handlers)
        # CTest does not add cleanup merely because its setup was selected.
        # A setup introduced directly or by DEPENDS still needs every declared
        # cleanup, whose own dependencies are recursively closed below.
        for fixture in as_names(props['FIXTURES_SETUP']) if 'FIXTURES_SETUP' in props else []:
            additional.update(cleanup.get(fixture, set()))
        if not additional <= tests.keys():
            raise ReviewError('CTest dependency is absent from full discovery')
        for item in additional - closed:
            closed.add(item)
            queue.append(item)
    return closed


def verify_evidence(run_root, entries):
    """Hash explicit review evidence without following linked paths."""
    if not isinstance(entries, list) or not entries:
        raise ReviewError('each reviewed scope needs at least one evidence file')
    run_root = Path(run_root).absolute()
    verified = []
    for item in entries:
        if not isinstance(item, dict) or not isinstance(item.get('path'), str) or not re.fullmatch(r'[0-9a-f]{64}', str(item.get('sha256', ''))):
            raise ReviewError('invalid review evidence entry')
        value = item['path']
        if not value or '\\' in value or any(x in ('', '.', '..') or ':' in x for x in value.split('/')):
            raise ReviewError('review evidence must use a safe run-relative path')
        path = run_root.joinpath(*value.split('/'))
        if not path.is_file() or not path.resolve().is_relative_to(run_root.resolve()):
            raise ReviewError('review evidence is missing or outside the owned run root')
        for parent in (path, *path.parents):
            info = parent.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
                raise ReviewError('review evidence contains a link or reparse point')
            if parent == run_root:
                break
        if digest(path) != item['sha256']:
            raise ReviewError('review evidence hash mismatch')
        verified.append(value)
    return verified


def validate_review(record, run_root, identity, source_sha, source_tree, manifest_sha, probe_sha, preflight_sha, discoveries,
                    allow_unreviewed_discovery=False):
    """Require a complete case partition and source/token/probe-bound evidence."""
    if not isinstance(record, dict) or record.get('schema') != 1:
        raise ReviewError('invalid safety review schema')
    expected = {'source_sha': source_sha, 'source_tree': source_tree, 'manifest_sha256': manifest_sha,
                'probe_sha256': probe_sha, 'preflight_sha256': preflight_sha, 'identity': identity}
    if any(record.get(key) != value for key, value in expected.items()):
        raise ReviewError('safety review does not match the source, manifest, token or actual probe')
    session = record.get('session_review')
    if (not isinstance(session, dict) or session.get('status') != 'approved' or
            not isinstance(session.get('reason'), str) or not session['reason'].strip()):
        raise ReviewError('independent evidence of the active interactive session is required')
    verify_evidence(run_root, session.get('evidence'))
    suites = record.get('suites')
    if not isinstance(suites, list) or {x.get('id') for x in suites if isinstance(x, dict)} != set(discoveries):
        raise ReviewError('review must cover exactly the declared test suites')
    if len(suites) != len(discoveries):
        raise ReviewError('duplicate suite safety review')
    decisions = {}
    for suite in suites:
        name = suite['id']
        tests = indexed(discoveries[name])
        discovery_review = suite.get('discovery')
        accepted = {'approved'} | ({'safety_unreviewed', 'condition_missing'} if allow_unreviewed_discovery else set())
        if (not isinstance(discovery_review, dict) or discovery_review.get('status') not in accepted or
                not isinstance(discovery_review.get('reason'), str) or not discovery_review['reason'].strip()):
            raise ReviewError('full discovery has not received an explicit evidence-backed review: ' + name)
        verify_evidence(run_root, discovery_review.get('evidence'))
        groups = suite.get('groups')
        if not isinstance(groups, list) or not groups:
            raise ReviewError('suite safety review has no groups: ' + name)
        cases, group_names = {}, set()
        for group in groups:
            if (not isinstance(group, dict) or not isinstance(group.get('name'), str) or not group['name'] or
                    group['name'] in group_names or group.get('status') not in UNRUN | {'approved'} or
                    not isinstance(group.get('reason'), str) or not group['reason'].strip()):
                raise ReviewError('invalid or duplicate safety review group')
            group_names.add(group['name'])
            evidence = verify_evidence(run_root, group.get('evidence'))
            if group['status'] == 'approved':
                path_review = group.get('runtime_paths_review')
                if (not isinstance(path_review, dict) or path_review.get('status') != 'approved' or
                        not isinstance(path_review.get('reason'), str) or not path_review['reason'].strip()):
                    raise ReviewError('approved group needs explicit argv, relative path and dynamic dependency review')
                verify_evidence(run_root, path_review.get('evidence'))
            members = group.get('cases')
            if not isinstance(members, list) or not members or any(not isinstance(x, str) for x in members):
                raise ReviewError('review group has no explicit case list')
            for case in members:
                if case not in tests or case in cases:
                    raise ReviewError('unknown or multiply reviewed CTest case: ' + case)
                disabled = tests[case][1].get('DISABLED', False)
                if disabled and group['status'] == 'approved':
                    raise ReviewError('disabled CTest case cannot be approved as executed: ' + case)
                cases[case] = {'status': group['status'], 'reason': group['reason'], 'evidence': evidence, 'group': group['name']}
        if set(cases) != set(tests):
            raise ReviewError('safety review does not partition the complete discovery: ' + name)
        decisions[name] = cases
    return decisions


def approved_selection(discovery, decisions, mode, desired=None):
    """Require all closure members to have been explicitly approved."""
    all_cases = set(indexed(discovery))
    if set(decisions) != all_cases:
        raise ReviewError('review decisions do not cover the full underlying tree')
    desired = all_cases if desired is None else set(desired)
    if not desired or not desired <= all_cases:
        raise ReviewError('desired cases are empty or absent from the full tree')
    approved = {name for name, item in decisions.items() if item['status'] == 'approved'}
    requested = desired & approved
    unrun = [{'case': name, **decisions[name]} for name in sorted(desired - approved)]
    if mode == 'full' and unrun:
        raise ReviewError('full mode cannot start with unclosed cases')
    if mode not in ('full', 'reviewed-subset'):
        raise ReviewError('unknown test execution mode')
    if not requested:
        return set(), unrun
    closure = selection_closure(discovery, requested)
    missing = sorted(closure - approved)
    if missing:
        raise ReviewError('CTest selection requires unapproved dependencies or fixtures: ' + ', '.join(missing))
    return closure, unrun
