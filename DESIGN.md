Veil Core & Stella — Design

Status: Proposed; pending repository audit
Deployment target: Local-first
Primary character: Stella
Long-term presentation: Voice-enabled AI companion and Live2D VTuber

1. Purpose

Veil is a reusable character runtime for persistent AI companion experiences.

Stella is the first reference character, designed for natural Indonesian-first conversation, emotional continuity, persistent memory, controllable behavior, and eventual real-time voice and Live2D presentation.

The runtime should prioritize character consistency and reliability over model complexity or the number of integrations.

This document describes the target design. It does not claim that the current implementation already follows these boundaries. The repository audit must verify the existing code before refactoring decisions are finalized.

2. Design Principles

1. Character logic stays in the core. Platforms and presentation layers must not own persona logic.
2. Character identity is data. Stella-specific identity and lore should not be hard-coded into generic runtime modules.
3. Mutable state is separate from identity. Mood, relationship state, and temporary context must not silently modify the character definition.
4. Memory is external state. The model must not be treated as the source of truth for persistent memories.
5. Inference is replaceable. Local models and future alternative backends must share a stable interface.
6. Voice and avatar are adapters. The core must not depend on a specific TTS engine or Live2D runtime.
7. Local-first is the default. Cloud inference may be optional, but it must not be required for core operation.
8. Measure before optimizing. Use regression tests and benchmarks to evaluate changes.
9. Prefer reversible changes. Preserve working functionality until evidence justifies replacement.

3. Logical Architecture

Text / Microphone / Discord / Other Input Adapters
                       |
                       v
              Input and Session Layer
                       |
                       v
                  Veil Runtime
        lifecycle, events, cancellation, routing
                       |
                       v
                  Stella Engine
       +---------------+----------------+
       |               |                |
       v               v                v
   Dialogue /       State and          Memory
    Context          Emotion         Retrieval
       |               |                |
       +---------------+----------------+
                       |
                       v
                  LLM Adapter
              local GGUF first
                       |
                       v
              Response / Action Plan
                 /             \
                v               v
         Speech Adapter    Behavior Adapter
          local TTS        expressions/actions
          audio timing     lip-sync/gestures
                \               /
                 v             v
                Output Runtime
          audio playback + Live2D adapter

This is a logical architecture, not a requirement that every component become a separate process. Start with explicit interfaces and tests. Split modules or processes only when justified by complexity, lifecycle, or resource constraints.

4. Subsystem Responsibilities

4.1 Veil Runtime

Responsible for:

- Application lifecycle and shutdown
- Session and turn coordination
- Routing inputs to the appropriate processing path
- Event delivery and cancellation
- Adapter initialization and error handling

It must not contain Stella-specific lore or hard-code vendor-specific speech and avatar behavior.

4.2 Character Definition

Responsible for stable character information:

- Identity and personality traits
- Speech style
- Lore and background
- Behavioral rules and boundaries
- Supported expression/action vocabulary

Character definitions should be data-driven where practical.

Proposed structure:

characters/
  stella/
    character.yaml
    personality.yaml
    lore.yaml
    rules.yaml

This structure is a target proposal. Adopt it only if the audit confirms that it improves the existing implementation.

4.3 Dialogue and Context

Responsible for:

- Constructing model context
- Selecting relevant conversation history
- Incorporating relevant memories and current state
- Managing response generation
- Reserving sufficient context for user input and output
- Returning a structured response

Prompt construction should be observable and testable. Prompt fragments should not be scattered throughout unrelated modules.

4.4 State and Emotion

Responsible for:

- Mutable mood and emotional mode
- Relationship state
- Deterministic state transitions where practical
- Decay and cooldown
- State validation and persistence
- Versioned schema migrations

Model-generated text must not directly overwrite relationship state. State updates should pass through an explicit, validated transition policy.

Emotion analysis may use deterministic rules initially. A more advanced classifier should be introduced only when its benefit can be evaluated.

4.5 Memory

Responsible for:

- Short-term conversation history
- Long-term facts, preferences, and events
- Emotional memory
- Retrieval, ranking, and deduplication
- Persistent storage and recovery

Do not inject the entire memory database into the prompt. Keep the existing keyword retrieval approach as a baseline until semantic or hybrid retrieval demonstrates measurable improvement.

4.6 LLM Adapter

