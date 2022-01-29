from datetime import datetime

import freezegun

# Initialize freezegun to avoid freezegun being reinitialized which is expensive
initialize_freezegun = freezegun.freeze_time(datetime(1948, 2, 19))  # Tony Iommis birth
initialize_freezegun.start()
