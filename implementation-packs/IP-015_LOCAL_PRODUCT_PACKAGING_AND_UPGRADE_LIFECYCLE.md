# IP-015 — Local Product Packaging and Upgrade Lifecycle

## Delivered reference slice

The package uses the existing Poetry product definition and `pm` entry point.
This pack supplies the missing operator lifecycle: isolated install, local
private-state boundary, backup before migration, validation after upgrade, and
explicit recovery.

## Limits

This pack does not publish a package, alter a live database, create a backup,
or transfer configuration. Those are local operator actions requiring the
relevant environment authority.
