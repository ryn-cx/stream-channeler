# TODO: Validate
from typing import Any

from sqlalchemy.sql.expression import ColumnElement, Subquery, UnaryExpression
from sqlmodel import func, select

from app.channels.episode_selector.sorting import SortExpressionBuilder
from app.channels.schemas import SortKeyInput

OrderTerms = list[UnaryExpression[Any] | ColumnElement[Any]]


# TODO: Validate
class OrderByComposer:
    # TODO: Validate
    def __init__(
        self,
        expressions: SortExpressionBuilder,
        sort_by: list[SortKeyInput],
        fuzzy_labels: dict[int, str],
    ) -> None:
        self._expressions = expressions
        self._sort_by = sort_by
        self._fuzzy_labels = fuzzy_labels

    # TODO: Validate
    def compose(self, subquery: Subquery) -> tuple[Subquery, OrderTerms]:
        for index in reversed(range(len(self._sort_by))):
            if self._sort_by[index].order == "sequential":
                continue
            row_number = func.row_number().over(
                partition_by=[
                    subquery.c[f"sort_value_{earlier}"] for earlier in range(index + 1)
                ],
                order_by=self._tail(subquery, index + 1)
                or [self._directed(subquery, index)],
            )
            subquery = select(
                subquery,
                row_number.label(f"order_rank_{index}"),
            ).subquery()
        return subquery, self._tail(subquery, 0)

    # TODO: Validate
    def _tail(self, level: Subquery, start: int) -> OrderTerms:
        terms: OrderTerms = []
        for index in range(start, len(self._sort_by)):
            terms.extend(self._contribution(level, index))
        return terms

    # TODO: Validate
    def _contribution(self, level: Subquery, index: int) -> OrderTerms:
        sort_key = self._sort_by[index]
        if sort_key.order == "sequential":
            if sort_key.fuzziness:
                return [self._fuzzy(level, index)]
            return [self._directed(level, index)]
        return [level.c[f"order_rank_{index}"], self._partition_order(level, index)]

    # TODO: Validate
    def _partition_order(self, level: Subquery, index: int) -> ColumnElement[Any]:
        sort_key = self._sort_by[index]
        if sort_key.order == "randomize":
            return self._expressions.random_hash(level.c[f"sort_value_{index}"])
        if sort_key.fuzziness:
            return self._fuzzy(level, index)
        return self._directed(level, index)

    # TODO: Validate
    def _directed(
        self,
        level: Subquery,
        index: int,
    ) -> UnaryExpression[Any] | ColumnElement[Any]:
        return self._expressions.apply_direction(
            level.c[f"sort_value_{index}"],
            self._sort_by[index],
        )

    # TODO: Validate
    def _fuzzy(self, level: Subquery, index: int) -> ColumnElement[Any]:
        fuzziness = self._sort_by[index].fuzziness or 0
        jitter: ColumnElement[Any] = self._expressions.random_hash(level.c.id) * (
            fuzziness / float(2**31)
        )
        return level.c[self._fuzzy_labels[index]] + jitter
