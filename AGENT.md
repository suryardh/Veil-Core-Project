# AGENT.md — Veil Development Guide

## Mission

Veil is being evolved into a reusable Character Runtime for persistent roleplay characters and AI VTuber-style personalities.

The primary engineering goal is **character consistency and continuity**, not maximum model complexity.

Read `PLAN.md` before making architectural changes.

## Core Principles

1. Character logic must not depend on Stella.
2. Character definitions are data; runtime behavior is code.
3. Memory is external state, not model knowledge.
4. Mutable emotional/relationship state must be separated from immutable character identity.
5. LLM providers are replaceable backends.
6. Fine-tuning is optional and must not be required by the runtime.
7. Prefer measurable behavior over subjective claims of improvement.
8. Keep the core runtime presentation-neutral.

## Architecture Boundaries

The intended subsystem boundaries are:

```text
Character Engine
Memory Engine
State / Emotion Engine
Relationship Engine
Cognition / Tool Engine
Context Builder
LLM Runtime
Response Evaluator
```

Avoid putting unrelated responsibilities into a single `PersonalityCore`-style god object.

When adding a feature, decide which subsystem owns it before implementing it.

## Character System

Do not hardcode Stella-specific identity, lore, or personality into generic runtime modules.

Prefer:

```text
characters/
  stella/
    character.yaml
    personality.yaml
    lore.yaml
    rules.yaml
```

A new character should be loadable without modifying the runtime's core source code.

Stella is the reference character, not a special case.

## State

Distinguish:

```text
Character Definition = stable
Character State       = mutable
```

Never persist temporary state by silently modifying the character definition.

State changes should be deterministic where practical and covered by unit tests.

## Memory

Memory must remain independent from model weights and prompt text.

Use explicit memory types such as:

```text
fact
preference
event
relationship
emotional
conversation
lore
```

Do not inject the entire memory database into prompts.

Retrieval should select relevant memories using importance, recency, relationship relevance, semantic similarity, or a combination of these.

Do not introduce a vector database merely because it is fashionable. Establish a simpler baseline first.

## Emotion

The current rule/keyword-based emotion analysis is acceptable as a baseline.

Do not remove a working deterministic fallback solely to replace it with an LLM.

Any future emotion classifier should have a clear interface so the runtime can switch implementations without changing the rest of the pipeline.

## LLM Integration

LLM calls belong behind an abstraction.

Core runtime code should not assume a specific provider, model name, context length, or inference engine.

Local GGUF/llama.cpp support should remain viable.

A model change must not require rewriting Character, Memory, State, or Relationship logic.

## Prompt / Context Construction

Build context explicitly:

```text
Character
+ State
+ Relevant Memories
+ Recent Conversation
+ Tool Results
+ User Input
```

Do not scatter prompt fragments throughout unrelated modules.

Prefer one observable context-building stage.

Do not place internal tool implementation details into the character's visible response.

## Fine-Tuning

Do not add CPT, SFT, LoRA, DPO, or other tuning infrastructure to the runtime until a baseline has been measured.

Required baseline components:

- character definition
- memory
- state
- context builder
- response evaluator

Training experiments belong under a separate training/evaluation area and must not make runtime execution dependent on training artifacts.

## Evaluation

Every major architectural change should have a measurable test or benchmark.

At minimum, evaluate:

- personality consistency
- speech style
- lore consistency
- state consistency
- memory consistency
- regression against previous behavior

Avoid relying only on a few hand-picked conversations.

## Testing Rules

Prefer small deterministic tests for:

- state transitions
- decay
- relationship updates
- memory ranking
- character loading
- prompt/context assembly
- serialization

LLM-dependent tests should be separated from deterministic unit tests.

Network/model availability must not be required for the core test suite.

## VTuber / Voice Compatibility

The runtime may eventually emit structured metadata such as:

```json
{
  "text": "...",
  "emotion": "happy",
  "intensity": 0.7,
  "expression": "smile",
  "action": "wave"
}
```

Do not couple this metadata to a specific avatar engine.

Live2D, VRM, TTS, STT, streaming, Web, and messaging integrations belong in adapters.

## Dependency Rules

Before adding a dependency:

1. Check whether the standard library or an existing dependency is sufficient.
2. Check whether the dependency is necessary for the current milestone.
3. Prefer small, maintained dependencies.
4. Avoid infrastructure that is not yet justified by measurements.

## Refactoring Rules

When refactoring existing code:

1. Preserve working behavior where practical.
2. Add tests before changing fragile logic.
3. Make one architectural boundary change at a time.
4. Avoid mixing unrelated feature work with core refactors.
5. Remove old code only after its replacement is verified.

Do not perform a giant rewrite just to make the directory structure look cleaner.

## Git / Change Hygiene

Keep commits focused and descriptive.

Recommended prefixes:

```text
feat:
fix:
refactor:
test:
docs:
chore:
```

Examples:

```text
refactor: extract character definition from personality core
feat: add generic character loader
test: cover relationship state transitions
docs: define Veil 2.0 runtime architecture
```

Do not commit generated model files, secrets, API keys, local databases, or machine-specific artifacts.

## Security

Never commit:

- API keys
- tokens
- passwords
- private credentials
- personal access tokens
- private model artifacts unless explicitly intended

Use environment variables or local configuration files excluded by `.gitignore`.

Treat tool execution and external integrations as privileged capabilities.

## Current Priority

Follow the migration order in `PLAN.md`.

The immediate priority is:

```text
Character abstraction
    ↓
State / relationship boundaries
    ↓
Memory 2.0
    ↓
Context pipeline
    ↓
Consistency evaluation
    ↓
LLM abstraction
    ↓
Training experiments
    ↓
Voice / VTuber adapters
```

Do not skip directly to fine-tuning, avatar rendering, or autonomous-agent features while the core character runtime is still unstable.

## Definition of Good Work

A good Veil change should make at least one of these properties better:

- character consistency
- long-term continuity
- testability
- modularity
- model independence
- observability
- reliability

If a change does not clearly improve one of them, question whether it belongs in the current milestone.
