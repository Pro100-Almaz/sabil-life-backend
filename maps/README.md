# Self-hosted Maps

This directory is mounted read-only into the production `tileserver` container.

Expected local files:

- `data/qatar.pmtiles` - Qatar PMTiles extract, not committed to git.
- `styles/protomaps-light.json` - generated Protomaps MapLibre style JSON.

Download/extract Qatar from a current Protomaps daily build:

```bash
mkdir -p maps/data maps/styles
docker run --rm -v "$PWD/maps/data:/data" protomaps/go-pmtiles \
  extract "https://build.protomaps.com/YYYYMMDD.pmtiles" \
  /data/qatar.pmtiles \
  --bbox=50.70,24.45,52.05,26.25
```

Generate the style JSON from https://maps.protomaps.com using "Get style JSON",
save it as `maps/styles/protomaps-light.json`, and point its `protomaps`
source at the local tileset:

```json
"url": "pmtiles://qatar.pmtiles"
```

The public raster tile URL exposed through Caddy is:

```text
https://api.sabil-life.com/maps/styles/light/{z}/{x}/{y}.png
```
