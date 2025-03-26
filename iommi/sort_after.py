from collections import defaultdict

from iommi.base import items

try:
    from tri_declarative import LAST
except ImportError:
    LAST = object()


class SortAfterException(Exception):
    pass


def sort_after(d):
    unmoved = []
    to_be_moved_by_index = []
    to_be_moved_by_name = defaultdict(list)
    to_be_moved_by_name_before = defaultdict(list)
    to_be_moved_last = []
    for x in items(d):
        after = getattr(x[1], 'after', None)
        if after is None:
            unmoved.append(x)
        elif after is LAST:
            to_be_moved_last.append(x)
        elif isinstance(after, int):
            to_be_moved_by_index.append(x)
        else:
            a = x[1].after
            if a.startswith('>'):
                a = a[1:]
            elif a.startswith('<'):
                a = a[1:]
                to_be_moved_by_name_before[a].append(x)
                continue
            to_be_moved_by_name[a].append(x)

    if len(unmoved) == len(d):
        return d

    to_be_moved_by_index = sorted(
        to_be_moved_by_index, key=lambda x: x[1].after
    )  # pragma: no mutate (infinite loop when x.after changed to None, but if changed to a number manually it exposed a missing test)

    def place(x):
        for y in to_be_moved_by_name_before.pop(x[0], []):
            yield from place(y)
        yield x
        for y in to_be_moved_by_name.pop(x[0], []):
            yield from place(y)

    def traverse():
        count = 0  # pragma: no mutate
        while unmoved or to_be_moved_by_index:
            while to_be_moved_by_index:
                next_to_be_moved_by_index = to_be_moved_by_index[0]

                next_by_position_index = next_to_be_moved_by_index[1].after
                if (
                    unmoved and count < next_by_position_index
                ):  # pragma: no mutate (infinite loop when mutating < to <=)
                    break  # pragma: no mutate (infinite loop when mutated to continue)

                for x in place(next_to_be_moved_by_index):
                    yield x
                    count += 1  # pragma: no mutate

                to_be_moved_by_index.pop(0)

            if unmoved:
                next_unmoved_and_its_children = place(unmoved.pop(0))
                for x in next_unmoved_and_its_children:
                    yield x
                    count += 1  # pragma: no mutate

        for x in to_be_moved_last:
            yield from place(x)

    result = list(traverse())

    if to_be_moved_by_name:
        available_names = "\n    ".join(sorted(list(d.keys())))
        raise SortAfterException(
            f'Tried to order after {", ".join(sorted(to_be_moved_by_name.keys()))} '
            f'but {"that key does" if len(to_be_moved_by_name) == 1 else "those keys do"} '
            f'not exist.\nAvailable names:\n    {available_names}'
        )

    if to_be_moved_by_name_before:
        available_names = "\n    ".join(sorted(list(d.keys())))
        raise SortAfterException(
            f'Tried to order before {", ".join(sorted(to_be_moved_by_name_before.keys()))} '
            f'but {"that key does" if len(to_be_moved_by_name_before) == 1 else "those keys do"} '
            f'not exist.\nAvailable names:\n    {available_names}'
        )

    d.clear()
    d.update(dict(result))
    return d
