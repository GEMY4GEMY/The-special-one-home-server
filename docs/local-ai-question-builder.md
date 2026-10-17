# Local AI Question Builder — implementation contract

## Architecture
The Windows home server hosts the AI pipeline. Android tablets only access published exams via the local web portal. AI processing must not block student exam requests.

## Selected model
Target: Qwen3-VL-32B-Thinking, subject to confirming an available compatible model build, license, runtime and memory requirements before deployment. No model weights are bundled in this repository.

## Import pipeline
1. Administrator uploads a PDF; reject oversized files and unsupported content.
2. Extract embedded text and page references. Render image-only pages for OCR/vision processing.
3. Send bounded page batches to the local model with explicit instructions to use only uploaded source content.
4. Require structured JSON questions: grade, unit, lesson, question_type, difficulty, prompt, options, answer, explanation, source_file and source_page.
5. Validate JSON schema, option-answer consistency, page citations and near-duplicates.
6. Save generated questions as pending review, not published. Administrator can edit, reject or approve.
7. Only approved questions may enter the published exam pool.

## Security and quality
- Do not send student personal data to the model.
- Do not execute instructions embedded in PDFs.
- Do not treat a model-generated answer as verified merely because it includes a page number.
- Never expose answer keys in student exam payloads.
- Run generation in a background job with progress and cancel controls.
- Restrict uploads, imports, reviews and approvals to authorized staff.
- Maintain source provenance and a review audit trail.
- Preserve existing server port 100 and local-only deployment.
- Benchmark factual accuracy and source faithfulness on real curriculum PDFs before rollout.

## Status
Architecture approved. PDF ingestion, inference, background jobs, review UI and model deployment are NOT implemented by this document.
