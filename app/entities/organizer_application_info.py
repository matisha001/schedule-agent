"""纯业务实体：办赛申请（玩家 → 办赛者，超管/运营审批）。"""

from dataclasses import dataclass


@dataclass
class OrganizerApplicationInfo:
    user_id: int
    status: str = "PENDING"  # PENDING / APPROVED / REJECTED
    reason: str | None = None
    reviewed_by: int | None = None
    reviewed_at: str | None = None
    id: int | None = None
    created_at: str | None = None
