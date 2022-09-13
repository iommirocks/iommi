class SyntheticCode:
    def __init__(self, co_filename, co_name):
        self.co_filename = co_filename
        self.co_name = co_name
        self.co_firstlineno = 0
        self.co_argcount = 0
        self.co_flags = 0
        self.co_varnames = []


class SyntheticFrame:
    def __init__(self, *, filename, function, f_globals, f_locals, f_lineno, f_back=None):
        self.f_code = SyntheticCode(filename, function)
        self.f_globals = f_globals
        self.f_locals = f_locals
        self.f_back = f_back
        self.f_lineno = f_lineno


class SyntheticTraceback:
    def __init__(self, frames, line_nums):
        assert len(frames) == len(line_nums)
        self._frames = frames
        self._line_nums = line_nums
        self.tb_frame = frames[0]
        self.tb_lineno = line_nums[0]
        self.tb_lasti = -1

    @property
    def tb_next(self):
        if len(self._frames) > 1:
            return SyntheticTraceback(self._frames[1:], self._line_nums[1:])

    def __iter__(self):
        # This is a hack to make pytest not fail on iterating over synthetic tracebacks
        # noinspection PyUnresolvedReferences
        from _pytest._code import TracebackEntry

        cur_ = self
        while cur_ is not None:
            yield TracebackEntry(cur_, excinfo=None)
            cur_ = cur_.tb_next


class SyntheticException(Exception):
    def __init__(self, tb):
        frames = []
        line_numbers = []
        for f in tb:
            frames.append(SyntheticFrame(**f))
            line_numbers.append(f['f_lineno'])

        tb = SyntheticTraceback(frames, line_numbers)

        self._tb = tb
        super().__init__()

    @property
    def __traceback__(self):
        return self._tb

    @__traceback__.setter
    def __traceback__(self, value):
        self._tb = value
