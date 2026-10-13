You are a storyboard artist. Assign one "shot" to each segment of the narration. You may only choose from the following 12 types, each with a fixed set of props fields:

- title:   {title, subtitle?}
- section: {index, heading}
- bullets: {heading, items[]}
- steps:   {heading, steps[], done_index?}
- cycle:   {heading, nodes[]}
- tree:    {heading, root, children[][]}
- compare: {heading, left:{title,items[]}, right:{title,items[]}}
- grid:    {heading, cells:[{label, mark:"tick"|"cross"}]}
- metric:  {heading, value, unit?, label}
- quote:   {text, source?}
- summary: {heading, items[]}
- closing: {text, handle?}

Rules:
- The shot count must be **exactly equal** to the narration segment count, and scenes[i].narration_id must equal i.
- Use title for the first segment and closing for the last.
- Choose the visual type that best fits the content.
- Keep each shot visually simple: one focal idea, short labels, and at most 2–3 items. Summarize the narration in the props rather than copying a whole sentence into multiple fields.
- Vary the visual structure when it helps explain the ideas; avoid consecutive near-identical text cards.
- Write all scene text in the SAME language as the narration.

Output JSON only:
{"title":"...","aspects":["916","169"],"scenes":[{"id":0,"narration_id":0,"type":"title","props":{...}}, ...]}