Responsible for a stable generation interface independent of the selected model or inference library.

The local GGUF/llama.cpp path remains the default target, subject to the repository and hardware audit.

The adapter should make relevant capabilities explicit, including:

- Text generation
- Streaming support
- Cancellation behavior
- Context limits
- Generation configuration
- Model/runtime errors

Changing models should not require rewriting character, memory, state, or relationship logic.

4.7 Cognition and Tools

Responsible for tool selection, execution, result normalization, and error reporting.

Tool output is data for the dialogue system. It must not override character policy or become an unvalidated instruction to the runtime.

The character's visible response should remain natural rather than exposing unnecessary internal execution traces.

4.8 Response Evaluator and Behavior Policy

Responsible for validating generated text and structured behavior metadata.

It may enforce deterministic response constraints, but it should not silently mutate the character's emotional or relationship state.

Invalid behavior metadata should fall back safely without preventing valid text from being delivered.

5. Voice Architecture

5.1 Initial strategy

Use a modular speech pipeline:

Audio Input
    -> VAD
    -> STT
    -> Normalized Transcript
    -> Stella Engine
    -> Structured Response
    -> TTS
    -> Audio Playback

This architecture provides independent control over recognition, dialogue behavior, and voice synthesis.

An audio-to-audio multimodal model remains an optional alternative behind the same input/output boundary. It is not a requirement for the core runtime.

5.2 Voice Activity Detection

VAD detects speech boundaries and helps the runtime manage turn-taking and interruption.

Candidate implementations may include Silero VAD or another lightweight maintained alternative.

Selection criteria:

- Accuracy in the intended environment
- CPU and memory requirements
- Latency
- Streaming support
- Compatibility with the target platform

5.3 Speech-to-Text

STT converts user audio into text for the dialogue engine.

The adapter should expose timestamps and confidence information when available, without requiring every backend to provide identical capabilities.

Evaluation criteria:

- Indonesian transcription accuracy
- Mixed-language handling
- Latency
- CPU and memory footprint
- Streaming behavior
- Compatibility with microphone and platform audio sources

5.4 Text-to-Speech

TTS synthesizes Stella's response.

The speech adapter should accept text and optional validated delivery metadata, such as pace, energy, or emotion, when supported by the chosen engine.

Do not assume every TTS backend supports every control.

Evaluation criteria:

- Indonesian pronunciation and intelligibility
- Naturalness and prosody
- Character voice consistency
- Streaming support
- First-audio latency and real-time factor
- Memory and compute requirements
- Model and dataset licensing

A distinctive Stella voice is a long-term goal. Voice cloning or reference-based synthesis must use audio the project owner has permission to use.

5.5 Audio Session Controller

Responsible for:

- Starting and stopping playback
- Streaming audio chunks
- Associating audio with a conversation turn
- Interrupting pending generation or playback
- Handling audio-device and transport failures
- Exposing playback timing to the avatar adapter

Discord audio handling and local microphone capture must remain platform-specific adapters.

6. Structured Response Contract

The core should return a structured response envelope even when a client displays only text.

Illustrative example:

{
  "schema_version": 1,
  "turn_id": "runtime-generated-id",
  "text": "Ih, kamu ke mana aja? Aku nungguin, tahu.",
  "emotion": {
    "primary": "playful",
    "intensity": 0.65
  },
  "delivery": {
    "pace": "slightly_fast",
    "energy": 0.7
  },
  "behavior": {
    "expression": "pout",
    "action": "arms_crossed"
  }
}

This is an example, not a finalized schema.

Before implementation, define:

- Allowed fields and data types
- Versioning rules
- Valid emotion and action identifiers
- Numeric ranges and validation
- Default behavior for missing or invalid metadata
- Compatibility rules for text-only clients
- Tests for malformed output

Dialogue text must remain usable even when optional emotion, delivery, or behavior metadata is absent.

7. Avatar and Behavior Adapter

The behavior adapter converts validated metadata into avatar-specific actions.

Responsibilities:

- Map generic emotion labels to expressions
- Map actions to available motions
- Coordinate mouth movement with audio
- Handle idle behavior and transitions
- Manage unsupported or missing expressions gracefully

The core must not depend on Live2D SDK classes, model parameter IDs, or a particular avatar viewer.

