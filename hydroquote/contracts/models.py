"""Pydantic contracts aligned with migration-package schemas."""

from __future__ import annotations

from decimal import Decimal
from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class QuotationStatus(str, Enum):
    NEEDS_INPUT = "needs_input"
    PRELIMINARY = "preliminary"
    REVIEW_REQUIRED = "review_required"
    READY = "ready"
    REJECTED = "rejected"
    ERROR = "error"
    PROCESSING = "processing"


class WorkflowPath(str, Enum):
    FAST_QUOTE = "fast_quote"
    EXPERT_QUOTE = "expert_quote"


class WorkflowStage(str, Enum):
    CUSTOMER_INQUIRY = "customer_inquiry"
    TECHNICAL_SELECTION = "technical_selection"
    ENGINEERING_COST = "engineering_cost"
    COMMERCIAL_QUOTATION = "commercial_quotation"
    PI_GENERATION = "pi_generation"
    COMPLETED = "completed"


MAIN_EQUIPMENT_KEYS = (
    "hydro_turbine",
    "generator_avr",
    "speed_governor",
    "inlet_valve",
    "automation_system",
)


class InquiryData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_name: Optional[str] = None
    project_country: Optional[str] = None
    project_location: Optional[str] = None
    customer_company: Optional[str] = None
    customer_contact: Optional[str] = None
    customer_email: Optional[str] = None
    net_head_m: Optional[float] = None
    design_flow_m3s: Optional[float] = None
    installed_capacity_kw: Optional[float] = None
    number_of_units: Optional[int] = None
    unit_capacity_kw: Optional[float] = None
    voltage_v: Optional[float] = None
    frequency_hz: Optional[float] = None
    turbine_type: Optional[str] = None
    automation_level: Literal["Basic", "Standard", "Advanced"] = "Standard"
    sediment_load: Optional[str] = None
    flow_variability: Optional[str] = None
    special_control_required: bool = False
    customer_requests_expert_review: bool = False
    turbine_type_ambiguous: bool = False
    boundary_head_condition: bool = False
    hydraulic_power_conflict: bool = False
    risk_reserve_rate: Optional[Decimal] = None
    risk_reserve_rate_approved: bool = False
    pressure_factor: Optional[Decimal] = None
    voltage_factor: Optional[Decimal] = None
    speed_factor: Optional[Decimal] = None
    efficiency: Optional[float] = None
    source_provenance: list[str] = Field(default_factory=list)
    field_evidence: dict[str, Any] = Field(default_factory=dict)

    @field_validator("risk_reserve_rate", "pressure_factor", "voltage_factor", "speed_factor", mode="before")
    @classmethod
    def _dec(cls, v: Any) -> Any:
        if v is None or v == "":
            return None
        return Decimal(str(v))


class EquipmentScopeItem(BaseModel):
    code: str
    name: str
    quantity: int = 1
    notes: Optional[str] = None


class ExpertOpinion(BaseModel):
    role: str
    analysis: str
    risks: list[str] = Field(default_factory=list)


class TechnicalSelectionPackage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    recommended_turbine_type: str
    unit_count: int
    unit_capacity_kw: Decimal
    hydraulic_calculation: dict[str, Any] = Field(default_factory=dict)
    equipment_scope: list[EquipmentScopeItem]
    automation_scope: str = "Standard PLC Automation"
    optional_upgrades: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    risk_notes: list[str] = Field(default_factory=list)
    expert_opinions: list[ExpertOpinion] = Field(default_factory=list)
    discussion_summary: Optional[str] = None
    cross_review: Optional[str] = None
    technical_approval_required: bool = False
    readiness: Literal["preliminary_ready", "firm_ready", "needs_human_review"] = "preliminary_ready"
    source_provenance: list[str] = Field(default_factory=list)
    selection_path: Literal["fast_quote", "expert_quote"] = "fast_quote"

    @field_validator("unit_capacity_kw", mode="before")
    @classmethod
    def _cap(cls, v: Any) -> Decimal:
        return Decimal(str(v))


class EquipmentCostLine(BaseModel):
    equipment_key: str
    display_name: str
    unit_base_price: Decimal
    quantity: int
    factors: dict[str, str] = Field(default_factory=dict)
    line_total: Decimal
    review_required: bool = False
    review_reasons: list[str] = Field(default_factory=list)
    rule_version: str


class CostBreakdown(BaseModel):
    equipment_costs: dict[str, EquipmentCostLine]
    main_equipment_base_cost: Decimal
    project_additional_cost: Decimal
    personnel_cost: Decimal
    risk_reserve_rate: Optional[Decimal] = None
    after_sales_rate: Decimal
    internal_cost: Optional[Decimal] = None
    commercial_quotation: Optional[Decimal] = None
    review_required: bool = False
    review_reasons: list[str] = Field(default_factory=list)
    rule_version: str
    calculation_idempotency_key: str
