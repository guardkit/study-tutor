# demo_history — a crafted fixture corpus (second-subject seam proof)

Every word under this directory was written for this test. Nothing here is copied from a
publisher, an exam board, a textbook, or any other source: the "Ashwood Charter" and the
county of Ashwood are inventions, so the fixture carries no redistribution question.

The tree is the four-folder corpus contract
(`study_tutor.knowledge.corpus.SOURCE_TYPE_FOLDERS`) for the subject `demo_history`:

```
primary_text/            the invented source document (chapter-structured, so the
                         citation-anchor inferer produces NovelCitationAnchors)
secondary_study_guide/   revision notes about it — plus one deliberately-named file
                         that the AQA assessment-material refusal regex must refuse
secondary_critical/      a critical commentary
context_historical/      a timeline
```

`tests/unit/knowledge/test_second_subject_proof.py` copies this tree into a temp
directory and runs the real `scripts/ingest_corpus.py` over the copy. Editing any file
here changes the chunk counts the proof pins — re-run the module and update the
`EXPECTED_*` constants together with the edit.
