import freezegun

# Initialize freezegun to the current rolling time, to avoid freezegun being reinitialized which is expensive
initialize_freezegun = freezegun.freeze_time(freezegun.api.real_datetime.now(), tick=True)
initialize_freezegun.start()
