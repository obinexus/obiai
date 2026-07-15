# U Agentic Model Artifacts

`obi-uagentic-0.1.0.pkl` is a trusted local Python pickle object loaded by the
U backend and served by Vite as a static artifact.

The pickle contains compact model state only:

- source fingerprints and page counts
- compact concept cards for U chat behavior
- the model/data separation contract

Raw PDFs, transcripts, image pages, camera frames, and audio are not copied into
this directory. The local source manifest is generated under
`ml/data/uagentic/source_manifest.json`, which is intentionally gitignored.
