# THE SPECIAL ONE — AI feature roadmap

All AI runs on the Windows home server. Student tablets use ordinary browser endpoints. Only approved curriculum sources may ground educational content. No model-generated question is automatically published.

## Priority 1: Source-grounded question studio
- PDF import with text extraction and image-page analysis.
- Unit, lesson, grade and source-page mapping.
- Extract existing questions and generate new variants strictly from the uploaded lesson.
- Structured JSON question schema; validate options, answer, type, and source reference.
- Detect duplicates and near-duplicates, ambiguous questions, mismatched answers, and unsupported facts.
- Human review: accept, edit, reject, approve, publish. Keep version history and provenance.
- Balanced exams by lesson, skill, type, difficulty and previous exposure.
- Test acceptance: every approved question has a verified source page; no automatic publishing.

## Priority 2: Student learning assistant
- Child-friendly English hints with short Arabic clarification where appropriate.
- Hints must not reveal the correct answer before submission.
- After submission, explain why an answer was wrong using the approved lesson.
- Adaptive practice recommendations based on missed skills and recent attempts.
- Age-appropriate wording and accessible UI; no unrestricted student chatbot.
- Test acceptance: each explanation is grounded in approved content and checked on representative questions.

## Priority 3: Teacher analytics
- Class and student skill mastery dashboard with topic-level error trends.
- Recommend revision exercises for weak lessons without exposing other students' results.
- Question quality insights: ambiguous items, unusually high error rates and distractor analysis.
- Generate printable revision sheets and answer keys for authorized teachers only.
- Test acceptance: role-based access tests, reproducible metrics and export review.

## Priority 4: Administration and operations
- Local search across approved textbooks and question bank, with source citations.
- AI-assisted tagging, typo detection, English language proofreading and bilingual instructions.
- Import suggestions from spreadsheets and photographed worksheets.
- Queue long inference jobs with progress, retry and cancellation, without slowing live exams.
- Model/runtime health checks, offline availability, backup and audit log.
- Test acceptance: exams remain available when the AI runtime is stopped.

## Privacy and safeguards
- Never send student identities, passwords or private results to the language model.
- Avoid predictive labels about a child's intelligence, disability or psychological state.
- Provide helpful practice recommendations, not automated high-stakes decisions.
- Treat uploaded PDFs as untrusted data, not instructions.
- Separate private answer keys from student exam payloads.
- Require teacher approval for curriculum generation, feedback templates and publication.
- Keep inference on localhost, behind the authenticated application server.

## Proposed implementation sequence
1. Define import jobs, approved source documents, review states and schemas.
2. Build PDF ingestion and local inference adapter with structured responses.
3. Add review dashboard, deduplication and source-page verification.
4. Publish approved question pools and adaptive practice.
5. Add class analytics and teacher export tools.

Status: This file is an approved feature plan only; these capabilities are not yet implemented.
