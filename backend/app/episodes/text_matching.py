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
    return StaticModel.from_pretrained("minishlab/potion-multilingual-128M")


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
        self._vocabulary = {
            term: index for index, term in enumerate(document_frequency)
        }
        self._build_tfidf_entries(documents)
        self._embeddings = _unit_vectors(descriptions)
        self._query_vectors: dict[str, numpy.ndarray] = {}

    # TODO: Validate
    def _build_tfidf_entries(self, documents: list[Counter[str]]) -> None:
        entry_documents: list[int] = []
        entry_terms: list[int] = []
        entry_weights: list[float] = []
        for index, counts in enumerate(documents):
            for term, weight in self._tfidf_weights(counts).items():
                entry_documents.append(index)
                entry_terms.append(self._vocabulary[term])
                entry_weights.append(weight)
        self._entry_documents = numpy.asarray(entry_documents, dtype=numpy.intp)
        self._entry_terms = numpy.asarray(entry_terms, dtype=numpy.intp)
        self._entry_weights = numpy.asarray(entry_weights, dtype=numpy.float64)

    # TODO: Validate
    def _tfidf_weights(self, counts: Counter[str]) -> dict[str, float]:
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
    def _tfidf_scores(self, text: str) -> numpy.ndarray:
        weights = self._tfidf_weights(Counter(_tokenize(text)))
        query = numpy.zeros(len(self._vocabulary), dtype=numpy.float64)
        for term, weight in weights.items():
            index = self._vocabulary.get(term)
            if index is not None:
                query[index] = weight
        return numpy.bincount(
            self._entry_documents,
            weights=query[self._entry_terms] * self._entry_weights,
            minlength=self._document_count,
        )

    # TODO: Validate
    def _query_vectors_of(self, descriptions: list[str]) -> numpy.ndarray:
        unread = [
            description
            for description in dict.fromkeys(descriptions)
            if description not in self._query_vectors
        ]
        if unread:
            for description, vector in zip(unread, _unit_vectors(unread), strict=True):
                self._query_vectors[description] = vector
        return numpy.asarray(
            [self._query_vectors[description] for description in descriptions],
        )

    # TODO: Validate
    def embedding_scores_of(self, descriptions: list[str]) -> numpy.ndarray:
        scores: numpy.ndarray = (
            self._query_vectors_of(descriptions) @ self._embeddings.T
        )
        return scores.astype(numpy.float64)

    # TODO: Validate
    def _tfidf_scores_of(self, descriptions: list[str]) -> numpy.ndarray:
        return numpy.asarray(
            [self._tfidf_scores(description) for description in descriptions],
        )

    # TODO: Validate
    def blended_scores_of(self, descriptions: list[str]) -> numpy.ndarray:
        return 0.6 * self._tfidf_scores_of(
            descriptions,
        ) + 0.4 * self.embedding_scores_of(descriptions)

    # TODO: Validate
    def embedding_scores(self, description: str) -> list[float]:
        scores: list[float] = self.embedding_scores_of([description])[0].tolist()
        return scores

    # TODO: Validate
    def blended_scores(self, description: str) -> list[float]:
        scores: list[float] = self.blended_scores_of([description])[0].tolist()
        return scores
