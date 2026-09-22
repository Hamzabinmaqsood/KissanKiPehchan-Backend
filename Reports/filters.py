from datetime import datetime, date
from typing import List, Optional
from CropsRecomendations.models import Recommendation, RecommendationItem
import logging

logger = logging.getLogger(__name__)

VALID_REPORT_TYPES = {"farmer", "agro"}

# ── Stage definitions ──────────────────────────────────────────────────────
#  Boundary semantics: day_start <= days < day_end  (half-open intervals)
#  This prevents the same day matching two stages at shared boundaries
#  (e.g. day 30 now belongs only to vegetative_growth, not pre_planting_early).
#  The final stage (maturity_pre_harvest) uses a closed end (<=) so that
#  exactly day 135 is still covered — handled explicitly in get_stage_for_days.

STAGE_DEFINITIONS = [
    {
        "key":            "pre_planting_early",
        "label":          "Pre Planting (Early Growth)",
        "day_start":      0,
        "day_end":        30,   # half-open: [0, 30)
        "farmer_indices": ["MSAVI"],
        "agro_indices":   ["MSAVI", "NDVI"],
    },
    {
        "key":            "vegetative_growth",
        "label":          "Vegetative Growth",
        "day_start":      30,
        "day_end":        65,   # half-open: [30, 65)
        "farmer_indices": ["NDVI"],
        "agro_indices":   ["NDVI", "NDMI", "NDRE"],
    },
    {
        "key":            "flowering_reproductive",
        "label":          "Flowering/Reproductive",
        "day_start":      65,
        "day_end":        95,   # half-open: [65, 95)
        "farmer_indices": ["NDVI"],
        "agro_indices":   ["NDVI", "NDMI", "NDRE"],
    },
    {
        "key":            "maturity_pre_harvest",
        "label":          "Maturity/Pre-Harvest",
        "day_start":      95,
        "day_end":        135,  # closed on both ends for final stage: [95, 135]
        "farmer_indices": ["NDVI"],
        "agro_indices":   ["NDVI", "ReCL"],
    },
]

_LAST_STAGE_INDEX = len(STAGE_DEFINITIONS) - 1


def get_stage_for_days(days_since_sowing: int) -> Optional[dict]:
    """
    Return the stage definition dict for the given days since sowing, or None.

    Interval semantics (half-open):  day_start <= days < day_end
    The final stage is closed on the right:  day_start <= days <= day_end
    This ensures shared boundary days (30, 65, 95) map to exactly one stage.
    """
    for i, stage in enumerate(STAGE_DEFINITIONS):
        is_last = (i == _LAST_STAGE_INDEX)
        if is_last:
            # Closed interval for the final stage
            if stage["day_start"] <= days_since_sowing <= stage["day_end"]:
                return stage
        else:
            # Half-open interval for all other stages
            if stage["day_start"] <= days_since_sowing < stage["day_end"]:
                return stage
    return None


def get_days_since_sowing(sowing_date) -> int:
    """
    Return days elapsed since sowing_date.

    Accepts both `datetime.date` and `datetime.datetime` objects so that
    Django ORM values (which may be datetime-aware) don't cause a TypeError.
    """
    # FIX #2: Coerce datetime → date to prevent TypeError on subtraction
    if isinstance(sowing_date, datetime):
        sowing_date = sowing_date.date()
    today = datetime.now().date()
    return (today - sowing_date).days


class RecommendationFilter:
    """
    Filters RecommendationItems by the current crop stage,
    determined from days elapsed since sowing_date.

    Report types
    ------------
    - "farmer" : single index per stage (simpler report for the farmer)
    - "agro"   : multiple indices per stage (detailed report for agronomists)

    The constructor accepts a pre-computed (days_since_sowing, current_stage)
    tuple via `precomputed_stage` so that callers who have already done this
    calculation (e.g. ReportGenerationService) can pass it in directly and
    avoid redundant datetime arithmetic.
    """

    def __init__(
        self,
        recommendations: List[Recommendation],
        sowing_date,                          # date | datetime
        report_type: str = "farmer",          # "farmer" | "agro"
        *,
        precomputed_stage: Optional[tuple] = None,  # (days_since_sowing, stage_dict|None)
    ):
        # FIX #3: Validate report_type early so bad values don't silently
        # fall through to the agro branch.
        if report_type not in VALID_REPORT_TYPES:
            raise ValueError(
                f"Invalid report_type {report_type!r}. "
                f"Must be one of: {sorted(VALID_REPORT_TYPES)}"
            )

        self.recommendations = recommendations
        self.sowing_date     = sowing_date
        self.report_type     = report_type
        self.current_date    = datetime.now().date()

        # FIX (duplicated calculation): Accept pre-computed values from the
        # orchestrator so we don't recalculate days/stage independently.
        if precomputed_stage is not None:
            self.days_since_sowing, self.current_stage = precomputed_stage
        else:
            self.days_since_sowing: int        = get_days_since_sowing(sowing_date)
            self.current_stage: Optional[dict] = get_stage_for_days(self.days_since_sowing)

    # ── Public API ─────────────────────────────────────────────────────────

    def get_applicable_items(self) -> List[RecommendationItem]:
        """
        Return RecommendationItems whose crop_stage and indice match the
        current stage and the report_type's allowed indices.
        """
        if self.current_stage is None:
            logger.warning(
                f"RecommendationFilter: day {self.days_since_sowing} is outside "
                f"all defined stages — no items returned."
            )
            return []

        all_items  = self._get_all_items()
        stage_key  = self.current_stage["key"]
        allowed_ix = self._allowed_indices()

        applicable = [
            item for item in all_items
            if item.crop_stage == stage_key and item.indice in allowed_ix
        ]

        logger.info(
            f"RecommendationFilter [{self.report_type}]: "
            f"day={self.days_since_sowing}, stage={stage_key}, "
            f"allowed_indices={allowed_ix}, "
            f"matched {len(applicable)}/{len(all_items)} items"
        )
        return applicable

    def get_stage_info(self) -> dict:
        """Return metadata about the current stage (useful for PDF headers)."""
        if self.current_stage is None:
            return {
                "key":               None,
                "label":             "Unknown Stage",
                "days_since_sowing": self.days_since_sowing,
                "indices":           [],
            }
        return {
            "key":               self.current_stage["key"],
            "label":             self.current_stage["label"],
            "days_since_sowing": self.days_since_sowing,
            "day_range":         (
                f"{self.current_stage['day_start']}-"
                f"{self.current_stage['day_end']} days"
            ),
            "indices":           self._allowed_indices(),
        }

    # ── Private helpers ────────────────────────────────────────────────────

    def _get_all_items(self) -> List[RecommendationItem]:
        items = []
        for rec in self.recommendations:
            items.extend(rec.items.all())
        return items

    def _allowed_indices(self) -> List[str]:
        if self.current_stage is None:
            return []
        key = "farmer_indices" if self.report_type == "farmer" else "agro_indices"
        return self.current_stage[key]