# CHINAPAL TecDoc-grade Chinese OEM Parts Catalogue

Premium web catalogue for Chinese cars, utilitaires, trucks and heavy trucks.

## What this is

A searchable buyer/supplier intelligence interface built from the extracted catalogue package in:

`C:\Users\PC\Desktop\byd seal u`

Source data is transformed into:

- OE/OEM searchable master catalogue
- brand/model filters
- part system groups
- evidence/confidence grading
- source file/page traceability
- Morocco compatibility and supplier RFQ questions
- CSV export from filtered selections

## Evidence rule

No fake OEMs. If a reference is not visible in source material, the catalogue marks it as RFQ / verification required.

## Deployment

Built with Vite + React. Production build:

```bash
npm install
npm run build
```

Vercel serves the `dist/` output automatically.