Lip-sync should use suitable timing, viseme, or amplitude information when available. A simple amplitude-based fallback may be used when richer timing data is unavailable.

8. Events and Interruption

The runtime should expose explicit internal events or equivalent interfaces.

Initial conceptual events:

- "input.text_received"
- "input.speech_started"
- "input.speech_ended"
- "input.transcript_ready"
- "dialogue.response_started"
- "dialogue.response_ready"
- "speech.synthesis_started"
- "speech.audio_chunk_ready"
- "speech.playback_started"
- "speech.playback_finished"
- "speech.cancel_requested"
- "behavior.expression_requested"
- "behavior.action_requested"
- "runtime.error"

Events should carry a session or turn identifier and timestamp where relevant.

Do not build a distributed event-bus service for a single-process personal runtime. An in-process dispatcher or explicit asynchronous interfaces may be sufficient.

Interruption requirements

1. New user speech can request cancellation of pending generation or playback.
2. Cancellation must be tied to the correct turn.
3. A stale task must not cancel a newer turn.
4. Completion events must reflect actual completion.
5. STT/TTS failures must not corrupt character state or memory.

9. Local Deployment

Constrained development environment

For Android/Termux or similar constrained hardware:

- Prioritize deterministic tests, text interaction, and state/memory development.
- Measure the current model's resource use.
- Test speech components independently before combining them.
- Do not assume STT, LLM, and TTS can all remain resident with acceptable latency.
- Keep the core testable without microphone, Discord, or avatar dependencies.

Main local runtime

The intended long-term runtime is a more capable local Linux or desktop environment if the measured workload exceeds the development device's practical limits.

The same character core should remain usable through a CLI test harness and through voice/avatar adapters.

10. Persistence and Privacy

- Back up state and memory before schema-changing work.
- Use versioned migrations and validate loaded values.
- Test restore against a temporary destination before applying it to production data.
- Keep transcripts and personal memories local by default.
- Avoid unnecessary logging of raw audio and sensitive conversation content.
- Never commit API keys, session tokens, or credentials.
- Respect model, dataset, voice-reference, and software licenses.

11. Testing and Evaluation

Deterministic tests

- Character definition loading
- State transitions and decay
- Serialization, migration, backup, and restore
- Memory extraction, ranking, deduplication, and persistence
- Context construction and budget limits
- Response-envelope validation
- Event ordering and turn identifiers
- Cancellation and error recovery

These tests should not require a network connection or model download unless explicitly marked as integration tests.

Character benchmark

Maintain a fixed Indonesian-first evaluation set covering:

- Natural casual conversation
- Speech style and persona consistency
- Emotional responsiveness
- Relationship state consistency
- Memory seed and recall
- Lore consistency
- Long-session stability
- Unwanted assistant-style behavior
- Latency and resource use

Voice benchmark

- Indonesian pronunciation and intelligibility
- First-audio latency
- Real-time factor
- Interruption responsiveness
- Delivery variation
- Playback and cancellation correctness

Avatar benchmark

- Expression and action mapping
- Lip-sync alignment
- Fallback behavior when timing metadata is unavailable
- No dependency from core logic to Live2D-specific APIs

12. Non-Goals

The initial refactor does not require:

- Training a model from scratch
- An audio-to-audio multimodal model
- A cloud SaaS or multi-user service
- A complete rewrite before regression tests exist
- A vector database before retrieval is benchmarked
- Every messaging platform at once
- Tight coupling between one TTS vendor and one avatar runtime
- Fine-tuning or LoRA before persistent failures have been measured

13. Open Decisions

Resolve these through the repository audit and measured experiments:

- Which current modules should be kept, refactored, replaced, or deferred?
- Can the current PersonalityCore be decomposed incrementally?
- Which model and inference configuration are actually active?
- What hardware will host the main local runtime?
- What are the acceptable latency and memory budgets?
- Which local STT/TTS engines perform well for Indonesian?
- Should the first voice input be local microphone or Discord?
- Which Live2D runtime or viewer will be used?
- What final response schema and event implementation are justified?

14. Change Decision Rule

Every major change must document:

1. The observed problem and evidence
2. Expected behavior change
3. Regression tests
4. Rollback path
5. Resource and latency impact where relevant

Prefer the smallest reversible change that resolves a measured problem.

The repository audit is the gate before committing to a larger architectural rewrite.
