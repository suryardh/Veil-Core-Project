# Veil 2.0 — Implementation TODO & Architecture Roadmap

> This file turns `PLAN.md` into an implementation checklist.
>
> **Primary goal:** evolve Veil from a Stella-specific companion into a reusable Character Runtime for persistent roleplay / AI VTuber-style characters.
>
> **Rule:** do not jump to fine-tuning before the runtime has measurable baselines.

---

# 0. How to Use This Roadmap

Each phase should produce a working, testable increment.

Status legend:

- `[ ]` not started
- `[~]` in progress
- `[x]` completed
- `[!]` blocked / needs investigation

Recommended order:

```text
Character
   ↓
State / Relationship
   ↓
Memory
   ↓
Context Pipeline
   ↓
Evaluation
   ↓
LLM abstraction
   ↓
Training experiments
   ↓
Voice / VTuber adapters
```

Do not implement everything at once.

---

# 1. Phase 0 — Baseline & Architecture Audit

## Objective

Understand what Veil already has before replacing anything.

## Tasks

- [ ] Map the current source tree.
- [ ] Identify where Stella-specific assumptions exist.
- [ ] Identify the current `PersonalityCore` responsibilities.
- [ ] Identify current emotion/state persistence.
- [ ] Identify short-term and long-term memory paths.
- [ ] Identify LLM/inference boundaries.
- [ ] Identify tool/cognition boundaries.
- [ ] Run the existing test suite and record the baseline.
- [ ] Record current behavior with a small fixed conversation benchmark.

## Deliverable

Create an architecture note containing:

```text
Current input
    ↓
Emotion?
    ↓
State?
    ↓
Memory?
    ↓
Prompt?
    ↓
LLM
    ↓
Response
```

Then compare it against the target architecture:

```text
User
 ↓
Conversation Coordinator
 ├── Emotion Interpreter
 ├── Relationship/State
 ├── Memory Retrieval
 ├── Character Definition
 ├── Tool/Cognition
 └── Context Builder
          ↓
       LLM Runtime
          ↓
   Response Evaluator
          ↓
       Response
```

---

# 2. Phase 1 — Generic Character System

## Why

Currently Stella should not be the hardcoded identity of the runtime.

The goal is:

```text
Veil
 ├── Character Runtime
 │
 ├── Stella
 ├── ExampleCharacter
 └── UserCharacter
```

A new character should be loadable without editing core runtime code.

## Tasks

- [ ] Define a `CharacterDefinition` model.
- [ ] Define character validation.
- [ ] Create a character loader.
- [ ] Move Stella identity into external character data.
- [ ] Remove Stella-specific imports from generic runtime modules.
- [ ] Define defaults for optional character fields.
- [ ] Add serialization/deserialization tests.
- [ ] Add one second dummy character to prove the abstraction works.

## Suggested structure

```text
characters/
├── loader.py
├── schema.py
├── stella/
│   ├── character.yaml
│   ├── personality.yaml
│   ├── lore.yaml
│   └── rules.yaml
└── example/
    ├── character.yaml
    ├── personality.yaml
    ├── lore.yaml
    └── rules.yaml
```

## Example

```yaml
name: Stella

personality:
  warmth: 0.9
  curiosity: 0.9
  playfulness: 0.8
  empathy: 0.9

speech:
  language: id
  formality: casual
  emoji_level: medium

behavior:
  teasing: true
  proactive: true
```

### Inspiration

SillyTavern uses the concept of a **character card**: a reusable collection of character information/prompts rather than hardcoding one personality into the application. This is directly relevant to Veil's character abstraction. citeturn0search0turn0search7

RisuAI also separates character-card handling from its broader processing/storage systems, which is a useful architectural precedent. citeturn0search4

### What to borrow conceptually

Borrow:

- character-as-data
- import/export-friendly schema
- versioned character definitions
- optional metadata
- lore/world information

