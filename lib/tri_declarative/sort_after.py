from collections import defaultdict

LAST = object()


def sort_after(l):
    unmoved = []
    to_be_moved_by_index = []
    to_be_moved_by_name = defaultdict(list)
    to_be_moved_last = []
    for x in l:
        after = getattr(x, 'after', None)
        if after is None:
            unmoved.append(x)
        elif after is LAST:
            to_be_moved_last.append(x)
        elif isinstance(after, int):
            to_be_moved_by_index.append(x)
        else:
            to_be_moved_by_name[x.after].append(x)

    to_be_moved_by_index = sorted(to_be_moved_by_index, key=lambda x: x.after)  # pragma: no mutate (infinite loop when x.after changed to None, but if changed to a number manually it exposed a missing test)

    def place(x):
        yield x
        for y in to_be_moved_by_name.pop(x.name, []):
            for z in place(y):
                yield z

    def traverse():
        count = 0
        while unmoved or to_be_moved_by_index:
            while to_be_moved_by_index:
                next_by_position_index = to_be_moved_by_index[0].after
                if count < next_by_position_index:  # pragma: no mutate (infinite loop when mutating < to <=)
                    break  # pragma: no mutate (infinite loop when mutated to continue)

                objects_with_index_due = place(to_be_moved_by_index.pop(0))
                for x in objects_with_index_due:
                    yield x
                    count += 1  # pragma: no mutate
            if unmoved:
                next_unmoved_and_its_children = place(unmoved.pop(0))
                for x in next_unmoved_and_its_children:
                    yield x
                    count += 1  # pragma: no mutate

        for x in to_be_moved_last:
            for y in place(x):
                yield y

    result = list(traverse())

    if to_be_moved_by_name:
        available_names = "\n   ".join(sorted([x.name for x in l]))
        raise KeyError(f'Tried to order after {", ".join(sorted(to_be_moved_by_name.keys()))} but {"that key does" if len(to_be_moved_by_name) == 1 else "those keys do"} not exist.\nAvailable names:\n    {available_names}')

    return result
