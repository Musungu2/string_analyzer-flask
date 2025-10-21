#  String Analyzer API — Flask Implementation

A RESTful API service that analyzes strings and stores their computed properties.

Built for **HNG Backend Wizards Stage 1**.

---

##  Features

For each analyzed string, the API computes and stores:
- `length`: Number of characters
- `is_palindrome`: Boolean — checks if the string reads the same backward and forward (case-insensitive)
- `unique_characters`: Count of distinct characters
- `word_count`: Number of words
- `sha256_hash`: Unique SHA-256 hash of the string
- `character_frequency_map`: Object mapping each character to its occurrence count

---

##  Endpoints

### 1️⃣ Create/Analyze a String
**POST** `/strings`

**Request Body:**
```json
{
  "value": "string to analyze"
}