Do **not** copy an external project's implementation wholesale. Reimplement the concepts around Veil's own interfaces.

---

# 3. Phase 2 — State & Relationship Engine

## Why

A character's personality should be relatively stable while its emotional condition changes.

Separate:

```text
Character Definition
    = who the character is

Character State
    = how the character feels right now

Relationship State
    = how the character currently relates to the user
```

## Tasks

- [ ] Define `CharacterState`.
- [ ] Define `RelationshipState`.
- [ ] Move state mutation behind a service/interface.
- [ ] Separate state persistence from character definition.
- [ ] Preserve existing decay behavior.
- [ ] Add deterministic transition tests.
- [ ] Add state snapshot/restore.
- [ ] Define bounds for every numeric state.
- [ ] Define what happens when state becomes stale.

## Example

```python
state = CharacterState(
    mood="happy",
    energy=0.75,
    affection=0.62,
    trust=0.80,
)

relationship = RelationshipState(
    familiarity=0.70,
    trust=0.80,
    attachment=0.45,
)
```

Do not make the LLM responsible for storing these values.

---

# 4. Phase 3 — Emotion Interpreter

## Objective

Turn user input into structured signals without coupling the runtime to one implementation.

```text
User message
    ↓
EmotionInterpreter
    ↓
EmotionResult
```

## Example output

```json
{
  "emotion": "joy",
  "valence": 0.82,
  "arousal": 0.63,
  "intent": "social_connection",
  "confidence": 0.91
}
```

## Tasks

- [ ] Define `EmotionResult`.
- [ ] Wrap the existing keyword/rule analyzer behind the interface.
- [ ] Add confidence.
- [ ] Add neutral/unknown fallback.
- [ ] Add deterministic tests.
- [ ] Later benchmark a small classifier.
- [ ] Only later evaluate LLM-assisted emotion interpretation.

## Rule

The runtime should not care whether emotion came from:

```text
rules
small model
LLM
hybrid
```

---

# 5. Phase 4 — Memory 2.0

## Objective

Turn memory into a first-class subsystem rather than an incidental prompt feature.

## Memory model

```text
Memory
├── id
├── type
├── content
├── importance
├── confidence
├── created_at
├── last_accessed_at
├── source
├── tags
└── embedding (optional)
```

## Types

```text
FACT
PREFERENCE
EVENT
RELATIONSHIP
EMOTIONAL
CONVERSATION
LORE
```

## Tasks

- [ ] Define memory schema.
- [ ] Define memory repository interface.
- [ ] Preserve current persistence during migration.
- [ ] Add importance scoring.
- [ ] Add recency scoring.
- [ ] Add retrieval/ranking interface.
- [ ] Add memory deduplication.
- [ ] Add memory update/forget behavior.
- [ ] Add memory tests.
- [ ] Benchmark JSON persistence before moving storage.
- [ ] Move to SQLite when justified.
- [ ] Add embeddings only after lexical/rule retrieval has a baseline.

## Retrieval example

```text
query:
"Do you remember what coffee I like?"

             ↓

MemoryRetriever
   ├── preference matches
   ├── semantic similarity
   ├── recency
   └── importance

             ↓

Top relevant memories
             ↓

Context Builder
```

### Inspiration

RisuAI's architecture explicitly separates memory systems, embeddings, lorebook, model integrations, and chat processing. Its repository structure is a useful example of keeping these concerns distinct. citeturn0search4

SillyTavern's lorebook model also demonstrates an important optimization: contextual information can be activated only when relevant rather than permanently injecting every piece of lore. citeturn0search2

### Design lesson for Veil

Use:

```text
Always-on character identity
+
Relevant dynamic memory
+
Relevant lore
```

instead of:

```text
Everything ever remembered
```

---

# 6. Phase 5 — Context Builder

## Objective

Create one explicit place responsible for deciding what the LLM sees.

## Target

