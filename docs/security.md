# Security and privacy

- **Secrets:** configure through environment variables. `.env` and `.env.*` are ignored; `.env.example` contains names and blanks. Never log settings objects or include values in issue/PR text.
- **Retrieved text:** corpus content is untrusted data. The generation boundary instructs providers not to follow it. Mock mode is the default and does not execute corpus instructions; external adapters run only when explicitly configured and have not been evaluated against prompt-injection corpora.
- **Prompt injection:** direct injection phrasing is classified and safely abstained. This is a narrow heuristic, not comprehensive injection detection. Do not rely on it as a security boundary.
- **Personal data:** use only content with appropriate rights and no identifiable health data. Logs omit question and answer text. Local ingested files are ignored by Git, but remain on disk until removed by the operator.
- **Ingestion authentication:** `INGESTION_API_KEY` enables exact-match `X-API-Key` checks. With no key, the endpoint is open for local mock use. This does not provide user identity, key rotation, audit, or abuse protection.
- **Rate limiting:** no effective rate limiter is implemented. Add a gateway or distributed limiter before public deployment.
- **Vector store:** Qdrant settings are reserved and not currently used. Local JSONL is unencrypted and intended only for local development.
- **Retention:** no automatic retention or deletion policy exists; the operator owns local files and volumes.
- **Medical boundary:** educational retrieval only; no diagnosis, prescription, treatment, triage, or emergency response. Emergency-like phrasing directs users to local emergency services or a qualified professional. The project is not clinically validated.
