import argparse
import os
import re
from subprocess import (
    CalledProcessError,
    call,
    check_output,
)


def _read_version():
    with open(os.path.join('pyproject.toml')) as f:
        m = re.search(r'''version\s*=\s*['"]([^'"]*)['"]''', f.read())
        if m:
            return m.group(1)
        raise ValueError("couldn't find version")


def tag():
    version = _read_version()
    errno = call(['git', 'tag', '--annotate', version, '--message', f'Version {version}'])
    if errno == 0:
        print("!!! Added tag for version %s" % version)
    raise SystemExit(errno)


def release_check():
    try:
        tagged_version = check_output(['git', 'describe', 'HEAD']).decode().strip()
    except CalledProcessError:
        tagged_version = ''
    version = _read_version()

    if tagged_version != version:
        print('### Missing %s tag on release' % version)
        raise SystemExit(1)

    current_branch = check_output(['git', 'rev-parse', '--abbrev-ref', 'HEAD']).decode().strip()
    if current_branch != 'master':
        print('### Only release from master')
        raise SystemExit(1)

    print("Ok to distribute files")


def main():
    parser = argparse.ArgumentParser(description="Release helper script for iommi")
    parser.add_argument(
        '--version', action='version', version=_read_version(), help="Show program's version number and exit."
    )
    subparsers = parser.add_subparsers(title='subcommands', description='Available subcommands', dest='command')
    subparsers.add_parser('tag', help="Set version tag in git")
    subparsers.add_parser('release-check', help="Verify that tag and version info correspond.")
    args = parser.parse_args()

    if args.command == 'tag':
        tag()
    elif args.command == 'release-check':
        release_check()
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