```text
                    ContextBuilder
                         │
       ┌─────────────────┼─────────────────┐
       ↓                 ↓                 ↓
 Character            State             Memories
       │                 │                 │
       └─────────────────┼─────────────────┘
                         ↓
                  Recent Conversation
                         ↓
                    Tool Results
                         ↓
                    User Message
                         ↓
                    Final Context
```

## Tasks

- [ ] Define `ContextRequest`.
- [ ] Define `ContextResult`.
- [ ] Separate system/persona context from dynamic context.
- [ ] Add token budgeting.
- [ ] Add memory ranking.
- [ ] Add optional lore injection.
- [ ] Add context debugging/logging.
- [ ] Add snapshot tests for generated context.
- [ ] Ensure secrets/internal tool details never enter character-facing context.

## Important constraint

Context size is a resource.

A huge permanent character prompt can reduce the room available for conversation history and relevant memories. SillyTavern's documentation explicitly highlights this tradeoff. citeturn0search7

So Veil should eventually track:

```text
context budget
├── character
├── state
├── memories
├── history
├── tools
└── response reserve
```

---

# 7. Phase 6 — Conversation Coordinator

## Objective

Replace an oversized orchestration object with an explicit pipeline.

## Suggested API

```python
result = conversation.process(
    character=stella,
    user_message="Aku hari ini capek banget."
)
```

Internally:

```text
process()
 │
 ├─ interpret emotion
 ├─ update relationship
 ├─ update state
 ├─ retrieve memories
 ├─ execute required tools
 ├─ build context
 ├─ call LLM
 ├─ evaluate response
 └─ persist state/memory
```

## Tasks

- [ ] Introduce coordinator.
- [ ] Extract orchestration from `PersonalityCore`.
- [ ] Keep individual services independently callable.
- [ ] Add pipeline tests.
- [ ] Add structured tracing for each stage.

---

# 8. Phase 7 — LLM Runtime Abstraction

## Objective

Make the model replaceable.

```text
LLMProvider
    ├── LlamaCppProvider
    ├── OpenAICompatibleProvider
    └── FutureProvider
```

## Interface example

```python
class LLMProvider(Protocol):
    def generate(self, request: GenerationRequest) -> GenerationResult:
        ...
```

## Tasks

- [ ] Define provider interface.
- [ ] Wrap current llama.cpp integration.
- [ ] Normalize generation parameters.
- [ ] Normalize errors/timeouts.
- [ ] Add mock provider for tests.
- [ ] Add provider capability metadata.
- [ ] Ensure character/memory/state code knows nothing about provider internals.

---

# 9. Phase 8 — Response Evaluator

## Objective

A character engine should be able to notice when a generated answer violates its own state/personality.

## Evaluation dimensions

```text
Personality consistency
Speech style
Lore consistency
Memory consistency
State consistency
Safety / boundary rules
```

## Example

```json
{
  "personality": 0.91,
  "speech_style": 0.88,
  "lore": 1.0,
  "memory": 0.76,
  "state": 0.93,
  "overall": 0.89,
  "regenerate": false
}
```

## Tasks

- [ ] Define evaluator interface.
- [ ] Start with deterministic checks where possible.
- [ ] Build a small benchmark set.
- [ ] Add model-based evaluation only where useful.
- [ ] Add bounded regeneration.
- [ ] Log evaluation failures.
- [ ] Track regressions across model changes.

---

# 10. Phase 9 — Character Benchmark

## Objective

Stop judging the character only by "this response feels good."

Create repeatable scenarios.

## Benchmark categories

### Personality

```text
User: "Kamu bisa serius sedikit nggak?"
Expected:
- remains recognizably playful/warm
- adapts tone without losing identity
```

### Memory

```text
Turn 1:
User says a persistent preference.

Turn 50:
Ask indirectly about that preference.

Expected:
Relevant memory is retrieved.
```

### Relationship

```text
Repeated positive interactions
        ↓
trust/affection should evolve
```

