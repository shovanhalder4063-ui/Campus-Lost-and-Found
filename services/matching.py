"""
AI Matching Service for Campus Lost & Found Portal.

This module provides a local, deterministic, and explainable AI matching engine
using scikit-learn's TF-IDF Vectorizer and Cosine Similarity, enhanced with
contextual relevance heuristics (category, location, and date proximity).

Key Principles:
1. Privacy First: Never processes private verification details or user credentials.
2. Local Execution: Requires no external APIs, subscriptions, or network access.
3. Transparent & Honest: Clearly displays 'Potential Match' and enumerates exactly
   why a match was recommended.
"""

import re
from datetime import date
from typing import List, Dict, Any, Optional
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def sanitize_text(text: Optional[str]) -> str:
    """Normalize input text by removing excessive whitespace and lowercase."""
    if not text:
        return ""
    text = re.sub(r"[^\w\s]", " ", text)
    return " ".join(text.lower().split())


def build_item_corpus_string(item) -> str:
    """
    Construct the public searchable text representation of an item.
    Crucial: Omits private verification details, passwords, and user contacts.
    """
    parts = [
        sanitize_text(getattr(item, "title", "")),
        sanitize_text(getattr(item, "category", "")),
        sanitize_text(getattr(item, "description", "")),
        sanitize_text(getattr(item, "location", ""))
    ]
    return " ".join([p for p in parts if p])


def compute_date_proximity_bonus(date1: Optional[date], date2: Optional[date]) -> tuple[float, Optional[str]]:
    """
    Calculate bonus score based on temporal proximity between incident dates.
    Returns (bonus_score, explanation_or_None).
    """
    if not date1 or not date2:
        return 0.0, None

    try:
        delta_days = abs((date1 - date2).days)
    except Exception:
        return 0.0, None

    if delta_days == 0:
        return 0.08, "Reported on the exact same date"
    elif delta_days <= 3:
        return 0.05, f"Incident dates within {delta_days} day(s) of each other"
    elif delta_days <= 7:
        return 0.02, f"Incident dates within {delta_days} days of each other"
    return 0.0, None


def compute_location_bonus(loc1: Optional[str], loc2: Optional[str]) -> tuple[float, Optional[str]]:
    """
    Check if two locations match exactly or share meaningful campus tokens
    (e.g., 'Library', 'Auditorium', 'Cafeteria', 'Block A').
    """
    if not loc1 or not loc2:
        return 0.0, None

    s1 = sanitize_text(loc1)
    s2 = sanitize_text(loc2)

    if not s1 or not s2:
        return 0.0, None

    if s1 == s2:
        return 0.12, f"Exact same location ({loc1})"

    # Token overlap check (ignoring common trivial words)
    stop_tokens = {"room", "near", "floor", "the", "at", "in", "and", "by", "block"}
    tokens1 = set(s1.split()) - stop_tokens
    tokens2 = set(s2.split()) - stop_tokens

    common = tokens1.intersection(tokens2)
    if common:
        shared_word = next(iter(common)).capitalize()
        return 0.08, f"Similar campus location area ({shared_word})"

    return 0.0, None


