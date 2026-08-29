# TODO: Validate

import math
import re
from collections import Counter
from functools import lru_cache

import numpy  # noqa: ICN001 - Spelled out, as abbreviated names are not used here.
from model2vec import StaticModel


# TODO: Validate
@lru_cache(maxsize=1)
def _model() -> StaticModel:
    return StaticModel.from_pretrained("minishlab/potion-base-8M")


# TODO: Validate
def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9']+", text.lower())


# TODO: Validate
def _unit_vectors(texts: list[str]) -> numpy.ndarray:
    embeddings = numpy.asarray(_model().encode(texts), dtype=numpy.float32)
    magnitudes = numpy.linalg.norm(embeddings, axis=1, keepdims=True)
    magnitudes[magnitudes == 0] = 1.0
    return embeddings / magnitudes


# TODO: Validate
def _cosine(left_vector: dict[str, float], right_vector: dict[str, float]) -> float:
    if len(right_vector) < len(left_vector):
        left_vector, right_vector = right_vector, left_vector
    return sum(
        weight * right_vector.get(term, 0.0) for term, weight in left_vector.items()
    )


# TODO: Validate
class TextMatcher:
    # TODO: Validate
    def __init__(self, descriptions: list[str]) -> None:
        documents = [Counter(_tokenize(text)) for text in descriptions]
        document_frequency: Counter[str] = Counter()
        for document in documents:
            document_frequency.update(document.keys())
        self._document_count = len(documents)
        self._inverse_document_frequency = {
            term: math.log((self._document_count + 1) / (frequency + 1)) + 1
            for term, frequency in document_frequency.items()
        }
        self._unseen_inverse_document_frequency = math.log(self._document_count + 1) + 1
        self._tfidf_vectors = [self._tfidf_vector(text) for text in descriptions]
        self._embeddings = _unit_vectors(descriptions)

    # TODO: Validate
    def _tfidf_vector(self, text: str) -> dict[str, float]:
        counts = Counter(_tokenize(text))
        weights = {
            term: (1 + math.log(count))
            * self._inverse_document_frequency.get(
                term,
                self._unseen_inverse_document_frequency,
            )
            for term, count in counts.items()
        }
        magnitude = math.sqrt(sum(weight * weight for weight in weights.values()))
        if magnitude == 0:
            return {}
        return {term: weight / magnitude for term, weight in weights.items()}

    # TODO: Validate
    def embedding_scores(self, description: str) -> list[float]:
        return [
            float(score)
            for score in _unit_vectors([description])[0] @ self._embeddings.T
        ]

    # TODO: Validate
    def blended_scores(self, description: str) -> list[float]:
        query_vector = self._tfidf_vector(description)
        return [
            0.6 * _cosine(query_vector, candidate_vector) + 0.4 * embedding_score
            for candidate_vector, embedding_score in zip(
                self._tfidf_vectors,
                self.embedding_scores(description),
                strict=True,
            )
        ]
