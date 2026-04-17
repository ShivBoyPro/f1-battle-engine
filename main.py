import fastf1
from fastf1 import plotting
import matplotlib.pyplot as plt
import os

# 1. Setup - Using the FastF1 dark theme
plotting.setup_mpl(mpl_timedelta_support=True, color_scheme='fastf1')

# 2. Caching - Essential so you don't redownload 100MB every time
if not os.path.exists('cache'):
    os.makedirs('cache')
fastf1.Cache.enable_cache('cache')

# 3. Load Data
print("Loading session data...")
session = fastf1.get_session(2024, 'Saudi Arabia', 'Q')
session.load()

# 4. Extract Verstappen's fastest lap
ver_lap = session.laps.pick_driver('VER').pick_fastest()
# get_telemetry() gives us the raw sensor data (Speed, Throttle, etc.)
# add_distance() converts time-based data into track-position data
telemetry = ver_lap.get_telemetry().add_distance()

# 5. The Plot: Speed vs Distance
fig, ax = plt.subplots(figsize=(10, 5))
ax.plot(telemetry['Distance'], telemetry['Speed'], label='VER Speed (km/h)', color='cyan')
ax.set_xlabel('Distance (m)')
ax.set_ylabel('Speed (km/h)')
ax.set_title('Max Verstappen - Pole Lap - Jeddah 2024')
ax.legend()
plt.show()