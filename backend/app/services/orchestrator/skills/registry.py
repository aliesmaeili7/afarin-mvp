from app.services.orchestrator.schema import Route
from app.services.orchestrator.skills.advertising import AdvertisingSkill
from app.services.orchestrator.skills.base import ChatSkill
from app.services.orchestrator.skills.education import EducationSkill
from app.services.orchestrator.skills.general_image import GeneralImageSkill

_SKILLS: dict[str, ChatSkill] = {
    "advertising": AdvertisingSkill(),
    "education": EducationSkill(),
    "general_image": GeneralImageSkill(),
}


def skill_for(route: Route) -> ChatSkill | None:
    return _SKILLS.get(route)
