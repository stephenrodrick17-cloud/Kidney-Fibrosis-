# NRM2 Stage 5 KPMP Descriptor Workbook Audit

**Report date:** 2026-11-18
**Status:** STOPPED BEFORE WORKBOOK INSPECTION
**Label:** EXPLORATORY, NOT CONFIRMATORY. WORKBOOK-CONTENT VALUES NOT VERIFIED.

## Retrieval result

Target workbook:

- `KPMP TIV Descriptor Scores 10.12.2026.xlsx`
- Repository file UUID: `06f24766-f09c-4dea-a858-53b14965a562`
- Package UUID: `a7eb92af-678b-413e-8f06-2948af1a2f10`
- Repository size: `468577` bytes

The official repository download endpoint was attempted through the browser:

`https://atlas.kpmp.org/api/v1/file/download/a7eb92af-678b-413e-8f06-2948af1a2f10/06f24766-f09c-4dea-a858-53b14965a562_KPMP%20TIV%20Descriptor%20Scores%2010.12.2026.xlsx`

The browser reported `net::ERR_ABORTED` while starting the download and no workbook file persisted under `D:\patent\stage_NRM2\data\`. A previous `curl.exe` attempt stopped at certificate verification and was not repeated with TLS verification disabled.

No TLS verification bypass was attempted.

## Inspection status

Because the workbook was not retrieved, it was not possible to inspect worksheet names, column headers, records, participant IDs, specimen IDs, slide IDs or pathology descriptors.

No workbook content was read.

## Five overlapping participants

The Stage 4 output identified these five Healthy Reference participants in descriptor repository metadata:

- `164-8`
- `164-12`
- `164-17`
- `164-21`
- `164-22`

The following cannot be established:

- Whether an interstitial fibrosis descriptor exists
- Whether a tubular atrophy descriptor exists
- Whether cortex or medullary fibrosis is present
- Percentage or severity values
- Pathologist scoring information
- Specimen-level or participant-level association
- Link to a specific TRI WSI
- Fibrosis relevance

Participant `164-6` is not in the descriptor repository-ID list.

## Other open TRI participants

The repository inventory contains 666 unique open TRI participants. The descriptor repository metadata lists 426 participant IDs, but actual workbook values and relationships remain NOT VERIFIED. No participant can be promoted to a workbook-confirmed fibrosis label.

## Severity coverage

Severity classification is unavailable. No no/minimal, mild, moderate or severe groups were created because there is no inspected workbook value or official local severity definition.

## Download and execution status

No WSI file was downloaded.
No fibrosis model was run or processed.
No artificial pathology label was created.
No workbook contents were fabricated.
No TLS verification or access control was bypassed.