### State

```text
Low energy
        ↓
response style changes
        ↓
does not rewrite core personality
```

### Lore

```text
User asks about known character/world facts.
Expected:
No contradiction with character definition.
```

## Tasks

- [ ] Create benchmark JSON/YAML format.
- [ ] Add 20–50 initial scenarios.
- [ ] Add automated scoring where practical.
- [ ] Record baseline before model tuning.
- [ ] Re-run after architecture changes.

---

# 11. Phase 10 — Fine-Tuning Experiments

## Do not start this phase early.

Only begin after the runtime has a measurable baseline.

Compare:

```text
A: Base model + prompt

B: Base model + Character Runtime

C: LoRA/SFT model + Character Runtime
```

Measure:

```text
personality
style
lore
memory
state
response quality
latency
VRAM/RAM
```

## Tasks

- [ ] Freeze benchmark dataset.
- [ ] Build training dataset pipeline.
- [ ] Remove duplicated/low-quality samples.
- [ ] Create SFT baseline.
- [ ] Test LoRA.
- [ ] Compare against untuned model.
- [ ] Record whether tuning actually improves results.
- [ ] Keep adapters outside core runtime.

## CPT

Only investigate CPT if the project has a sufficiently large and coherent domain/style corpus.

Do not use CPT merely because "AI character projects usually tune models."

---

# 12. Phase 11 — Voice

## Tasks

- [ ] Define TTS adapter.
- [ ] Define STT adapter.
- [ ] Add voice event model.
- [ ] Map emotion/intensity to voice parameters.
- [ ] Support interruption/cancellation.
- [ ] Keep voice outside the core conversation engine.

Target:

```text
LLM Response
    ↓
Emotion / Expression Metadata
    ↓
TTS Adapter
    ↓
Audio
```

---

# 13. Phase 12 — VTuber Runtime

## Tasks

- [ ] Define expression/action event schema.
- [ ] Add avatar adapter interface.
- [ ] Prototype Live2D adapter.
- [ ] Prototype VRM adapter.
- [ ] Map emotional state to expressions.
- [ ] Add idle behavior.
- [ ] Add initiative events.
- [ ] Keep avatar failures isolated from conversation.

Example:

```json
{
  "emotion": "embarrassed",
  "intensity": 0.72,
  "expression": "blush",
  "action": "look_away"
}
```

---

# 14. Phase 13 — Platform Adapters

Potential adapters:

```text
Veil Core
 ├── CLI
 ├── Web
 ├── Discord
 ├── Telegram
 ├── TTS
 ├── Live2D
 └── VRM
```

## Tasks

- [ ] Keep platform adapters thin.
- [ ] Do not duplicate character logic per platform.
- [ ] Normalize incoming messages.
- [ ] Normalize outgoing responses/events.

---

# 15. Similar Projects — What We Should Learn From

## SillyTavern

Useful concepts:

- character cards
- persona separation
- lore/world info
- context budgeting
- prompt manager
- provider flexibility

SillyTavern treats character definitions as reusable data and emphasizes context allocation because permanent character information competes with conversation history for the model's context window. citeturn0search0turn0search7

**Veil adaptation:**

```text
Character Card
      ↓
CharacterDefinition
      ↓
ContextBuilder
```

Do not copy its entire frontend/prompt architecture.

Official repository/docs:
https://github.com/SillyTavern/SillyTavern
https://docs.sillytavern.app/

## RisuAI

Useful concepts:

- character cards
- lorebook
- long-term memory
- multiple model providers
- embeddings
- plugins
- TTS
- emotion presentation

RisuAI's current architecture separates storage, processing, memory, model integrations, embeddings, lorebook, and adapters, which is close to the direction Veil needs. citeturn0search4turn0search5

**Veil adaptation:**

```text
Storage
   ↓
Memory
   ↓
Processing
   ↓
Model
   ↓
Presentation adapters
```

