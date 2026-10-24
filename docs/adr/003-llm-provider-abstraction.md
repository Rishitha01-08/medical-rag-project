# ADR 003: Provider abstraction with mock-first generation

- **Status:** Accepted
- **Context:** The prototype loaded a large model on import and required downloads. The upgrade must not make paid or network calls.
- **Decision:** Define a provider interface and strict structured response schemas; use deterministic mock generation by default and allow OpenAI-compatible/Gemini adapters only with mock mode disabled and the matching environment key configured.
- **Alternatives:** Keep direct Transformers pipeline, support one hosted provider only, or remove generation abstraction.
- **Trade-offs:** Tests remain reproducible and offline; real adapters require credentials and network at runtime, and are not clinically validated.
- **Consequences:** Provider adapters validate structured output and retry malformed output once. CI sets mock mode and makes no provider calls.
