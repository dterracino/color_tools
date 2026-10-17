# Vercel badge functions

This directory contains two small, stateless Vercel serverless functions that
generate the dynamic SVG badges displayed in the main project README. They are
deployed with the root [`vercel.json`](../vercel.json) configuration and use
the Color Tools package version pinned in [`requirements.txt`](requirements.txt).

These functions are **not the upcoming Color Tools REST API**. The future REST
API is a separate project surface and is not implemented in this directory.
These endpoints return SVG images rather than a general-purpose JSON API.

## Endpoints

### `GET /api/color_of_day`

Implemented by [`color_of_day.py`](color_of_day.py).

The function loads the default named-color palette, sorts its records by name,
and deterministically selects one color from the current calendar date. Every
request made on the same date selects the same color without requiring stored
state.

The SVG response displays:

- the selected color swatch;
- the formatted color name;
- its hexadecimal color value;
- its RGB components; and
- the current date.

### `GET /api/filament_of_day`

Implemented by [`filament_of_day.py`](filament_of_day.py).

The function loads the default filament database, sorts its records by maker,
material type, and color name, and deterministically selects one filament from
the current calendar date. It uses a filament-specific date seed so its daily
selection is independent of the color endpoint.

The SVG response displays:

- the filament's effective color swatch;
- its color name;
- maker, material type, and optional finish;
- its hexadecimal color value and RGB components; and
- the current date.

For multi-color filaments, the displayed swatch uses the record's
`effective_hex` value.

## Response behavior

Both endpoints:

- accept `GET` requests;
- return `200 OK` with `Content-Type: image/svg+xml; charset=utf-8`;
- send `Cache-Control: public, max-age=3600, s-maxage=3600`;
- send `X-Content-Type-Options: nosniff`;
- require no database, scheduled job, or persistent state; and
- suppress the default `BaseHTTPRequestHandler` request log.

The hourly cache duration is configured both by the functions and by
[`vercel.json`](../vercel.json). More usage and deployment information is
available in the published [badge documentation](../docs/Badges.md).