Official repository:
https://github.com/kwaroran/Risuai

## Character Card Ecosystem

Character cards are worth supporting eventually because they provide a portable way to represent character identity and prompt-oriented metadata. The V2 specification includes fields such as system prompt, post-history instructions, alternate greetings, character book, tags, creator metadata, and extensions. citeturn0search6

**Future Veil feature:**

```text
Veil CharacterDefinition
       ↕
Character Card Import/Export
```

This should be an adapter, not the internal runtime schema.

---

# 16. Code Reuse Policy

We can absolutely study similar open-source projects and reproduce useful ideas.

However:

- [ ] Prefer architecture/pattern inspiration over copying large code sections.
- [ ] Check the repository license before reusing implementation code.
- [ ] Preserve required attribution/license notices when code is actually reused.
- [ ] Keep copied code isolated and documented.
- [ ] Prefer reimplementing small interfaces ourselves when the concept is simple.
- [ ] Do not copy proprietary or unclear-license code.

For Veil, the preferred approach is:

```text
Study project
     ↓
Understand pattern
     ↓
Design Veil-specific interface
     ↓
Implement independently
     ↓
Benchmark
```

rather than:

```text
Copy source
    ↓
Rename classes
    ↓
Hope architecture works
```

---

# 17. Proposed Final Architecture

Once the migration is mature:

```text
veil/
├── characters/
│   ├── loader.py
│   ├── schema.py
│   └── stella/
│       ├── character.yaml
│       ├── personality.yaml
│       ├── lore.yaml
│       └── rules.yaml
│
├── runtime/
│   ├── conversation.py
│   ├── context.py
│   ├── pipeline.py
│   └── events.py
│
├── state/
│   ├── character_state.py
│   ├── relationship.py
│   ├── emotion.py
│   └── decay.py
│
├── memory/
│   ├── models.py
│   ├── repository.py
│   ├── extractor.py
│   ├── retriever.py
│   ├── ranking.py
│   └── consolidation.py
│
├── llm/
│   ├── base.py
│   ├── llama_cpp.py
│   └── openai_compatible.py
│
├── cognition/
│   ├── tools.py
│   └── executor.py
│
├── evaluation/
│   ├── evaluator.py
│   ├── benchmarks.py
│   └── scoring.py
│
└── adapters/
    ├── cli/
    ├── web/
    ├── discord/
    ├── tts/
    ├── stt/
    ├── live2d/
    └── vrm/
```

The exact directory names are not mandatory. The **boundaries** are.

---

# 18. Milestone Definition

## M1 — Generic Character

Done when:

```text
Stella + ExampleCharacter
```

can run through the same runtime without modifying core source code.

## M2 — Persistent Character

Done when:

```text
restart process
    ↓
state survives
memory survives
relationship survives
```

## M3 — Context-Aware Character

Done when the runtime retrieves only relevant memories/lore and builds a measurable context.

## M4 — Consistent Character

Done when benchmark results demonstrate stable personality, lore, memory, and state behavior.

## M5 — Model Independent

Done when at least two LLM backends can use the same Character Runtime.

## M6 — Tunable Character

Done when LoRA/SFT can be evaluated against the untuned baseline without changing runtime architecture.

## M7 — VTuber Ready

Done when a frontend can consume:

```text
text
emotion
intensity
expression
action
```

without knowing how Veil generated them.

---

# 19. Immediate Next Actions

Do these first. Everything else can wait.

- [ ] Audit current repository against this TODO.
- [ ] Run existing tests and record baseline.
- [ ] Identify Stella-specific coupling.
- [ ] Design `CharacterDefinition`.
- [ ] Design `CharacterState`.
- [ ] Design `RelationshipState`.
- [ ] Add second dummy character.
- [ ] Refactor only after tests cover the current behavior.

**Do not train the model yet.**

The first win is proving that Veil can make two different characters behave differently using the same runtime.
