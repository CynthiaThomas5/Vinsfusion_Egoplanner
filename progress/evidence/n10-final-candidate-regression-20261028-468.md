# N10.6 final candidate regression — #468

## Result

PASS. The final candidate ran 596 unit tests and the required navigation adapter integration and official EGO policy probe. The regression log is SHA-256 `50c27ccf4dd1a47f5ef4fd97303e0bde53806d4dc0b1fcf545c6c314ac36e8f7`.

The frozen acceptance revision 8 replay used the source-covered v3 physical-interval clearance bound from #460. Frozen configuration SHA-256 is `7cf226ee4c471d49fec05f25eede1c9c127cd97fc22f0ae371ba13681d599750`; comparison with the archived draft SHA-256 `9a49da186d970ed9a49eb0fb4fa28b5b23cad9c17198a9563d7d63b0cea3ce63` confirms every field except lifecycle `status` is identical. All 13 required in-scope metrics passed. The optional fault-to-terminal metric remains `INSUFFICIENT` with `required=false`, consistent with user scope #434; it is not evidence that faults are qualified and does not count toward N15.

The replay without the v3 interval bound is preserved separately as an incomplete/failed diagnostic. It was not replaced or hidden; the passing replay is bound to the interval report and the same frozen acceptance configuration.

## Artifacts

- Regression test and integration log: [`artifacts/runs/n10-20261028-468-final-candidate-validation/project-test.log`](../../artifacts/runs/n10-20261028-468-final-candidate-validation/project-test.log)
- Frozen acceptance replay: [`artifacts/reanalysis/n10-20261028-468-frozen-acceptance/n10-acceptance-evaluation-frozen.json`](../../artifacts/reanalysis/n10-20261028-468-frozen-acceptance/n10-acceptance-evaluation-frozen.json)
- Physical-interval clearance basis: [`artifacts/reanalysis/n10-20261028-460-component-geometry/n10-interval-clearance-bound.json`](../../artifacts/reanalysis/n10-20261028-460-component-geometry/n10-interval-clearance-bound.json)

This is N10 candidate regression evidence. Formal N11–N16 runs remain separate and unstarted.
