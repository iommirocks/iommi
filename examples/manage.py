#!/usr/bin/env python
import os
import sys
from os.path import dirname, join, abspath

sys.path.append(join(dirname(dirname(abspath(__file__))), 'lib'))

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "examples.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
