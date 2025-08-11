import logging
from typing import Dict, Any
import math
import uuid
from datetime import datetime, UTC
from uuid import UUID

from patrol.validation import Constants, TaskType
from patrol.validation.scoring import MinerScore, MinerScoreRepository, ValidationResult

logger = logging.getLogger(__name__)

NUMBER_OF_LOW_SCORES_TO_DISCARD = 2

class MinerScoring:
    def __init__(self, miner_score_repository: MinerScoreRepository, moving_average_denominator: int = 20):
        self.importance = {
            'volume': 0.9,
            'responsiveness': 0.1,
        }
        self.miner_score_repository = miner_score_repository
        self.moving_average_denominator = moving_average_denominator

    def calculate_novelty_score(self, payload: Dict[str, Any]) -> float:
        # Placeholder for future implementation
        return 0.0

    def calculate_volume_score(self, total_items: int) -> float:
        # Sigmoid formula
        score = 1 / (1 + math.exp(-Constants.STEEPNESS * (total_items - Constants.INFLECTION_POINT)))
        return score

    def calculate_responsiveness_score(self, response_time: float) -> float:
        return Constants.RESPONSE_TIME_HALF_SCORE / (response_time + Constants.RESPONSE_TIME_HALF_SCORE)

    async def _moving_average(self, overall_score: float, miner: tuple[str, int]) -> float:
        previous_scores = list(await self.miner_score_repository.find_latest_overall_scores(
            miner,
            TaskType.COLDKEY_SEARCH,
            self.moving_average_denominator - 1
        ))
        previous_scores.append(overall_score)
        numerator_scores = sorted(previous_scores, reverse=True)

        denominator = self.moving_average_denominator - NUMBER_OF_LOW_SCORES_TO_DISCARD
        numerator_scores = numerator_scores[:denominator]

        return sum(numerator_scores) / len(numerator_scores)

    async def calculate_score(
        self,
        uid: int,
        coldkey: str,
        hotkey: str,
        validation_result: ValidationResult,
        response_time: float,
        batch_id: UUID,
    ) -> MinerScore:

        if not validation_result.validated:
            overall_score_moving_average = self._moving_average(0.0, (hotkey, uid))

            logger.warning(f"Zero score added to records for {uid}, reason: {validation_result.message}.")
            return MinerScore(
                id=uuid.uuid4(),
                batch_id=batch_id,
                created_at=datetime.now(UTC),
                uid=uid,
                coldkey=coldkey,
                hotkey=hotkey,
                overall_score_moving_average=await overall_score_moving_average,
                overall_score=0.0,
                volume_score=0.0,
                volume=validation_result.volume,
                responsiveness_score=0.0,
                response_time_seconds=response_time,
                novelty_score=None,
                validation_passed=False,
                error_message=validation_result.message,
                task_type=TaskType.COLDKEY_SEARCH
            )

        volume_score = self.calculate_volume_score(validation_result.volume)
        responsiveness_score = self.calculate_responsiveness_score(response_time)

        overall_score = sum([
            volume_score * self.importance["volume"],
            responsiveness_score * self.importance["responsiveness"]
        ])

        logger.info(f"Scoring completed for miner {uid}, with overall score: {overall_score}")
        overall_score_moving_average = await self._moving_average(overall_score, (hotkey, uid))

        return MinerScore(
            id=uuid.uuid4(),
            batch_id=batch_id,
            created_at=datetime.now(UTC),
            uid=uid,
            coldkey=coldkey,
            hotkey=hotkey,
            overall_score_moving_average=overall_score_moving_average,
            overall_score=overall_score,
            volume_score=volume_score,
            volume=validation_result.volume,
            responsiveness_score=responsiveness_score,
            response_time_seconds=response_time,
            novelty_score=None,
            validation_passed=True,
            error_message=None,
            task_type=TaskType.COLDKEY_SEARCH
        )

    async def calculate_zero_score(self, batch_id, uid, coldkey, hotkey, error_message):

        overall_score_moving_average = await self._moving_average(0.0, (hotkey, uid))

        return MinerScore(
            id=uuid.uuid4(),
            batch_id=batch_id,
            created_at=datetime.now(UTC),
            uid=uid,
            coldkey=coldkey,
            hotkey=hotkey,
            overall_score_moving_average=overall_score_moving_average,
            overall_score=0,
            volume_score=0,
            volume=0,
            responsiveness_score=0,
            response_time_seconds=0,
            novelty_score=None,
            validation_passed=False,
            error_message=error_message,
            task_type=TaskType.COLDKEY_SEARCH
        )


def normalize_scores(scores: Dict[int, float]) -> dict[float]:
    """
        Normalize a dictionary of miner Coverage scores to ensure fair comparison.
        Returns list of Coverage scores normalized between 0-1.
    """
    if not scores:
        return {}
    
    min_score = min(scores.values())
    max_score = max(scores.values())
    
    if min_score == max_score:
        return [1.0] * len(scores)
    
    return {uid: round((score - min_score) / (max_score - min_score), 6) for uid, score in scores.items()}
