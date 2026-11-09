# Airport terminal digital twin

An OpenUSD airport concourse driven by Unity Catalog, Delta, and MLflow. Eight
gates and two shared zones; deterministic baseline and `delay_A4` scenarios.

## Current status

Live platform discovery is complete. M0's separate Python 3.11 Spark environment
is being built; airport M1 is gated on its live contracts. Implementation and
validation results will be recorded per milestone. No remote deployment has
been attempted.

- [Verified local platform](docs/LOCAL_PLATFORM.md)
- [Parity and adapters](docs/PARITY.md)
- [Platform requests](docs/PLATFORM_ASKS.md)
- [Decisions](docs/DECISIONS.md)

The adjacent LocalUnityCatalog checkout owns the local compute environment. Its
existing Python 3.12 RAPIDS service remains separate and unchanged. Airport code
will run on Python 3.11 without GPU-specific imports. There is no side database.
