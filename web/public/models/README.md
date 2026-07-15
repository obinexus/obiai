# U Agentic Model Artifacts

`obi-uagentic-0.1.1.pkl` is the current trusted local Python pickle object
loaded by the U backend and served by Vite as a static artifact.
(`obi-uagentic-0.1.0.pkl` is the retained previous version; the loader
rebuilds routing from code if it ever encounters a stale artifact.)

The pickle contains compact model state only:

- intent routes (scored keyword/phrase matching + tool routing:
  system clock, weather API, web retrieval, vision classifier)
- compact concept cards for OBI philosophy, Unbiased AI, and
  prompt-free cognition
- source fingerprints and page counts
- the model/data separation contract

Raw PDFs, transcripts, image pages, camera frames, and audio are not copied
into this directory. Seed datasets and manifests are generated under
`ml/data/uagentic/` (gitignored) by `ml/scripts/build_uagentic_dataset.py`;
the artifact itself is rebuilt by `ml/scripts/build_uagentic_pickle.py` and
evaluated by `ml/scripts/eval_uagentic.py`.
