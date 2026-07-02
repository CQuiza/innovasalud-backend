from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.certificate import Certificate
from app.models.certificate_type import CertificateType
from app.models.course import Course
from app.models.user import User


class DashboardRepository:
    async def get_stats(self, db: AsyncSession) -> dict[str, int]:
        queries = {
            "total_users": select(func.count(User.id)),
            "total_certificates": select(func.count(Certificate.id)),
            "active_certificates": select(func.count(Certificate.id)).where(
                Certificate.status == "active"
            ),
            "expired_certificates": select(func.count(Certificate.id)).where(
                Certificate.status == "expired"
            ),
            "revoked_certificates": select(func.count(Certificate.id)).where(
                Certificate.status == "revoked"
            ),
            "published_courses": select(func.count(Course.id)).where(
                Course.status == "published"
            ),
            "certificate_types": select(func.count(CertificateType.id)),
        }
        results: dict[str, int] = {}
        for key, stmt in queries.items():
            r = await db.execute(stmt)
            results[key] = r.scalar_one()
        return results


dashboard_repository = DashboardRepository()
