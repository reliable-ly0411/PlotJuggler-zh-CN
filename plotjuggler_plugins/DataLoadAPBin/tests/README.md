# Synthetic fixtures

These fixtures were generated for this fork. No flight recordings, positions,
hardware identifiers or user logs are included. The data format is ArduPilot
DataFlash, not MAVLink telemetry.

synthetic.BIN: FMT, FMTU, UNIT, MULT, three byte instances (0, 1, 200),
TimeUS in microseconds, and a 0.01 field multiplier.
second.BIN: reuses the same message ID with a different schema and no FMTU.
invalid.BIN: truncated input, which must fail without producing samples.
