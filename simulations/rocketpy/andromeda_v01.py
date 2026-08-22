"""Preliminary RocketPy 6-DOF model for Andromeda v0.1.

All dimensions and mass properties are provisional.  The coordinate system has
its origin at the tail/nozzle plane and points forward toward the nose.
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
from rocketpy import Environment, Flight, Rocket, SolidMotor


OUTPUT_FILE = Path(__file__).with_name("andromeda_v01_results.json")
THRUST_CURVE = np.array(
    [
        [0.00, 0.0],
        [0.05, 893.0],
        [0.50, 798.0],
        [1.00, 739.0],
        [1.50, 659.0],
        [2.00, 586.0],
        [2.50, 513.0],
        [2.97, 417.0],
        [3.20, 225.0],
        [3.47, 67.0],
        [3.59, 0.0],
    ]
)

# Vehicle baseline
LENGTH = 2.150
RADIUS = 0.060
RAIL_LENGTH = 4.0
LOWER_RAIL_BUTTON_FROM_TAIL = 0.450
UPPER_RAIL_BUTTON_FROM_TAIL = 1.250


@dataclass(frozen=True)
class AirframeModule:
    """Preliminary module envelope and roll-up mass properties."""

    name: str
    start_from_tail_m: float
    end_from_tail_m: float
    mass_kg: float
    cg_from_tail_m: float

    @property
    def length_m(self) -> float:
        return self.end_from_tail_m - self.start_from_tail_m


# Legacy-inspired modular arrangement, retained as a single powered stage.
# Module masses include their allocated airframe, interfaces, and installed
# hardware. They are provisional roll-up values, not measured component masses.
MODULE_LAYOUT = (
    AirframeModule("Propulsion", 0.000, 0.600, 2.170, 0.380),
    AirframeModule("Power", 0.600, 0.800, 0.550, 0.700),
    AirframeModule("Avionics", 0.800, 1.050, 0.700, 0.925),
    AirframeModule("Recovery", 1.050, 1.600, 1.400, 1.325),
    AirframeModule("Nose", 1.600, 2.150, 0.500, 1.830),
)
VEHICLE_MASS_WITHOUT_MOTOR = sum(module.mass_kg for module in MODULE_LAYOUT)
DRY_VEHICLE_CG_FROM_TAIL = (
    sum(module.mass_kg * module.cg_from_tail_m for module in MODULE_LAYOUT)
    / VEHICLE_MASS_WITHOUT_MOTOR
)

if not math.isclose(VEHICLE_MASS_WITHOUT_MOTOR, 5.320, abs_tol=1e-9):
    raise ValueError("Module mass budget must total 5.320 kg without the motor")
if not math.isclose(MODULE_LAYOUT[-1].end_from_tail_m, LENGTH, abs_tol=1e-9):
    raise ValueError("Module envelopes must end at the 2.150 m nose tip")
for forward, aft in zip(MODULE_LAYOUT, MODULE_LAYOUT[1:]):
    if not math.isclose(forward.end_from_tail_m, aft.start_from_tail_m, abs_tol=1e-9):
        raise ValueError("Module envelopes must be contiguous")

# The handbook gives 1.68 kg loaded and 0.65 kg after burnout.
MOTOR_DRY_MASS = 0.650
PROPELLANT_MASS = 1.030


def isa_like_profiles(elevation: float = 200.0):
    """Return provisional UAE-winter pressure and temperature profiles."""

    altitude = np.array([0.0, elevation, 500.0, 1000.0, 2000.0, 3000.0, 5000.0])
    launch_temperature = 293.15  # 20 deg C at the provisional launch elevation
    temperature = launch_temperature - 0.0065 * (altitude - elevation)
    launch_pressure = 98_945.0
    pressure = launch_pressure * (temperature / launch_temperature) ** 5.25588
    return np.column_stack((altitude, pressure)), np.column_stack(
        (altitude, temperature)
    )


def build_environment() -> Environment:
    pressure, temperature = isa_like_profiles()
    environment = Environment(
        latitude=24.0,
        longitude=54.0,
        elevation=200.0,
        max_expected_height=5000.0,
    )
    environment.set_atmospheric_model(
        type="custom_atmosphere",
        pressure=pressure,
        temperature=temperature,
        wind_u=5.0,
        wind_v=0.0,
    )
    return environment


def build_motor() -> SolidMotor:
    grain_number = 5
    grain_density = 1700.0
    grain_outer_radius = 0.025
    grain_height = 0.075
    grain_inner_radius = math.sqrt(
        grain_outer_radius**2
        - PROPELLANT_MASS
        / (grain_number * grain_density * math.pi * grain_height)
    )

    return SolidMotor(
        # Use the handbook points directly because RocketPy's .eng importer
        # requires the zero-time point to be omitted, unlike our shared file.
        thrust_source=THRUST_CURVE,
        dry_mass=MOTOR_DRY_MASS,
        dry_inertia=(0.0130, 0.0130, 0.00024),
        nozzle_radius=0.018,
        throat_radius=0.008,
        grain_number=grain_number,
        grain_density=grain_density,
        grain_outer_radius=grain_outer_radius,
        grain_initial_inner_radius=grain_inner_radius,
        grain_initial_height=grain_height,
        grain_separation=0.003,
        grains_center_of_mass_position=0.250,
        center_of_dry_mass_position=0.240,
        nozzle_position=0.0,
        burn_time=(0.0, 3.59),
        interpolation_method="linear",
        coordinate_system_orientation="nozzle_to_combustion_chamber",
    )


def main_trigger(_pressure: float, height: float, state: list[float]) -> bool:
    """Deploy the main below 400 m AGL only while descending."""

    vertical_velocity = state[5]
    return vertical_velocity < 0 and height <= 400.0


def build_rocket(motor: SolidMotor) -> Rocket:
    # Preliminary subsonic drag curves. Replace with RASAero/CFD or test data.
    mach = np.array([0.0, 0.3, 0.6, 0.8, 0.95, 1.05, 1.2, 2.0])
    power_off_cd = np.array([0.44, 0.42, 0.43, 0.48, 0.65, 0.72, 0.62, 0.48])
    power_on_cd = np.array([0.47, 0.45, 0.46, 0.51, 0.68, 0.75, 0.65, 0.51])

    def power_off_drag(mach_number):
        return float(np.interp(float(np.real(mach_number)), mach, power_off_cd))

    def power_on_drag(mach_number):
        return float(np.interp(float(np.real(mach_number)), mach, power_on_cd))

    rocket = Rocket(
        radius=RADIUS,
        mass=VEHICLE_MASS_WITHOUT_MOTOR,
        inertia=(1.80, 1.80, 0.025),
        power_off_drag=power_off_drag,
        power_on_drag=power_on_drag,
        center_of_mass_without_motor=DRY_VEHICLE_CG_FROM_TAIL,
        coordinate_system_orientation="tail_to_nose",
    )
    rocket.add_motor(motor, position=0.0)
    rocket.add_nose(length=0.550, kind="von karman", position=LENGTH)
    rocket.add_trapezoidal_fins(
        n=4,
        root_chord=0.300,
        tip_chord=0.120,
        span=0.140,
        position=0.320,
        sweep_length=0.140,
    )
    rocket.set_rail_buttons(
        upper_button_position=UPPER_RAIL_BUTTON_FROM_TAIL,
        lower_button_position=LOWER_RAIL_BUTTON_FROM_TAIL,
        angular_position=45.0,
    )

    drogue_cd_s = math.pi * 0.55**2 / 4
    main_cd_s = math.pi * 1.55**2 / 4
    rocket.add_parachute(
        "Drogue",
        cd_s=drogue_cd_s,
        trigger="apogee",
        sampling_rate=100,
        lag=0.0,
        radius=0.55 / 2,
        drag_coefficient=1.0,
    )
    rocket.add_parachute(
        "Main",
        cd_s=main_cd_s,
        trigger=main_trigger,
        sampling_rate=100,
        lag=0.0,
        radius=1.55 / 2,
        drag_coefficient=1.0,
    )
    return rocket


def scalar(function, time: float) -> float:
    """Evaluate a RocketPy Function and return a JSON-friendly float."""

    return float(function(time))


def run() -> dict[str, object]:
    environment = build_environment()
    motor = build_motor()
    rocket = build_rocket(motor)
    flight = Flight(
        rocket=rocket,
        environment=environment,
        rail_length=RAIL_LENGTH,
        inclination=90.0,
        heading=90.0,
        max_time=300.0,
        max_time_step=0.05,
        rtol=1e-6,
        verbose=False,
        name="Andromeda v0.1 UAE winter nominal",
    )

    launch_mass = scalar(rocket.total_mass, 0.0)
    parachute_events = {
        parachute.name: float(event_time)
        for event_time, parachute in flight.parachute_events
    }
    drogue_time = parachute_events["Drogue"]
    main_time = parachute_events["Main"]
    result = {
        "launch_mass_kg": launch_mass,
        "dry_vehicle_mass_kg": VEHICLE_MASS_WITHOUT_MOTOR,
        "dry_vehicle_cg_from_tail_m": DRY_VEHICLE_CG_FROM_TAIL,
        "module_layout": [
            {**asdict(module), "length_m": round(module.length_m, 3)}
            for module in MODULE_LAYOUT
        ],
        "rail_length_m": RAIL_LENGTH,
        "rail_button_span_m": (
            UPPER_RAIL_BUTTON_FROM_TAIL - LOWER_RAIL_BUTTON_FROM_TAIL
        ),
        "motor_initial_mass_kg": scalar(motor.total_mass, 0.0),
        "motor_total_impulse_ns": float(motor.total_impulse),
        "static_margin_at_ignition_cal": scalar(rocket.static_margin, 0.0),
        "rail_exit_velocity_m_s": float(flight.out_of_rail_velocity),
        "apogee_agl_m": float(flight.apogee - environment.elevation),
        "time_to_apogee_s": float(flight.apogee_time),
        "drogue_trigger_time_s": drogue_time,
        "main_trigger_time_s": main_time,
        "main_trigger_altitude_agl_m": scalar(flight.altitude, main_time),
        "main_trigger_speed_m_s": scalar(flight.speed, main_time),
        "max_speed_m_s": float(flight.max_speed),
        "max_mach": float(flight.max_mach_number),
        "max_acceleration_m_s2": float(flight.max_acceleration),
        "impact_speed_m_s": abs(float(flight.impact_velocity)),
        "impact_distance_m": float(math.hypot(flight.x_impact, flight.y_impact)),
        "flight_time_s": float(flight.t_final),
    }
    OUTPUT_FILE.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
