"""
PitWall AI — ML Prediction API Endpoints
Real-time predictions from trained ML models.
"""

from fastapi import APIRouter, HTTPException

from apps.backend.api.v1.schemas.ml_schemas import (
    DegradationPredictionRequest,
    DegradationPredictionResponse,
    PitPredictionRequest,
    PitPredictionResponse,
    PositionPredictionRequest,
    PositionPredictionResponse,
    PositionResult,
)

router = APIRouter()


# ── Pit Stop Prediction ────────────────────────────────────────────────────────


@router.post("/predict/pit-stop", response_model=PitPredictionResponse)
async def predict_pit_stop(request: PitPredictionRequest):
    """
    Predict pit stop probability for current race state.

    Returns probability 0-1 and HIGH/MEDIUM/LOW confidence.
    Model: GradientBoosting, ROC-AUC 0.827, Recall 83.3%

    Top predictive features:
    - TyreLife (24%) — age of current tyre set
    - DegRate (17%) — current degradation rate
    - LapsRemaining (13%) — strategic window remaining
    """
    try:
        from core.ml.pit_predictor import predict_pit_probability

        result = predict_pit_probability(
            {
                "TyreLife": request.tyre_life,
                "Compound": request.compound,
                "Position": request.position,
                "GapAhead": request.gap_ahead,
                "GapBehind": request.gap_behind,
                "LapsRemaining": request.laps_remaining,
                "LapTimeSeconds": request.lap_time,
                "LapTimeTrend": request.lap_time_trend,
                "DegRate": request.deg_rate,
                "Stint": request.stint,
                "LapNumber": request.lap_number,
                "Circuit": request.circuit,
                "SpeedFL": request.speed_fl,
            }
        )

        return PitPredictionResponse(
            pit_probability=result["pit_probability"],
            recommend_pit=result["recommend_pit"],
            confidence=result["confidence"],
            threshold=result["threshold"],
            meta={
                "model": "GradientBoostingClassifier",
                "roc_auc": 0.827,
                "recall": 0.833,
                "compound": request.compound,
                "tyre_life": request.tyre_life,
            },
        )

    except FileNotFoundError:
        raise HTTPException(
            status_code=503,
            detail="ML model not trained. Run train_pit_predictor() first.",
        ) from None
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


# ── Degradation Prediction ─────────────────────────────────────────────────────


@router.post("/predict/lap-delta", response_model=DegradationPredictionResponse)
async def predict_lap_delta(request: DegradationPredictionRequest):
    """
    Predict lap time delta above fresh tyre pace.

    Returns how many seconds slower than fresh tyre pace
    given current tyre age and conditions.

    Model: XGBoost Regressor, RMSE 1.40s (HARD: 0.988s)
    """
    try:
        from core.ml.degradation_model import predict_lap_delta

        result = predict_lap_delta(
            tyre_life=request.tyre_life,
            compound=request.compound,
            stint=request.stint,
            lap_number=request.lap_number,
            laps_remaining=request.laps_remaining,
            deg_rate=request.deg_rate,
            position=request.position,
            speed_fl=request.speed_fl,
        )

        return DegradationPredictionResponse(
            predicted_delta=result["predicted_delta"],
            tyre_life=result["tyre_life"],
            compound=result["compound"],
            interpretation=result["interpretation"],
            meta={
                "model": "XGBoostRegressor",
                "rmse": 1.40,
                "hard_rmse": 0.988,
            },
        )

    except FileNotFoundError:
        raise HTTPException(
            status_code=503,
            detail="ML model not trained. Run train_degradation_model() first.",
        ) from None
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


# ── Position Prediction ────────────────────────────────────────────────────────


@router.post("/predict/position", response_model=PositionPredictionResponse)
async def predict_position(request: PositionPredictionRequest):
    """
    Predict finishing position probability distribution.

    Returns probability for each position P1-P20.
    Most useful with 10+ laps remaining.

    Model: XGBoost Multiclass, Top-3 Accuracy 86%
    """
    try:
        from core.ml.position_predictor import predict_position_distribution

        result = predict_position_distribution(
            current_position=request.current_position,
            laps_remaining=request.laps_remaining,
            tyre_life=request.tyre_life,
            compound=request.compound,
            gap_ahead=request.gap_ahead,
            gap_behind=request.gap_behind,
            lap_time=request.lap_time,
            lap_time_trend=request.lap_time_trend,
            deg_rate=request.deg_rate,
            stint=request.stint,
        )

        top5 = [
            PositionResult(position=pos, probability=prob)
            for pos, prob in result["top5_positions"]
        ]

        return PositionPredictionResponse(
            most_likely_position=result["most_likely_position"],
            top5_positions=top5,
            current_position=request.current_position,
            laps_remaining=request.laps_remaining,
            meta={
                "model": "XGBoostMulticlass",
                "top3_acc": 0.86,
                "within_1": 0.62,
            },
        )

    except FileNotFoundError:
        raise HTTPException(
            status_code=503,
            detail="ML model not trained. Run train_position_predictor() first.",
        ) from None
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None
