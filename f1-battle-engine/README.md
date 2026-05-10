# F1 Battle Engine Pro

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![FastF1](https://img.shields.io/badge/FastF1-3.0+-red.svg)
![Streamlit](https://img.shields.io/badge/UI-Streamlit_|_Apple_Design-black.svg)
![Status](https://img.shields.io/badge/Status-Active_Development-brightgreen.svg)

> **A high-fidelity, high-performance telemetry analysis engine for Formula 1 racing. Built to process, interpolate, and visualize multi-driver data streams with millimeter precision.**

---

## System Overview
*(**Note to Developer:** Add a GIF or high-res screenshot of the dark-mode Apple UI here!)*
`![Dashboard Preview](docs/dashboard-preview.gif)`

The **F1 Battle Engine** is an advanced telemetry dashboard designed to mimic professional pit-wall software. By pulling raw, high-frequency data from official F1 timing transponders, this system allows users to compare the exact racing lines, braking points, and acceleration profiles of any two drivers on the grid.

### The Engineering Problem
Comparing two F1 drivers isn't as simple as overlaying two graphs. Driver A might complete a lap in 80 seconds, while Driver B takes 82 seconds. Because their speeds differ, their data points do not align in time. 

**The Solution:** This engine utilizes **Distance-Based Linear Interpolation**. We strip away the element of time and force both data streams onto a unified, 1-meter master spatial grid. This allows for an exact, meter-by-meter comparison of who is braking later and accelerating harder.

---

## Core Features

* **Apple-Inspired Architecture:** A custom "Glassmorphism" UI featuring frosted glass, Bento Box layouts, and high-contrast dark mode aesthetics.
* **Spatial Interpolation Engine:** Aligns asynchronous telemetry streams onto a standardized distance vector.
* **Time-Delta Matrix:** Calculates the exact cumulative time gained or lost at every micro-sector of the circuit.
* **Dynamic Grid Injection:** Fetches live data for any specific track, year, and driver combination without hardcoded parameters.

---

## The Physics & Mathematics

This application goes beyond raw API fetching by deriving physical forces that are not natively provided by the F1 data stream.

### Longitudinal G-Force Derivation
We calculate the longitudinal G-force ($G_x$) representing acceleration and braking forces by taking the derivative of velocity with respect to time, normalized against standard gravity ($g = 9.81 m/s^2$):

$$G_x = \frac{1}{g} \frac{dv}{dt}$$

### Spatial Data Alignment
To compare Driver 1 ($S_1$) and Driver 2 ($S_2$), we define a master distance array ($D_{master}$) and interpolate both speed arrays:

$$S_1(d) = S_1(d_{prev}) + (d - d_{prev}) \frac{S_1(d_{next}) - S_1(d_{prev})}{d_{next} - d_{prev}}$$

---

## Tech Stack
* **Backend Logic:** Python 3, Pandas, NumPy (Vectorized operations for high-speed calculation).
* **Data Ingestion:** `fastf1` (Official F1 Live Timing API).
* **Frontend UI:** Streamlit, Custom CSS injection.
* **Visualization:** Plotly Graph Objects (Interactive, transparent-background charts).

---

## Quick Start Guide

You don't need to be an engineer to run this on your machine. Just follow these steps:

### 1. Clone the Repository
```bash
git clone [https://github.com/yourusername/f1-battle-engine.git](https://github.com/yourusername/f1-battle-engine.git)
cd f1-battle-engine