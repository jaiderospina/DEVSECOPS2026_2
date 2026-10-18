"""Measure host staging scripts explicitly across the sanitized env boundary."""
import itertools
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'dast'))
import ci

counter = itertools.count()


def measured_script(name, *arguments):
    source = (ROOT / 'dast' / name).resolve()
    if source.parent != ROOT / 'dast' or not source.is_file():
        raise RuntimeError('Invalid staging test script')
    data = ROOT / 'reports' / f'coverage-data.zap-child-{next(counter):03d}'
    return ci.execute([sys.executable, '-m', 'coverage', 'run',
                       '--data-file=' + str(data), str(source), *arguments])


if __name__ == '__main__':
    if Path.cwd().resolve() != ROOT:
        raise SystemExit('Run the staging coverage harness from the repository root')
    ci.script = measured_script
    try:
        ci.main()
    except Exception as error:
        print(ci.sanitize(type(error).__name__ + ': ' + str(error),
                          ci.private_values(ci.RUNTIME), (ROOT.parent,)), file=sys.stderr)
        raise SystemExit(1)
