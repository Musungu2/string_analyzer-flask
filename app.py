from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import hashlib
from collections import Counter
import re

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///strings.db'
db = SQLAlchemy(app)

from models import AnalyzedString
from utils import analyze_string

@app.route("/strings", methods=["POST"])
def create_string():
    data = request.get_json()
    if not data or "value" not in data:
        return jsonify({"error": "Missing 'value' field"}), 400
    
    value = data["value"]
    if not isinstance(value, str):
        return jsonify({"error": "'value' must be a string"}), 422
    
    # Compute hash
    sha256_hash = hashlib.sha256(value.encode()).hexdigest()
    existing = AnalyzedString.query.get(sha256_hash)
    if existing:
        return jsonify({"error": "String already exists"}), 409
    
    props = analyze_string(value)
    new_string = AnalyzedString(
        id=props["sha256_hash"],
        value=value,
        length=props["length"],
        is_palindrome=props["is_palindrome"],
        unique_characters=props["unique_characters"],
        word_count=props["word_count"],
        character_frequency_map=props["character_frequency_map"]
    )
    
    db.session.add(new_string)
    db.session.commit()
    
    return jsonify({
        "id": props["sha256_hash"],
        "value": value,
        "properties": props,
        "created_at": new_string.created_at.isoformat() + "Z"
    }), 201

@app.route("/strings/<string_value>", methods=["GET"])
def get_string(string_value):
    record = AnalyzedString.query.filter_by(value=string_value).first()
    if not record:
        return jsonify({"error": "String not found"}), 404

    props = {
        "length": record.length,
        "is_palindrome": record.is_palindrome,
        "unique_characters": record.unique_characters,
        "word_count": record.word_count,
        "sha256_hash": record.id,
        "character_frequency_map": record.character_frequency_map
    }

    return jsonify({
        "id": record.id,
        "value": record.value,
        "properties": props,
        "created_at": record.created_at.isoformat() + "Z"
    }), 200
@app.route("/strings", methods=["GET"])
def get_all_strings():
    # Get query parameters
    is_palindrome = request.args.get("is_palindrome")
    min_length = request.args.get("min_length", type=int)
    max_length = request.args.get("max_length", type=int)
    word_count = request.args.get("word_count", type=int)
    contains_character = request.args.get("contains_character")

    # Start query
    query = AnalyzedString.query

    # Apply filters
    filters_applied = {}

    if is_palindrome is not None:
        if is_palindrome.lower() not in ["true", "false"]:
            return jsonify({"error": "Invalid value for is_palindrome (must be true or false)"}), 400
        is_palindrome_value = is_palindrome.lower() == "true"
        query = query.filter_by(is_palindrome=is_palindrome_value)
        filters_applied["is_palindrome"] = is_palindrome_value

    if min_length is not None:
        query = query.filter(AnalyzedString.length >= min_length)
        filters_applied["min_length"] = min_length

    if max_length is not None:
        query = query.filter(AnalyzedString.length <= max_length)
        filters_applied["max_length"] = max_length

    if word_count is not None:
        query = query.filter_by(word_count=word_count)
        filters_applied["word_count"] = word_count

    if contains_character is not None:
        if len(contains_character) != 1:
            return jsonify({"error": "contains_character must be a single character"}), 400
        filters_applied["contains_character"] = contains_character
        query = query.filter(AnalyzedString.value.contains(contains_character))

    # Execute query
    results = query.all()

    data = []
    for record in results:
        props = {
            "length": record.length,
            "is_palindrome": record.is_palindrome,
            "unique_characters": record.unique_characters,
            "word_count": record.word_count,
            "sha256_hash": record.id,
            "character_frequency_map": record.character_frequency_map
        }
        data.append({
            "id": record.id,
            "value": record.value,
            "properties": props,
            "created_at": record.created_at.isoformat() + "Z"
        })

    return jsonify({
        "data": data,
        "count": len(data),
        "filters_applied": filters_applied
    }), 200
@app.route("/strings/<string_value>", methods=["DELETE"])
def delete_string(string_value):
    try:
        # Find the string in the database (case-sensitive match)
        record = AnalyzedString.query.filter_by(value=string_value).first()

        # If not found, return 404
        if not record:
            return jsonify({"error": "String not found"}), 404

        # Delete and commit
        db.session.delete(record)
        db.session.commit()

        # Return 204 No Content (empty body)
        return "", 204

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route("/strings/filter-by-natural-language", methods=["GET"])
def filter_by_natural_language():
    query_text = request.args.get("query", "").lower().strip()

    if not query_text:
        return jsonify({"error": "Missing query parameter"}), 400

    parsed_filters = {}

    # --- Handle Palindrome-related queries ---
    if "palindrome" in query_text or "palindromic" in query_text:
        parsed_filters["is_palindrome"] = True

    # --- Handle word count ---
    single_word_match = re.search(r"single\s+word", query_text)
    if single_word_match:
        parsed_filters["word_count"] = 1

    # --- Handle length-based queries ---
    longer_than_match = re.search(r"longer\s+than\s+(\d+)", query_text)
    shorter_than_match = re.search(r"shorter\s+than\s+(\d+)", query_text)
    exactly_match = re.search(r"exactly\s+(\d+)\s+characters", query_text)

    if longer_than_match:
        parsed_filters["min_length"] = int(longer_than_match.group(1)) + 1
    if shorter_than_match:
        parsed_filters["max_length"] = int(shorter_than_match.group(1)) - 1
    if exactly_match:
        parsed_filters["min_length"] = parsed_filters["max_length"] = int(exactly_match.group(1))

    # --- Handle contains letter/character queries ---
    contains_match = re.search(r"contain(?:s|ing)?\s+(?:the\s+letter\s+|letter\s+|character\s+)?([a-z])", query_text)
    if contains_match:
        parsed_filters["contains_character"] = contains_match.group(1)

    # Handle “first vowel” or similar heuristic
    if "first vowel" in query_text:
        parsed_filters["contains_character"] = "a"

    # If no valid filters detected
    if not parsed_filters:
        return jsonify({"error": "Unable to parse natural language query"}), 400

    # --- Apply filters using same logic as GET /strings ---
    query = AnalyzedString.query

    if "is_palindrome" in parsed_filters:
        query = query.filter_by(is_palindrome=parsed_filters["is_palindrome"])

    if "word_count" in parsed_filters:
        query = query.filter_by(word_count=parsed_filters["word_count"])

    if "min_length" in parsed_filters:
        query = query.filter(AnalyzedString.length >= parsed_filters["min_length"])

    if "max_length" in parsed_filters:
        query = query.filter(AnalyzedString.length <= parsed_filters["max_length"])

    if "contains_character" in parsed_filters:
        query = query.filter(AnalyzedString.value.contains(parsed_filters["contains_character"]))

    results = query.all()

    # --- Format response ---
    data = []
    for record in results:
        data.append({
            "id": record.id,
            "value": record.value,
            "properties": {
                "length": record.length,
                "is_palindrome": record.is_palindrome,
                "unique_characters": record.unique_characters,
                "word_count": record.word_count,
                "sha256_hash": record.id,
                "character_frequency_map": record.character_frequency_map
            },
            "created_at": record.created_at.isoformat() + "Z"
        })

    return jsonify({
        "data": data,
        "count": len(data),
        "interpreted_query": {
            "original": query_text,
            "parsed_filters": parsed_filters
        }
    }), 200
