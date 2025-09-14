```mermaid
flowchart LR
  start([Start])
  policy[Policy Node]
  rag[RAG Tool - Qdrant]
  web[Web Tool - Tavily]
  synth[Synthesis]
  finish([End])

  start --> policy
  policy --> rag

  rag -->|no hits| web
  rag -->|hits & web augment keyword| web
  rag -->|hits| synth

  web --> synth
  synth --> finish