class ItemMatcher:
    """Local TF-IDF and heuristic matching engine."""

    def __init__(self, min_score: float = 0.15, top_k: int = 5):
        self.min_score = min_score
        self.top_k = top_k

    def find_matches(self, target_item, candidate_items: List[Any]) -> List[Dict[str, Any]]:
        """
        Compare target_item with a list of candidate items.
        
        Args:
            target_item: The Item being matched.
            candidate_items: Iterable of candidate Item objects.
            
        Returns:
            List of match dictionaries sorted by descending score.
        """
        # Step 0: Filter candidates
        # Must not be the same item, must be opposite report_type, and must be active
        target_id = getattr(target_item, "id", None)
        target_type = getattr(target_item, "report_type", None)

        valid_candidates = []
        for cand in candidate_items:
            cand_id = getattr(cand, "id", None)
            cand_type = getattr(cand, "report_type", None)
            cand_status = getattr(cand, "status", "active")

            # Must not be self
            if target_id is not None and cand_id is not None and cand_id == target_id:
                continue

            # Must be opposite report type (lost -> found or found -> lost)
            if target_type and cand_type and target_type == cand_type:
                continue

            # Ineligible statuses
            if cand_status in ("resolved", "closed"):
                continue

            valid_candidates.append(cand)

        if not valid_candidates:
            return []

        # Step 1: Text Corpus Preparation
        target_text = build_item_corpus_string(target_item)
        if not target_text.strip():
            # If target has no text, cannot reliably match
            return []

        candidate_texts = [build_item_corpus_string(cand) for cand in valid_candidates]
        corpus = [target_text] + candidate_texts

        # Step 2: TF-IDF Vectorization & Cosine Similarity
        try:
            vectorizer = TfidfVectorizer(
                stop_words="english",
                ngram_range=(1, 2),
                max_features=5000,
                token_pattern=r"(?u)\b\w+\b"
            )
            tfidf_matrix = vectorizer.fit_transform(corpus)
            # Row 0 is target, rows 1..N are candidates
            cosine_scores = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:]).flatten()
        except Exception:
            # Fallback if scikit-learn encounters degenerate empty vocabulary
            cosine_scores = np.zeros(len(valid_candidates))

        # Step 3: Compute Contextual Adjustments and Build Results
        target_cat = getattr(target_item, "category", "")
        target_loc = getattr(target_item, "location", "")
        target_date = getattr(target_item, "incident_date", None)

        results = []

        for idx, cand in enumerate(valid_candidates):
            text_sim = float(cosine_scores[idx]) if idx < len(cosine_scores) else 0.0
            reasons = []

            # 3A. Text similarity explanation
            if text_sim >= 0.40:
                reasons.append(f"Strong description similarity ({int(text_sim * 100)}%)")
            elif text_sim >= 0.15:
                reasons.append(f"Relevant keyword overlap ({int(text_sim * 100)}%)")

            # 3B. Category Agreement (+15%)
            cand_cat = getattr(cand, "category", "")
            cat_bonus = 0.0
            if target_cat and cand_cat and target_cat.strip().lower() == cand_cat.strip().lower():
                cat_bonus = 0.15
                reasons.append(f"Exact category match: {target_cat}")

            # 3C. Location Agreement (+8% - +12%)
            cand_loc = getattr(cand, "location", "")
            loc_bonus, loc_reason = compute_location_bonus(target_loc, cand_loc)
            if loc_reason:
                reasons.append(loc_reason)

            # 3D. Date Proximity (+2% - +8%)
            cand_date = getattr(cand, "incident_date", None)
            date_bonus, date_reason = compute_date_proximity_bonus(target_date, cand_date)
            if date_reason:
                reasons.append(date_reason)

            # Composite Score Calculation
            # 60% text similarity + 40% contextual features
            composite_score = (text_sim * 0.65) + cat_bonus + loc_bonus + date_bonus
            # Bound strictly between 0.0 and 1.0
            composite_score = min(1.0, max(0.0, composite_score))
            score_percentage = int(round(composite_score * 100))

            # Only retain if meets threshold and has at least one meaningful reason
            if composite_score >= self.min_score and reasons:
                results.append({
                    "item": cand,
                    "score": composite_score,
                    "score_percentage": score_percentage,
                    "reasons": reasons,
                    "text_similarity": text_sim,
                })

        # Step 4: Sort descending by score
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:self.top_k]


# Convenience functional entrypoint
def get_item_matches(item, all_items: List[Any], min_score: float = 0.15, top_k: int = 5) -> List[Dict[str, Any]]:
    """Helper function to find matches for a given item from a list of all items."""
    matcher = ItemMatcher(min_score=min_score, top_k=top_k)
    return matcher.find_matches(item, all_items)
