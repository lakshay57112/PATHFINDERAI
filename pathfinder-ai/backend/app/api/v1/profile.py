from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import catalog_dep, current_user, rate_limit
from app.core.config import get_settings
from app.core.errors import NotFound
from app.db.models import Certificate, Project, User
from app.db.session import get_db
from app.engines.extraction import analyze_project
from app.engines.profile_analyzer import analyze_profile
from app.knowledge.catalog import Catalog
from app.schemas.api import CertificateIn, InterestsIn, OnboardingIn, ProfileUpdateIn, ProjectIn, SkillsIn
from app.services import profile_service as ps
from app.services import storage

router = APIRouter(tags=["profile"])


@router.post("/profile")
def save_profile(data: OnboardingIn, user: User = Depends(current_user), db: Session = Depends(get_db),
                 catalog: Catalog = Depends(catalog_dep)):
    """Save the full onboarding profile (idempotent: replaces interests/skills, adds new certificates/projects)."""
    ps.save_onboarding(db, user, data, catalog)
    return ps.serialize_profile(user, catalog)


@router.get("/profile")
def get_profile(user: User = Depends(current_user), db: Session = Depends(get_db), catalog: Catalog = Depends(catalog_dep)):
    ps.get_or_create_profile(db, user)
    return ps.serialize_profile(user, catalog)


@router.patch("/profile")
def update_profile(data: ProfileUpdateIn, user: User = Depends(current_user), db: Session = Depends(get_db),
                   catalog: Catalog = Depends(catalog_dep)):
    p = ps.get_or_create_profile(db, user)
    if data.name is not None:
        user.name = data.name.strip()
    for field in ("hours_per_week", "career_goals", "learning_preferences", "activities", "work_styles"):
        val = getattr(data, field)
        if val is not None:
            setattr(p, field, val)
    db.commit()
    return ps.serialize_profile(user, catalog)


@router.get("/profile/analysis")
def profile_analysis(user: User = Depends(current_user), db: Session = Depends(get_db), catalog: Catalog = Depends(catalog_dep)):
    return analyze_profile(ps.build_snapshot(db, user, catalog), catalog)


@router.post("/skills")
def update_skills(data: SkillsIn, user: User = Depends(current_user), db: Session = Depends(get_db),
                  catalog: Catalog = Depends(catalog_dep)):
    ps.set_skills(db, user, data.skills, catalog, replace=False)
    db.commit()
    db.refresh(user)
    return ps.serialize_profile(user, catalog)["skills"]


@router.post("/interests")
def update_interests(data: InterestsIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    ps.set_interests(db, user, data.interests)
    db.commit()
    return {"interests": [i.domain for i in user.interests]}


# ------------------------------------------------------------------------ certificates
@router.post("/certificates")
def add_certificate(data: CertificateIn, user: User = Depends(current_user), db: Session = Depends(get_db),
                    catalog: Catalog = Depends(catalog_dep)):
    cert = ps.add_certificate(db, user, data, catalog)
    db.commit()
    return ps.serialize_certificate(cert)


@router.post("/certificates/upload", dependencies=[Depends(rate_limit("upload", 20))])
async def upload_certificate(
    file: UploadFile = File(...),
    name: str = Form(..., min_length=2, max_length=200),
    issuer: str | None = Form(None, max_length=160),
    completed_on: date | None = Form(None),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
    catalog: Catalog = Depends(catalog_dep),
):
    s = get_settings()
    data = await file.read(s.max_upload_mb * 1024 * 1024 + 1)
    mime = storage.validate(data, file.filename)
    text = storage.extract_text(data, mime)
    key = storage.save_encrypted(data) if s.keep_uploaded_files else None
    cert = ps.add_certificate(db, user, CertificateIn(name=name, issuer=issuer, completed_on=completed_on), catalog,
                              extracted_text=text, file_key=key, file_mime=mime)
    db.commit()
    out = ps.serialize_certificate(cert)
    out["extracted_characters"] = len(text)
    return out


@router.delete("/certificates/{cert_id}")
def delete_certificate(cert_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    cert = db.get(Certificate, cert_id)
    if not cert or cert.user_id != user.id:
        raise NotFound("Certificate not found.")
    storage.delete(cert.file_key)
    db.delete(cert)
    db.commit()
    return {"ok": True}


# ------------------------------------------------------------------------ projects
@router.post("/projects")
def add_project(data: ProjectIn, user: User = Depends(current_user), db: Session = Depends(get_db),
                catalog: Catalog = Depends(catalog_dep)):
    proj = ps.add_project(db, user, data, catalog)
    db.commit()
    return ps.serialize_project(proj)


@router.post("/projects/analyze")
def analyze_project_preview(data: ProjectIn, _: User = Depends(current_user), catalog: Catalog = Depends(catalog_dep)):
    return analyze_project(data.name, data.description, data.technologies, catalog)


@router.delete("/projects/{project_id}")
def delete_project(project_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    proj = db.get(Project, project_id)
    if not proj or proj.user_id != user.id:
        raise NotFound("Project not found.")
    db.delete(proj)
    db.commit()
    return {"ok": True}
