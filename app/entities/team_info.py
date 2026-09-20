"""纯业务实体：球队信息。

初始设计，字段待用户后续补充确认（教练、主场、球衣色等）。
"""

from dataclasses import dataclass


@dataclass
class TeamInfo:
    id: str
    name: str
    sport: str
    short_name: str
    region: str
    home_venue: str
    description: str
