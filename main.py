import fastf1
from fastf1 import plotting
import matplotlib.pyplot as plt
import os

# 1. Enable Team Colors & Caching
plotting.setup_mpl()
if not os.path.exists('cache'):
    os.makedirs('cache')
fastf1.Cache.enable_cache('cache')

# 2. Load the Session (2024 Saudi Arabian GP Qualifying)
session = fastf1.get_session(2024, 'Saudi Arabia', 'Q')
session.load()

# 3. Get the Fastest Lap for Max Verstappen (VER)
fastest_lap = session.laps.pick_driver('VER').pick_fastest()
telemetry = fastest_lap.get_telemetry().add_distance()

# 4. Plotting the Speed Trace
plt.figure(figsize=(10, 5))
plt.plot(telemetry['Distance'], telemetry['Speed'], color='cyan', label='VER Speed (km/h)')
plt.title("Verstappen Telemetry - Saudi Arabia 2024")
plt.xlabel("Distance (m)")
plt.ylabel("Speed (km/h)")
plt.legend()
plt.show()