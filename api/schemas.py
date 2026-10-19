"""Request / response contracts for the prediction API."""

from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

EXAMPLE_PATIENT = {
    "age": 58, "sex": 1, "cp": 4, "trestbps": 140, "chol": 260, "fbs": 0,
    "restecg": 2, "thalach": 125, "exang": 1, "oldpeak": 2.2, "slope": 2,
    "ca": 1, "thal": 7,
}


class PatientFeatures(BaseModel):
    """The 13 raw clinical attributes of the UCI Cleveland dataset."""

    model_config = ConfigDict(extra="forbid",
                              json_schema_extra={"example": EXAMPLE_PATIENT})

    age: float = Field(..., ge=18, le=100, description="Age in years")
    sex: Literal[0, 1] = Field(..., description="1 = male, 0 = female")
    cp: Literal[1, 2, 3, 4] = Field(
        ..., description="Chest pain: 1 typical, 2 atypical, "
                         "3 non-anginal, 4 asymptomatic")
    trestbps: float = Field(..., ge=70, le=250,
                            description="Resting blood pressure (mm Hg)")
    chol: float = Field(..., ge=100, le=650,
                        description="Serum cholesterol (mg/dl)")
    fbs: Literal[0, 1] = Field(..., description="Fasting sugar > 120 mg/dl")
    restecg: Literal[0, 1, 2] = Field(..., description="Resting ECG result")
    thalach: float = Field(..., ge=60, le=230,
                           description="Max heart rate achieved")
    exang: Literal[0, 1] = Field(..., description="Exercise-induced angina")
    oldpeak: float = Field(..., ge=0, le=7,
                           description="ST depression induced by exercise")
    slope: Literal[1, 2, 3] = Field(..., description="Slope of peak ST")
    ca: Optional[int] = Field(None, ge=0, le=3,
                              description="Major vessels coloured (0-3); "
                                          "optional, imputed if missing")
    thal: Optional[Literal[3, 6, 7]] = Field(
        None, description="3 normal, 6 fixed, 7 reversible defect; "
                          "optional, imputed if missing")


class PredictionResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    prediction: int = Field(..., description="1 = heart disease predicted")
    label: str
    confidence: float = Field(..., description="Probability of the "
                                               "predicted class")
    risk_probability: float = Field(..., description="P(heart disease)")
    model_version: str
    request_id: str


class BatchRequest(BaseModel):
    patients: List[PatientFeatures] = Field(..., min_length=1,
                                            max_length=500)


class BatchResponse(BaseModel):
    predictions: List[PredictionResponse]
