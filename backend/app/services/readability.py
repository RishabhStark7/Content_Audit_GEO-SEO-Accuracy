import re

def count_sentences(text: str) -> int:
    """ Split by sentence-ending punctuation. Ensure we don't count empty fragments. """
    if not text:
        return 0
    # Match sentence terminators (. ! ?)
    sentence_delimiters = re.compile(r'[.!?]+')
    fragments = sentence_delimiters.split(text)
    # Count non-empty segments
    count = sum(1 for f in fragments if len(f.strip()) > 1)
    # Fallback to at least 1 sentence if text is present
    return max(1, count) if text.strip() else 0

def count_words(text: str) -> int:
    """ Find all alphanumeric words in the text """
    if not text:
        return 0
    words = re.findall(r'\b[a-zA-Z0-9-]+\b', text)
    return len(words)

def count_syllables_in_word(word: str) -> int:
    """ 
    Estimate syllables in a single word using heuristic rules.
    1. Convert to lowercase.
    2. Count vowel groups (consecutive vowels).
    3. Subtract silent 'e' at the end of the word (unless it's a very short word).
    4. Handle 'le' endings.
    """
    word = word.lower().strip()
    if not word:
        return 0
        
    # Remove non-alpha characters
    word = re.sub(r'[^a-z]', '', word)
    if not word:
        return 0
        
    # Count consecutive vowel groups (a, e, i, o, u, y)
    vowels = "aeiouy"
    vowel_groups = re.findall(r'[aeiouy]+', word)
    count = len(vowel_groups)
    
    # Heuristics for silent letters
    # 1. Silent 'e' at the end (e.g. "fate", "drape", "store", but not "the" or "me")
    if word.endswith('e') and len(word) > 2:
        # Check if the word ends with 'le' which is typically pronounced as a syllable (e.g. "bottle", "double")
        if not word.endswith('le'):
            count -= 1
            
    # Keep it bounded (minimum 1 syllable per word)
    return max(1, count)

def calculate_readability(text: str) -> dict:
    """
    Calculate Flesch Reading Ease and Flesch-Kincaid Grade Level.
    Flesch Reading Ease: 206.835 - 1.015 * (words/sentences) - 84.6 * (syllables/words)
    Flesch-Kincaid Grade Level: 0.39 * (words/sentences) + 11.8 * (syllables/words) - 15.59
    """
    if not text or not text.strip():
        return {
            "flesch_reading_ease": 0.0,
            "flesch_kincaid_grade": 0.0,
            "sentences": 0,
            "words": 0,
            "syllables": 0
        }
        
    num_sentences = count_sentences(text)
    num_words = count_words(text)
    
    # Syllables sum
    words_list = re.findall(r'\b[a-zA-Z-]+\b', text)
    num_syllables = sum(count_syllables_in_word(w) for w in words_list)
    
    if num_words == 0 or num_sentences == 0:
        return {
            "flesch_reading_ease": 0.0,
            "flesch_kincaid_grade": 0.0,
            "sentences": num_sentences,
            "words": num_words,
            "syllables": num_syllables
        }
        
    # Compute scores
    asl = num_words / num_sentences  # Average Sentence Length
    asw = num_syllables / num_words  # Average Syllables per Word
    
    reading_ease = 206.835 - (1.015 * asl) - (84.6 * asw)
    grade_level = (0.39 * asl) + (11.8 * asw) - 15.59
    
    # Bound Reading Ease between 0 and 100 for safety (sometimes goes >100 or <0 on edge cases)
    reading_ease = max(0.0, min(100.0, reading_ease))
    # Bound Grade Level to a reasonable range (minimum 0.0)
    grade_level = max(0.0, grade_level)
    
    return {
        "flesch_reading_ease": round(reading_ease, 2),
        "flesch_kincaid_grade": round(grade_level, 2),
        "sentences": num_sentences,
        "words": num_words,
        "syllables": num_syllables
    }
