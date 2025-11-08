# Questionnaire Results Storage

This directory stores anonymous questionnaire submissions for research purposes.

## Data Format

Each submission is stored as a separate JSON file with the following structure:

```json
{
  "user_id": "unique-persistent-uuid",
  "country_code": "DE",
  "submitted_at": "2025-11-08T12:34:56.789Z",
  "questions": [
    {
      "question_number": 1,
      "question_text": "Question text here",
      "answer": "yes|no|neutral|skipped",
      "weight_enabled": true,
      "custom_answer": "Optional custom text answer"
    }
  ]
}
```

## File Naming Convention

Files are named: `{timestamp}_{user_id_prefix}.json`

Example: `20251108_123456_abc123.json`

## Privacy

- All data is anonymous
- User IDs are randomly generated UUIDs stored in browser localStorage
- No personally identifiable information is collected
- All result files are git-ignored by default
