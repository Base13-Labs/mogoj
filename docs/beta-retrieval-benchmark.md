# Beta retrieval benchmark

Mogoj compares three local retrieval strategies: all Markdown injected as context, all files containing a literal keyword, and ranked SQLite FTS5/BM25 results assembled progressively under a fixed budget.

Run against a real store:

```bash
python3 benchmarks/retrieval_benchmark.py --root ~/.mogoj \
  --query "current project priorities" --query "recent decisions" \
  --budget-tokens 1200
```

The JSON output publishes character counts, estimated tokens, result counts, and whether every progressive response stayed within budget. The beta's deterministic token estimate is `ceil(characters / 4)`; it intentionally does not claim provider-specific tokenizer precision.

On the bundled two-document migration fixture, querying `migration` with a 120-token budget produces a 245-character progressive packet (~62 estimated tokens), versus 108 characters for naive full injection and 62 for literal-keyword injection. Tiny fixtures can make naive injection smaller; progressive retrieval is designed for stores that grow beyond a model's context window. Quality is inspectable through stable `path:Lx-Ly` citations, while relevance comes from FTS5/BM25 order plus a bounded recency bonus.

Session-start retrieval defaults to at most 1,200 estimated tokens, eight distinct documents, one snippet per document, and no full documents. Full content is included only with `--full` and still cannot exceed the budget.
