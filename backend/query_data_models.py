from typing import Any, Literal, Optional, List
from pydantic import BaseModel


class DataFetcherInputs(BaseModel):
    question: str
    hard_filters: list
    db_name: str
    previous_context: list


class Clarification(BaseModel):
    question: str
    response: Optional[str] = None


class PreviousContextItem(BaseModel):
    question: str
    sql: str


class PDFSearchRequest(BaseModel):
    analysis_id: str
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "analysis_id": "your-analysis-id"
                }
            ]
        }
    }


class AnalysisData(BaseModel):
    analysis_id: str
    db_name: str
    initial_question: Optional[str] = None
    tool_name: Optional[str] = None
    inputs: Optional[DataFetcherInputs] = None
    clarification_questions: Optional[list[Clarification]] = None
    assignment_understanding: Optional[str] = None
    previous_context: Optional[list[PreviousContextItem]] = None
    sql: Optional[str] = None
    output: Optional[str] = None
    error: Optional[str] = None
    pdf_search_results: Optional[list] = None


class RerunEditedInputs(BaseModel):
    question: Optional[str] = None
    hard_filters: Optional[list] = None
    sql: Optional[str] = None


class RerunRequest(BaseModel):
    token: str
    db_name: str
    analysis_id: str
    edited_inputs: Optional[RerunEditedInputs] = None
