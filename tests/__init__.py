from datetime import datetime

import freezegun

# Initialize freezegun to avoid freezegun being reinitialized which is expensive
initialize_freezegun = freezegun.freeze_time(datetime(2021, 1, 1))
initialize_freezegun.start()
