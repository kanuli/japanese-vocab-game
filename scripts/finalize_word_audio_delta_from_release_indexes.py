#!/usr/bin/env python3
"""Finalize the reviewed 713-key hosted-audio delta from already-published Release indexes.

This does not synthesize audio. It validates every published index against the exact
reviewed delta source, then reconstructs the three small ready catalogs consumed by
the browser. Base hosted catalogs remain unchanged.
"""
from __future__ import annotations
import argparse, json
from pathlib import Path


def load(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))


def write(path: Path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, separators=(',', ':')) + '\n', encoding='utf-8')


def index_url(repo: str, tag: str, name: str):
    return f'https://github.com/{repo}/releases/download/{tag}/{name}'


def validate_index(idx: dict, ids: set[str], expected_n: int, source: Path):
    if int(idx.get('wordCount', -1)) != expected_n:
        raise SystemExit(f'{source}: wordCount {idx.get("wordCount")} != {expected_n}')
    bundles = idx.get('bundles') or {}
    b = bundles.get('0') or bundles.get(0)
    if not isinstance(b, dict):
        raise SystemExit(f'{source}: missing bundle 0')
    members = b.get('members') or {}
    if set(map(str, members)) != ids:
        missing = len(ids - set(map(str, members)))
        extra = len(set(map(str, members)) - ids)
        raise SystemExit(f'{source}: member IDs mismatch; missing={missing} extra={extra}')
    if not b.get('githubUrl') and not b.get('hfUrl') and not b.get('url'):
        raise SystemExit(f'{source}: bundle has no hosted URL')
    return members


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--catalog', default='word-audio-delta-catalog.json')
    ap.add_argument('--vv-dir', required=True)
    ap.add_argument('--st-dir', required=True)
    ap.add_argument('--av-dir', required=True)
    ap.add_argument('--repo', default='kanuli/japanese-vocab-game')
    ap.add_argument('--vv-tag', required=True)
    ap.add_argument('--st-tag', required=True)
    ap.add_argument('--av-tag', required=True)
    args = ap.parse_args()

    src = load(Path(args.catalog))
    items = list(src.get('items') or [])
    words = src.get('words') or {}
    n = int(src.get('wordCount', -1))
    if n != 713 or len(items) != n or len(words) != n:
        raise SystemExit(f'Expected exact reviewed 713-key source; got wordCount={n}, items={len(items)}, words={len(words)}')
    ids = {str(x['id']) for x in items}
    if len(ids) != n:
        raise SystemExit('Delta source IDs are not unique')

    # VOICEVOX: exactly 43 published speaker indexes.
    vv_files = sorted(Path(args.vv_dir).glob('word-voicevox-delta-s??-index.json'))
    if len(vv_files) != 43:
        raise SystemExit(f'Expected 43 VOICEVOX indexes, got {len(vv_files)}')
    vv_group = {}
    for p in vv_files:
        d = load(p); validate_index(d, ids, n, p)
        key = str(d.get('speakerKey') or '')
        if not key or key in vv_group:
            raise SystemExit(f'{p}: invalid/duplicate speakerKey {key!r}')
        vv_group[key] = {
            'name': d.get('speaker'), 'style': d.get('style'), 'styleId': d.get('styleId'),
            'credit': f"VOICEVOX:{d.get('speaker')}",
            'indexGithubUrl': index_url(args.repo, args.vv_tag, p.name),
        }
    if sorted(vv_group) != [f's{i:02d}' for i in range(1,44)]:
        raise SystemExit('VOICEVOX index keys are not canonical s01..s43')
    vv = {
        'version':1,'status':'ready','engine':'voicevox-delta','storage':'github-releases-range-bundles',
        'wordCount':n,'speakerCount':43,'recordingCount':n*43,'shardCount':1,
        'coverageRule':'exact reading|written-form','words':words,'speakers':vv_group,
    }

    # Supertonic 3: exactly ten F1-F5/M1-M5 indexes.
    expected_st = [f'F{i}' for i in range(1,6)] + [f'M{i}' for i in range(1,6)]
    st_files = sorted(Path(args.st_dir).glob('word-supertonic3-delta-*-index.json'))
    st_group = {}
    for p in st_files:
        d = load(p); validate_index(d, ids, n, p)
        key = str(d.get('voice') or '')
        if key not in expected_st or key in st_group:
            raise SystemExit(f'{p}: invalid/duplicate Supertonic voice {key!r}')
        st_group[key] = {'label': d.get('label') or key, 'indexGithubUrl': index_url(args.repo, args.st_tag, p.name)}
    if set(st_group) != set(expected_st):
        raise SystemExit(f'Supertonic index set mismatch: {sorted(st_group)}')
    st = {
        'version':1,'status':'ready','engine':'supertonic-3-delta','storage':'github-releases-range-bundles',
        'wordCount':n,'voiceCount':10,'recordingCount':n*10,'shardCount':1,
        'coverageRule':'exact reading|written-form','words':words,'voices':st_group,
    }

    # AivisSpeech: exactly four reviewed styles.
    av_files = sorted(Path(args.av_dir).glob('word-aivis-delta-a*-index.json'))
    if len(av_files) != 4:
        raise SystemExit(f'Expected 4 Aivis indexes, got {len(av_files)}')
    av_group = {}; model = None
    for p in av_files:
        d = load(p); validate_index(d, ids, n, p)
        key = str(d.get('voice') or '')
        if not key or key in av_group:
            raise SystemExit(f'{p}: invalid/duplicate Aivis voice {key!r}')
        mm = {
            'name':d.get('modelName'),'version':d.get('modelVersion'),'architecture':d.get('modelArchitecture'),
            'license':d.get('license'),'licenseSha256':d.get('licenseSha256')
        }
        if model is not None and model != mm:
            raise SystemExit('Aivis model metadata differs across indexes')
        model = mm
        av_group[key] = {
            'speaker':d.get('speaker'),'style':d.get('style'),'displayName':d.get('displayName') or f"{d.get('speaker')}｜{d.get('style')}",
            'modelName':d.get('modelName'),'modelVersion':d.get('modelVersion'),'modelArchitecture':d.get('modelArchitecture'),
            'license':d.get('license'),'licenseSha256':d.get('licenseSha256'),
            'indexGithubUrl':index_url(args.repo,args.av_tag,p.name),
        }
    if sorted(av_group) != [f'a{i:02d}' for i in range(1,5)]:
        raise SystemExit(f'Aivis index keys mismatch: {sorted(av_group)}')
    av = {
        'version':1,'status':'ready','engine':'aivisspeech-style-bert-vits2-delta','storage':'github-releases-range-bundles',
        'wordCount':n,'voiceCount':4,'recordingCount':n*4,'shardCount':1,
        'coverageRule':'exact reading|written-form','model':model,'words':words,'voices':av_group,
    }

    write(Path('word-voicevox-delta-catalog.json'), vv)
    write(Path('word-supertonic3-delta-catalog.json'), st)
    write(Path('word-aivis-delta-catalog.json'), av)
    summary = {
        'status':'PASS','exact_delta_words':n,
        'voicevox':{'voices':43,'recordings':n*43,'indexes':43},
        'supertonic3':{'voices':10,'recordings':n*10,'indexes':10},
        'aivis':{'voices':4,'recordings':n*4,'indexes':4},
        'total_recordings':n*(43+10+4),
        'source':'existing GitHub Release tar/index assets; no re-synthesis performed by finalizer'
    }
    write(Path('audit/vocab/results/voice_delta_completion.json'), summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
