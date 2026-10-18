# THE SPECIAL ONE — Sample curriculum package

This directory is bundled with the Windows Standard edition.

## Importable JSON
`primary3-example-bank.json` is a demonstration question bank, not an official school curriculum. Sign in as admin, open **Import JSON Question Bank**, and select the file. The importer validates all entries before inserting them.

## Matching PDF
`THE_SPECIAL_ONE_Sample_Questions.pdf` is generated during the Windows build from the same JSON data. It is a printable reference, **not** a direct Standard-edition import format. The Standard edition imports JSON only.

## Make your own bank
Copy the JSON file and keep the outer fields exactly:
- `format`: `the-special-one-question-bank`
- `version`: `1`
- `questions`: array of question objects.

Each question needs `grade`, `unit`, `lesson`, `difficulty`, `kind`, `prompt`, `answer`, and `options`.

Valid difficulties: `easy`, `medium`, `hard`.
Valid question types: `choose`, `fill`, `rearrange`, `letters`.
For `choose`, provide 2–5 options and include the exact correct answer among them. For the other kinds, `options` can be an empty array.

**Important:** Student grades must match the `grade` text in the imported bank exactly (e.g., `Primary 3`). Units must also match the labels entered in the bank. Avoid importing the same JSON repeatedly because that creates duplicate questions.

## Admin → student workflow
1. Import approved questions from JSON.
2. Create student accounts with the matching grade.
3. In Exam Builder, select grade, one or more units, one or more types, and question count (20/40/60/80/100).
4. Create draft → Publish → Show now.
5. Students see the active teacher exam for their grade. The admin can hide it at any time.
6. Students can also generate private **Custom Practice** from their own grade's units/types and see their scores.

Use approved curriculum materials when replacing these demonstration questions. The PDF is not automatically parsed into questions in Standard edition.
