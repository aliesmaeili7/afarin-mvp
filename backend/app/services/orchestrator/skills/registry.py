from app.services.orchestrator.schema import Route
from app.services.orchestrator.skills.advertising import AdvertisingSkill
from app.services.orchestrator.skills.base import ChatSkill
from app.services.orchestrator.skills.education import EducationSkill
from app.services.orchestrator.skills.general_image import GeneralImageSkill
from app.services.orchestrator.skills.image_edit import ImageEditSkill

_SKILLS: dict[str, ChatSkill] = {
    "advertising": AdvertisingSkill(),
    "education": EducationSkill(),
    "general_image": GeneralImageSkill(),
    "image_edit": ImageEditSkill(),
}


def skill_for(route: Route) -> ChatSkill | None:
    return _SKILLS.get(route)
