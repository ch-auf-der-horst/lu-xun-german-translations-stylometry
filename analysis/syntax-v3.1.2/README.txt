Syntax analysis 3.1.2 — public preparation

The computation matches the manuscript v3.3 syntax method. Public attachment edits use token hashes instead of lexical strings; this changes the validation representation, not the token/head decisions. The full sentence field and quotation-bearing edit explanations are omitted.

results/full_results.json and register_results.json are unchanged. results/sentence_metrics.json provides counts and depths for all 2,404 sentences without source text. Source files are not distributed. See the root REPRODUCTION.txt for hash verification and private recalculation.

test_pipeline.py contains constructed examples. The one source-quotation test has been replaced with a constructed sentence testing the same OCR repair and offset preservation.
